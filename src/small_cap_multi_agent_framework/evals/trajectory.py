"""
Trajectory Eval
================

Grounding checks whether a report is honest; thesis-consistency checks
whether it's internally coherent; outcome tracking checks whether it was
actually right. None of them can see HOW the agents got there - the path
itself. A report can pass all three and still have gotten there by an agent
flailing for a minute and a half. This eval grades the path.

Motivated by a real incident, not a hypothetical one: the Quantitative
Financial Analyst got stuck calling the fundamentals tool for HROW 36 times
in a row over ~90 seconds, alternating between the real tool result and
crewai's own built-in loop-detection warning ("I tried reusing the same
input, I must stop using this action input..."), which the model kept
ignoring. Grounding and thesis-consistency both passed that run - the
eventual numbers were real and the call matched them - so neither eval had
any way to see the problem. A trajectory grader is the only one of the four
that can.

Checks four things, each a real failure mode:
1. Repeated identical tool calls within one task (the HROW case).
2. Zero tool calls from an agent whose own instructions require one (the
   opposite failure - skipping the job instead of looping on it).
3. A tool call for the wrong ticker (the task was for X, the call was for Y -
   cross-contamination between tickers).
4. A tool call from an agent that should never make one at all (tools=[] in
   agents.py) - a delegation leak or similar would show up here.

Like grounding and thesis-consistency, this is deterministic and rule-based,
not another LLM call - whether a path repeats itself is not a judgment call.
"""

import re
from collections import Counter

TICKER_INPUT_RE = re.compile(r'"ticker"\s*:\s*"([A-Z.\-]+)"')
TICKER_IN_DESCRIPTION_RE = re.compile(r"ticker '([A-Z.\-]+)'")

# Roles with tools=[] in agents.py - these should never show up with a tool
# call in their segment at all.
NO_TOOL_ROLES = {"Senior Portfolio Manager", "Financial Data Quality Specialist"}

# A single repeat (2 calls where 1 was expected) is a minor inefficiency,
# worth knowing about but not alarming. Three or more identical calls is the
# pathological loop that motivated this eval.
WARN_AT_REPEATS = 2
FAIL_AT_REPEATS = 3

_SEVERITY_ORDER = {"ok": 0, "warn": 1, "fail": 2}


def _agent_from_tool_input(tool_input: str):
    """Best-effort agent-role guess from a tool call alone, used only for an
    incomplete segment (see below) where there's no task_complete to read
    the real agent name from."""
    if not tool_input:
        return None
    if '"fundamental"' in tool_input:
        return "Quantitative Financial Analyst"
    if '"news"' in tool_input:
        return "Market Intelligence Analyst"
    return None


def _segment_trace_by_task(trace_events: list) -> list:
    """Group each task's tool_calls with the task_complete that follows it.

    Process.sequential means tasks run strictly one at a time, in order, so
    every tool_call between two task_complete events belongs to the task
    that completes next. This gives ground-truth per-task attribution
    without the tracer needing to know which task is active - which
    crewai's step_callback payload doesn't tell us directly.

    Critically: if the trace ends with tool_calls that were never followed
    by a task_complete, that task never actually finished - the run was
    killed, crashed, or abandoned mid-loop. This is the shape the real HROW
    incident took: the trace had 36 tool_calls for one task and it never
    completed at all, so naively only looking at *completed* tasks would
    miss the exact failure this eval exists to catch. That trailing work is
    emitted as its own "incomplete" segment rather than silently dropped.
    """
    segments = []
    pending_calls = []
    for event in trace_events:
        if event.get("type") == "tool_call":
            pending_calls.append(event)
        elif event.get("type") == "task_complete":
            segments.append({
                "agent": event.get("agent") or "",
                "description": event.get("description") or "",
                "tool_calls": pending_calls,
                "completed": True,
            })
            pending_calls = []

    if pending_calls:
        guessed_agent = _agent_from_tool_input(pending_calls[-1].get("tool_input"))
        segments.append({
            "agent": guessed_agent or "",
            "description": "",
            "tool_calls": pending_calls,
            "completed": False,
        })

    return segments


