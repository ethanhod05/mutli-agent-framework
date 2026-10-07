"""
Run Trends
===========

Every eval we've built (grounding, thesis-consistency, trajectory,
data-source health) and the cost tracking in utils/cost.py all write their
verdict into a single run, one record at a time, in run_history.jsonl.
Nobody can tell "is this actually getting better" from reading one JSON
file at a time - that question needs an aggregate over many runs, which is
what this module computes.

Deliberately a pure function over already-loaded records, not a file
reader - keeps it trivially testable with synthetic data, and lets the
caller (webapp.py, or a future CLI) decide where the records come from.

The prompt-version breakdown is the sharpest tool here: since
config/agents.py's PROMPT_VERSION is bumped on every meaningful prompt/
guardrail change, grouping by it turns "did that change actually help"
from a guess into a before/after comparison with real numbers.
"""

from statistics import mean
from typing import Any, Dict, List, Optional


def _rate(records: List[dict], field: str) -> Optional[float]:
    """Fraction of records where `field` is truthy, among records where
    that field is present at all - a run from before an eval existed
    shouldn't silently count as a failure for it, or dilute the rate."""
    applicable = [r for r in records if r.get(field) is not None]
    if not applicable:
        return None
    return sum(1 for r in applicable if r[field]) / len(applicable)


def _average(records: List[dict], field: str) -> Optional[float]:
    values = [r[field] for r in records if r.get(field) is not None]
    return mean(values) if values else None


def _total(records: List[dict], field: str) -> Optional[float]:
    values = [r[field] for r in records if r.get(field) is not None]
    return sum(values) if values else None


def _summarize_group(records: List[dict]) -> Dict[str, Any]:
    return {
        "run_count": len(records),
        "grounding_pass_rate": _rate(records, "grounding_passed"),
        "thesis_pass_rate": _rate(records, "thesis_passed"),
        "trajectory_pass_rate": _rate(records, "trajectory_passed"),
        "avg_tool_calls": _average(records, "tool_calls_made"),
        "avg_elapsed_seconds": _average(records, "elapsed_seconds"),
        "total_estimated_cost_usd": _total(records, "estimated_cost_usd"),
        "avg_estimated_cost_usd": _average(records, "estimated_cost_usd"),
    }


def compute_trends(records: List[dict], window: int = 30) -> Dict[str, Any]:
    """`records` should be run_history.jsonl entries, oldest first (as
    they're appended) - only the most recent `window` are used. Returns an
    overall summary plus a breakdown grouped by prompt_version, so a
    before/after prompt-change comparison doesn't need to be computed by
    hand."""
    recent = records[-window:] if window else records

    by_version: Dict[str, List[dict]] = {}
    for r in recent:
        version = r.get("prompt_version") or "unknown"
        by_version.setdefault(version, []).append(r)

    return {
        "window": window,
        "overall": _summarize_group(recent),
        "by_prompt_version": {
            version: _summarize_group(group) for version, group in by_version.items()
        },
    }
