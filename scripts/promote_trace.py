#!/usr/bin/env python
"""
Promote a Trace to a Permanent Regression Case
=================================================

Turns a real saved trace into a permanent fixture that
tests/evals/test_promoted_cases.py replays against the CURRENT trajectory
grader on every test run - so a real production incident, once understood
and fixed, can never silently regress without a test failing. Before this,
turning an incident into a guard meant hand-writing a synthetic test that
approximates the shape of what happened (see test_trajectory.py's
test_repeated_calls_on_an_incomplete_task_is_flagged, built by hand to
resemble the HROW incident) - this promotes the actual real trace instead.

Deliberately scoped to STRUCTURAL/behavioral cases only - trajectory
violations like repeated calls, wrong-role tool use, or an incomplete
task. It refuses to promote a clean ('ok') trajectory, since there'd be
nothing to guard against.

This is NOT for data-accuracy cases (grounding/thesis failures), and on
purpose. A trace captured before a data-source fix (e.g. before the SEC
EDGAR fallback existed) has a grounding "expected" outcome that was only
ever correct because of a bug that's since been fixed - promoting that as
permanent truth would start flagging regressions on bugs already fixed,
or lock in the wrong expected behavior as if it were correct. A trajectory
violation is about the agent's own control flow, true independent of
which data source answered the tool call - safe to promote as-is,
forever. If you want to guard a data-accuracy scenario, that needs a
fresh, manually-verified baseline run instead (see the conversation that
led here) - not this script.

Usage:
    python scripts/promote_trace.py --execution-id 20261001_142145 \
        --name hrow_infinite_loop \
        --reason "Agent repeated the same fundamentals call 36 times without completing the task"
"""

import argparse
import json
import shutil
import sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from small_cap_multi_agent_framework.evals.trajectory import evaluate_trajectory

FIXTURES_DIR = Path(__file__).parent.parent / "tests" / "fixtures" / "promoted_traces"


def main():
    parser = argparse.ArgumentParser(
        description="Promote a real trace into a permanent trajectory regression case."
    )
    parser.add_argument("--execution-id", required=True, help="Execution ID of the trace to promote")
    parser.add_argument("--name", required=True, help="Short, descriptive case name (used as the fixture filename)")
    parser.add_argument("--reason", required=True, help="What happened and why it matters - saved with the case")
    parser.add_argument("--output-dir", default="output", help="Output directory to read the trace from (default: output)")
    args = parser.parse_args()

    output_dir = Path(args.output_dir)
    trace_path = output_dir / "traces" / f"trace_{args.execution_id}.json"
    if not trace_path.exists():
        sys.exit(f"No trace file found: {trace_path}")

    trace = json.loads(trace_path.read_text())
    result = evaluate_trajectory(trace["events"])

    if result["severity"] == "ok":
        sys.exit(
            "This trace's trajectory is 'ok' - nothing to promote. Promotion exists to turn a real "
            "violation into a permanent regression guard, not to archive a clean run."
        )

    FIXTURES_DIR.mkdir(parents=True, exist_ok=True)
    fixture_path = FIXTURES_DIR / f"{args.name}.json"
    meta_path = FIXTURES_DIR / f"{args.name}.meta.json"

    if fixture_path.exists():
        sys.exit(f"A case named '{args.name}' already exists at {fixture_path} - pick a different --name.")

    shutil.copy(trace_path, fixture_path)
    meta = {
        "case_name": args.name,
        "source_execution_id": args.execution_id,
        "promoted_at": datetime.now().isoformat(),
        "reason": args.reason,
        "classification": "structural",
        "expected": {
            "severity": result["severity"],
            "trajectory_passed": result["trajectory_passed"],
            "repeated_call_tickers": result["repeated_call_tickers"],
        },
    }
    meta_path.write_text(json.dumps(meta, indent=2))

    print(f"Promoted '{args.name}' from execution {args.execution_id}")
    print(f"  Fixture: {fixture_path}")
    print(f"  Expected: severity={result['severity']}, trajectory_passed={result['trajectory_passed']}, "
          f"repeated_call_tickers={result['repeated_call_tickers']}")
    print("  Run `pytest tests/evals/test_promoted_cases.py` to verify it's wired up correctly.")


if __name__ == "__main__":
    main()