def _expected_ticker(description: str, tool_calls: list):
    """The ticker this task was for, from its description - or, if there's
    no description at all (an incomplete segment has none), from its own
    tool calls instead, since they still name the ticker even when nothing
    else does."""
    m = TICKER_IN_DESCRIPTION_RE.search(description)
    if m:
        return m.group(1)
    for call in tool_calls:
        m = TICKER_INPUT_RE.search(call.get("tool_input") or "")
        if m:
            return m.group(1)
    return None


def _grade_segment(agent: str, ticker, tool_calls: list, completed: bool) -> dict:
    violations = []
    severity = "ok"

    def bump(sev):
        nonlocal severity
        if _SEVERITY_ORDER[sev] > _SEVERITY_ORDER[severity]:
            severity = sev

    if not completed:
        # The trace ended mid-task: the run was killed, crashed, or
        # abandoned before this task ever produced a final answer. That's
        # noteworthy on its own, regardless of what the calls inside it
        # look like - a task that never finishes is never "ok".
        violations.append(
            f"task for {ticker or 'this task'} never completed - the trace ends mid-task"
        )
        bump("warn")

    if agent in NO_TOOL_ROLES:
        if tool_calls:
            violations.append(
                f"{agent} made {len(tool_calls)} tool call(s) but this role should never call a tool"
            )
            bump("fail")
        return {"severity": severity, "violations": violations}

    # From here on, agent is expected to use its tool exactly once.
    if not tool_calls:
        violations.append(f"{agent} made no tool call at all for {ticker or 'this task'}")
        bump("fail")
        return {"severity": severity, "violations": violations}

    call_counts = Counter(c.get("tool_input") for c in tool_calls)
    for tool_input, count in call_counts.items():
        if count >= FAIL_AT_REPEATS:
            violations.append(f"called the same input {count} times in one task: {tool_input}")
            bump("fail")
        elif count >= WARN_AT_REPEATS:
            violations.append(f"called the same input {count} times in one task: {tool_input}")
            bump("warn")

    if ticker:
        for call in tool_calls:
            m = TICKER_INPUT_RE.search(call.get("tool_input") or "")
            if m and m.group(1) != ticker:
                violations.append(f"task was for {ticker} but called the tool for {m.group(1)} instead")
                bump("fail")

    return {"severity": severity, "violations": violations}


def evaluate_trajectory(trace_events: list) -> dict:
    """Grade the path the agents took during one run, not just the output.

    Returns a dict with:
    - segments: one entry per task, with its agent, ticker, tool-call count,
      severity, and any violations found
    - repeated_call_tickers: tickers where a tool was called more than once
      with the same input (the core failure mode this eval exists to catch)
    - total_tool_calls / total_tasks: raw counts, for a quick efficiency
      glance even before reading details
    - severity: 'ok' | 'warn' | 'fail' - the worst single segment's severity
    - trajectory_passed: False only at 'fail' severity (3+ repeats, a
      no-tool-role violation, a wrong-ticker call, or a skipped tool call)
    """
    segments = _segment_trace_by_task(trace_events)

    results = []
    worst_severity = "ok"

    for seg in segments:
        agent = seg["agent"]
        ticker = _expected_ticker(seg["description"], seg["tool_calls"])
        grade = _grade_segment(agent, ticker, seg["tool_calls"], seg["completed"])

        if _SEVERITY_ORDER[grade["severity"]] > _SEVERITY_ORDER[worst_severity]:
            worst_severity = grade["severity"]

        results.append({
            "agent": agent,
            "ticker": ticker,
            "tool_call_count": len(seg["tool_calls"]),
            "completed": seg["completed"],
            "severity": grade["severity"],
            "violations": grade["violations"],
        })

    return {
        "segments": results,
        "repeated_call_tickers": sorted({
            r["ticker"] for r in results if r["severity"] in ("warn", "fail") and r["ticker"]
        }),
        "total_tool_calls": sum(r["tool_call_count"] for r in results),
        "total_tasks": len(results),
        "severity": worst_severity,
        "trajectory_passed": worst_severity != "fail",
    }
