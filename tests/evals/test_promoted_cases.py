"""
Promoted Regression Cases
===========================

Each fixture here is a REAL saved trace from a real incident, promoted via
scripts/promote_trace.py (see its docstring for why this is scoped to
structural/trajectory violations only, never data-accuracy ones). This
test is intentionally generic and data-driven - it doesn't know about any
specific case by name, so running the promotion script is enough to get a
regression test for the new case; no new test code needed here, ever.
"""

import json
from pathlib import Path

import pytest

from small_cap_multi_agent_framework.evals.trajectory import evaluate_trajectory

FIXTURES_DIR = Path(__file__).parent.parent / "fixtures" / "promoted_traces"


def _load_cases():
    if not FIXTURES_DIR.exists():
        return []
    return sorted(FIXTURES_DIR.glob("*.meta.json"))


@pytest.mark.parametrize("meta_path", _load_cases(), ids=lambda p: p.stem.replace(".meta", ""))
def test_promoted_case_still_matches_expected_trajectory(meta_path):
    meta = json.loads(meta_path.read_text())
    trace_path = meta_path.parent / f"{meta['case_name']}.json"
    trace = json.loads(trace_path.read_text())

    result = evaluate_trajectory(trace["events"])
    expected = meta["expected"]

    assert result["severity"] == expected["severity"], (
        f"{meta['case_name']}: expected severity '{expected['severity']}', got '{result['severity']}'. "
        f"Promoted because: {meta['reason']}"
    )
    assert result["trajectory_passed"] == expected["trajectory_passed"], (
        f"{meta['case_name']}: trajectory_passed regressed (expected {expected['trajectory_passed']}). "
        f"Promoted because: {meta['reason']}"
    )
    assert result["repeated_call_tickers"] == expected["repeated_call_tickers"], (
        f"{meta['case_name']}: repeated_call_tickers changed (expected {expected['repeated_call_tickers']}). "
        f"Promoted because: {meta['reason']}"
    )


def test_at_least_one_case_is_promoted():
    """A parametrize decorator over an empty list silently collects zero
    tests rather than failing - pytest won't complain on its own, so this
    exists to make a broken/empty promotion pipeline loud instead of
    quietly passing nothing."""
    assert len(_load_cases()) >= 1, "No promoted cases found - see scripts/promote_trace.py"
