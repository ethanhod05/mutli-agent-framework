#!/usr/bin/env python
"""
Outcome Scorecard
=================

Checks real current prices against past BUY/HOLD/SELL calls that are old
enough to honestly score, and prints an accuracy scorecard. This is the
real "is the system good at picking stocks" signal - distinct from grounding
(is it honest) and thesis-consistency (is it internally coherent). A report
can pass both of those and still be wrong about the market; only time and a
real price check can tell you that.

Usage:
    python scripts/score_outcomes.py
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from small_cap_multi_agent_framework.evals.outcomes import score_outcomes, MIN_HOLD_DAYS


def main():
    path = Path("output") / "call_outcomes.jsonl"
    result = score_outcomes(path)

    print(f"Total calls logged: {result['total_logged']}")
    print(f"Too recent to score (< {MIN_HOLD_DAYS} days old): {result['too_recent_to_score']}")
    print(f"Newly scored this run: {result['newly_scored']}")
    print(f"Total scored overall: {result['total_scored']}")
    if result['accuracy'] is not None:
        print(f"Overall accuracy: {result['accuracy'] * 100:.0f}%")
    else:
        print("Overall accuracy: n/a (nothing scoreable yet - come back after calls are a week old)")

    scored = [r for r in result['results'] if 'correct' in r]
    if scored:
        print("\nScored calls:")
        for r in scored[-20:]:
            mark = "CORRECT" if r['correct'] else "WRONG"
            print(f"  [{mark}] {r['ticker']:6} {r['call']:4} ${r['price_at_call']:.2f} -> ${r['price_now']:.2f} "
                  f"({r['pct_change']:+.1f}%) after {r['days_held']}d")


if __name__ == "__main__":
    main()
