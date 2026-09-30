#!/usr/bin/env python
"""
Grounding Eval CLI
==================

Checks a run's report against its trace: did every ticker and every number
in the report actually come from a real tool call? Defaults to the most
recent run.

Usage:
    python scripts/eval_grounding.py
    python scripts/eval_grounding.py --execution-id 20260930_180847

Exits non-zero if grounding is broken (an ungrounded ticker, or numeric
grounding below 80%), so this can gate CI or a future self-improving loop.
"""

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from small_cap_multi_agent_framework.evals.grounding import evaluate_grounding

NUMERIC_GROUNDING_THRESHOLD = 0.8


def find_latest_execution_id(output_dir: Path) -> str:
    traces = sorted((output_dir / "traces").glob("trace_*.json"))
    if not traces:
        raise FileNotFoundError(f"No trace files found in {output_dir / 'traces'}")
    return traces[-1].stem.replace("trace_", "")


def main():
    parser = argparse.ArgumentParser(description="Evaluate a report's grounding against its tool-call trace.")
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

    result = evaluate_grounding(report_text, trace["events"])

    print(f"Execution: {execution_id}")
    print(f"Ticker grounding: {result['ticker_grounding_rate'] * 100:.0f}% "
          f"({len(result['reported_tickers'])} tickers in report)")
    if result["ungrounded_tickers"]:
        print(f"  UNGROUNDED TICKERS (mentioned but never looked up via a real tool call): "
              f"{result['ungrounded_tickers']}")

    print(f"Numeric grounding: {result['numeric_grounding_rate'] * 100:.0f}% "
          f"of quoted numbers matched a real tool call result")
    for t in result["per_ticker"]:
        if t["unverified_numbers"]:
            print(f"  {t['ticker']}: unverified numbers {t['unverified_numbers']}")

    eval_file = output_dir / f"grounding_eval_{execution_id}.json"
    eval_file.write_text(json.dumps(result, indent=2))
    print(f"\nSaved: {eval_file}")

    grounding_failed = (
        bool(result["ungrounded_tickers"])
        or result["numeric_grounding_rate"] < NUMERIC_GROUNDING_THRESHOLD
    )
    sys.exit(1 if grounding_failed else 0)


if __name__ == "__main__":
    main()
