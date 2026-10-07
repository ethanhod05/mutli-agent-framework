#!/usr/bin/env python
"""
Data-Source Health Check CLI
==============================

Live check of whether each real data source (yfinance, SEC EDGAR, Finnhub)
is actually returning real data right now, against a canary ticker - run
this periodically, or any time something feels off, to find out in seconds
rather than by noticing silence in the UI. This is the standalone version
of the same check crew.py runs (as a non-blocking warning) at the start of
every live analysis.

Usage:
    python scripts/eval_data_health.py
    python scripts/eval_data_health.py --ticker MSFT
"""

import argparse
import json
import sys
from datetime import datetime
from pathlib import Path

from dotenv import load_dotenv

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))
load_dotenv()

from small_cap_multi_agent_framework.evals.data_health import CANARY_TICKER, run_data_source_health_check


def main():
    parser = argparse.ArgumentParser(description="Check whether real data sources are actually working.")
    parser.add_argument("--ticker", default=CANARY_TICKER, help=f"Canary ticker to check against (default: {CANARY_TICKER})")
    parser.add_argument("--output-dir", default="output", help="Output directory (default: output)")
    args = parser.parse_args()

    result = run_data_source_health_check(args.ticker)

    print(f"Canary ticker: {result['canary_ticker']}")
    print(f"Checked at: {result['timestamp']}")
    print()
    print("SOURCES:")
    for name, check in result["sources"].items():
        print(f"  [{check['status'].upper():8}] {name}: {check['detail']}")
    print()
    print("CAPABILITIES:")
    for name, cap in result["coverage"].items():
        print(f"  [{cap['status'].upper():8}] {name} (via {cap['via']})")
        if cap["status"] != "ok":
            print(f"             primary: {cap['primary_detail']}")
        if cap["status"] == "fail":
            print(f"             fallback: {cap['fallback_detail']}")
    print()
    print(f"OVERALL: {result['overall'].upper()}")

    output_dir = Path(args.output_dir)
    output_dir.mkdir(exist_ok=True)
    out_file = output_dir / f"data_health_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    out_file.write_text(json.dumps(result, indent=2))
    print(f"\nSaved: {out_file}")

    # "degraded" means a fallback is actually covering the gap - visible,
    # not blocking. Only a genuine blind spot ("fail") fails this check.
    sys.exit(0 if result["overall"] != "fail" else 1)


if __name__ == "__main__":
    main()
