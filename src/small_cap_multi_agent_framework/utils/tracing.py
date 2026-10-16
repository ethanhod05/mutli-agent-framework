"""
Run Tracing
===========

Records every real tool call and task completion during a crew run to a
structured JSON file, so agent behavior can be inspected after the fact
instead of only appearing as scrolling console output. This is also the
data source for grounding evals: every number in the final report should
be traceable back to a tool_call entry here.
"""

import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Callable, Optional

from crewai.events.event_bus import crewai_event_bus
from crewai.events.types.tool_usage_events import ToolUsageFinishedEvent

logger = logging.getLogger(__name__)


class RunTracer:
    """Captures tool calls and task outputs for one crew execution.

    Tool calls are captured via crewai's global event bus (subscribing to
    ToolUsageFinishedEvent), not the old step_callback mechanism - as of
    crewai 1.15, step_callback only ever fires with a bare AgentFinish (no
    tool name/args/result attached at all), confirmed empirically by
    logging the real object type/attrs during a live run. The event bus is
    a process-wide singleton, so the handler registered in __init__ MUST
    be unregistered via close() when this run ends, or every later run in
    the same process would keep accumulating stale listeners - the exact
    failure mode already hit once this session with step_callback on the
    module-level agent singletons.

    task_callback (still passed via Crew(task_callback=tracer.on_task_complete))
    is unaffected by that change and keeps working as before.

    `on_event`, if given, is called with each event dict the moment it's
    recorded - used by the web UI to stream live agent activity without the
    tracer needing to know anything about SSE/queues.
    """

    def __init__(self, execution_id: str, output_dir: str = "output/traces",
                 on_event: Optional[Callable[[dict], None]] = None):
        self.execution_id = execution_id
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.trace_file = self.output_dir / f"trace_{execution_id}.json"
        self.events = []
        self.on_event = on_event
        crewai_event_bus.on(ToolUsageFinishedEvent)(self._on_tool_usage_finished)

    def close(self) -> None:
        """Unregister this run's event-bus handler. Always call this when a
        run ends (success or failure) - see the class docstring for why."""
        crewai_event_bus.off(ToolUsageFinishedEvent, self._on_tool_usage_finished)

    def _record(self, event: dict) -> None:
        self.events.append(event)
        self._save()
        if self.on_event:
            self.on_event(event)

    def _on_tool_usage_finished(self, source, event: ToolUsageFinishedEvent) -> None:
        """crewai event-bus handler - fires once per completed tool call,
        with the real tool name/args/output/agent role already attached
        (no more duck-typing or guessing needed)."""
        tool_args = event.tool_args
        tool_input = json.dumps(tool_args) if isinstance(tool_args, dict) else str(tool_args)
        self._record({
            "type": "tool_call",
            "timestamp": datetime.now().isoformat(),
            "tool": event.tool_name,
            "tool_input": tool_input,
            "result": str(event.output)[:4000],
            "agent_role": event.agent_role,
        })

    def on_task_complete(self, output) -> None:
        """crewai task_callback - fires after each task finishes."""
        self._record({
            "type": "task_complete",
            "timestamp": datetime.now().isoformat(),
            "agent": str(getattr(output, "agent", "")),
            "description": (getattr(output, "description", "") or "").strip()[:300],
            "raw_output": getattr(output, "raw", ""),
        })

    def tool_calls(self) -> list:
        """The tool-call events only - the ground truth for grounding evals."""
        return [e for e in self.events if e["type"] == "tool_call"]

    def _save(self) -> None:
        try:
            with open(self.trace_file, "w") as f:
                json.dump({"execution_id": self.execution_id, "events": self.events}, f, indent=2)
        except Exception as e:
            logger.warning(f"Failed to write trace file: {e}")
