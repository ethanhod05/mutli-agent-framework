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

logger = logging.getLogger(__name__)


class RunTracer:
    """Captures tool calls and task outputs for one crew execution.

    Wire up via crewai's Crew(step_callback=tracer.on_step,
    task_callback=tracer.on_task_complete). Saves after every event so a
    crash mid-run still leaves a usable partial trace.

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

    def _record(self, event: dict) -> None:
        self.events.append(event)
        self._save()
        if self.on_event:
            self.on_event(event)

    def on_step(self, step) -> None:
        """crewai step_callback - fires after every agent step.

        Duck-typed on purpose: crewai passes different internal object types
        through this callback (a bare tool result, then the fuller action
        object once the tool has run). We only care about the latter, which
        has both `tool` and a populated `result`.
        """
        tool = getattr(step, "tool", None)
        result = getattr(step, "result", None)
        if tool and result is not None:
            self._record({
                "type": "tool_call",
                "timestamp": datetime.now().isoformat(),
                "tool": tool,
                "tool_input": getattr(step, "tool_input", None),
                "result": str(result)[:4000],
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
