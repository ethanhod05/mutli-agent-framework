#!/usr/bin/env python
"""
Trajectory Eval CLI
====================

Grades the PATH an agent took during a run, not just its final output -
catching things grounding and thesis-consistency can't see, like an agent
calling the same tool repeatedly instead of once. Defaults to the most
recent run.

Usage:
    python scripts/eval_trajectory.py
    python scripts/eval_trajectory.py --execution-id 20261001_142145
"""

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from small_cap_multi_agent_framework.evals.trajectory import evaluate_trajectory


def find_latest_execution_id(output_dir: Path) -> str:
    traces = sorted((output_dir / "traces").glob("trace_*.json"))
    if not traces:
        raise FileNotFoundError(f"No trace files found in {output_dir / 'traces'}")
    return traces[-1].stem.replace("trace_", "")


def main():
    parser = argparse.ArgumentParser(description="Grade the path agents took during a run.")
    parser.add_argument("--execution-id", default=None, help="Execution ID to evaluate (default: latest)")
    parser.add_argument("--output-dir", default="output", help="Output directory (default: output)")
    args = parser.parse_args()

    output_dir = Path(args.output_dir)
    execution_id = args.execution_id or find_latest_execution_id(output_dir)

    trace_path = output_dir / "traces" / f"trace_{execution_id}.json"
    if not trace_path.exists():
        sys.exit(f"Trace file not found: {trace_path}")

    trace = json.loads(trace_path.read_text())
    result = evaluate_trajectory(trace["events"])

    print(f"Execution: {execution_id}")
    print(f"Trajectory: {result['severity'].upper()} ({result['total_tool_calls']} tool calls across "
          f"{result['total_tasks']} tasks)")
    if result["repeated_call_tickers"]:
        print(f"  Tickers with repeated/flagged calls: {result['repeated_call_tickers']}")

    for seg in result["segments"]:
        if seg["violations"]:
            status = seg["severity"].upper()
            print(f"  [{status}] {seg['agent']} ({seg['ticker'] or 'n/a'}) - "
                  f"{seg['tool_call_count']} call(s), completed={seg['completed']}")
            for v in seg["violations"]:
                print(f"      - {v}")

    eval_file = output_dir / f"trajectory_eval_{execution_id}.json"
    eval_file.write_text(json.dumps(result, indent=2))
    print(f"\nSaved: {eval_file}")

    sys.exit(0 if result["trajectory_passed"] else 1)


if __name__ == "__main__":
    main()
