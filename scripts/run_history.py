#!/usr/bin/env python
"""
Run History Viewer
===================

Prints a table of every run's grounding outcome over time, so you can see
whether prompt/tool changes are actually making the system more grounded -
the actual "self-improving" signal, made visible instead of just claimed.

Usage:
    python scripts/run_history.py
    python scripts/run_history.py --last 10
"""

import argparse
import json
from pathlib import Path


def main():
    parser = argparse.ArgumentParser(description="View run history and grounding trends.")
    parser.add_argument("--output-dir", default="output", help="Output directory (default: output)")
    parser.add_argument("--last", type=int, default=20, help="Show the last N runs (default: 20)")
    args = parser.parse_args()

    history_file = Path(args.output_dir) / "run_history.jsonl"
    if not history_file.exists():
        print(f"No run history yet at {history_file} - run the pipeline at least once first.")
        return

    records = [json.loads(line) for line in history_file.read_text().splitlines() if line.strip()]
    records = records[-args.last:]

    if not records:
        print("Run history file is empty.")
        return

    header = f"{'execution_id':<17} {'source':<22} {'tickers':>7} {'numbers':>7} {'thesis':>7} {'retry':>5} {'passed':>6}"
    print(header)
    print("-" * len(header))
    for r in records:
        source = (r.get('source') or '')[:22]
        tg = r.get('ticker_grounding_rate')
        ng = r.get('numeric_grounding_rate')
        tc = r.get('thesis_consistency_rate')
        print(
            f"{r['execution_id']:<17} {source:<22} "
            f"{f'{tg*100:.0f}%' if tg is not None else 'n/a':>7} "
            f"{f'{ng*100:.0f}%' if ng is not None else 'n/a':>7} "
            f"{f'{tc*100:.0f}%' if tc is not None else 'n/a':>7} "
            f"{'yes' if r.get('retried') else 'no':>5} "
            f"{'yes' if r.get('grounding_passed') else 'NO':>6}"
        )

    passed = sum(1 for r in records if r.get('grounding_passed'))
    retried = sum(1 for r in records if r.get('retried'))
    inconsistent = sum(1 for r in records if r.get('inconsistent_tickers'))
    print(f"\n{passed}/{len(records)} runs passed grounding ({retried} needed a retry to get there).")
    print(f"{len(records) - inconsistent}/{len(records)} runs had fully consistent theses.")


if __name__ == "__main__":
    main()
