#!/usr/bin/env python
"""
Thesis Consistency Eval CLI
===========================

Checks whether a run's BUY/HOLD/SELL calls are directionally consistent with
the real fundamentals they were given - a different question from grounding
(evals/grounding.py), which only checks whether the numbers are real.
Defaults to the most recent run.

Usage:
    python scripts/eval_thesis.py
    python scripts/eval_thesis.py --execution-id 20260930_180847
"""

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from small_cap_multi_agent_framework.evals.thesis_consistency import evaluate_thesis_consistency


def find_latest_execution_id(output_dir: Path) -> str:
    traces = sorted((output_dir / "traces").glob("trace_*.json"))
    if not traces:
        raise FileNotFoundError(f"No trace files found in {output_dir / 'traces'}")
    return traces[-1].stem.replace("trace_", "")


def main():
    parser = argparse.ArgumentParser(description="Check a report's calls against their own fundamentals.")
    parser.add_argument("--execution-id", default=None, help="Execution ID to evaluate (default: latest)")
    parser.add_argument("--output-dir", default="output", help="Output directory (default: output)")
    args = parser.parse_args()

    output_dir = Path(args.output_dir)
    execution_id = args.execution_id or find_latest_execution_id(output_dir)

    trace_path = output_dir / "traces" / f"trace_{execution_id}.json"
    report_path = output_dir / f"alpha_investment_report_{execution_id}.md"

    if not trace_path.exists():
        sys.exit(f"Trace file not found: {trace_path}")
    if not report_path.exists():
        sys.exit(f"Report file not found: {report_path}")

    trace = json.loads(trace_path.read_text())
    report_text = report_path.read_text()

    result = evaluate_thesis_consistency(report_text, trace["events"])

    print(f"Execution: {execution_id}")
    print(f"Thesis consistency: {result['thesis_consistency_rate'] * 100:.0f}%")
    for t in result["per_ticker"]:
        if not t["applicable"]:
            print(f"  {t['ticker']}: n/a (no call or no real fundamentals to check against)")
        elif t["consistent"]:
            print(f"  {t['ticker']}: {t['call']} - consistent (score {t['fundamental_score']})")
        else:
            print(f"  {t['ticker']}: {t['call']} - INCONSISTENT - {t['reason']}")
            for name, value, weight in t["signals"]:
                print(f"      {name}: {value} (weight {weight:+.2f})")

    eval_file = output_dir / f"thesis_eval_{execution_id}.json"
    eval_file.write_text(json.dumps(result, indent=2))
    print(f"\nSaved: {eval_file}")

    sys.exit(1 if result["inconsistent_tickers"] else 0)


if __name__ == "__main__":
    main()
