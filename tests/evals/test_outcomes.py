"""
Tests for evals/outcomes.py - logging real calls with their real price at
call time, and scoring them only once enough real time has passed.
"""

import json
from datetime import datetime, timedelta

from small_cap_multi_agent_framework.evals.outcomes import (
    extract_calls_for_logging,
    score_outcomes,
    MIN_HOLD_DAYS,
)


def _tool_call(ticker, result):
    return {
        "type": "tool_call",
        "timestamp": "2026-01-01T00:00:00",
        "tool_input": f'{{"ticker": "{ticker}", "query_type": "fundamental"}}',
        "result": result,
    }


def test_extract_calls_for_logging_pulls_real_ticker_call_and_price():
    trace = [_tool_call("AAA", "Current Price: $50.00")]
    report = "## AAA: Company\n**Investment Call:**\nBUY."
    records = extract_calls_for_logging(report, trace, "exec1")
    assert len(records) == 1
    assert records[0]["ticker"] == "AAA"
    assert records[0]["call"] == "BUY"
    assert records[0]["price_at_call"] == 50.0


def test_zero_price_is_never_logged():
    # Regression test: the underlying tool defaults a missing price field to
    # literal 0 instead of omitting it (confirmed in production for AGFY).
    # A $0.00 "price" must never be logged as a real call-time price.
    trace = [_tool_call("AGFY", "Current Price: $0.00")]
    report = "## AGFY: Company\n**Investment Call:**\nSELL."
    records = extract_calls_for_logging(report, trace, "exec1")
    assert records == []


def test_ticker_with_no_call_is_not_logged():
    trace = [_tool_call("AAA", "Current Price: $50.00")]
    report = "## AAA: Company\nJust some metrics, no call stated."
    records = extract_calls_for_logging(report, trace, "exec1")
    assert records == []


def test_call_extraction_in_logging_ignores_incidental_mentions():
    trace = [_tool_call("CDX", "Current Price: $1.36")]
    report = """## CDX: Company
**News Sentiment:**
1. Upgraded to Buy by an analyst.

**Investment Call:**
SELL.
"""
    records = extract_calls_for_logging(report, trace, "exec1")
    assert records[0]["call"] == "SELL"


def test_score_outcomes_leaves_recent_calls_unscored(tmp_path):
    path = tmp_path / "outcomes.jsonl"
    today = datetime.now().strftime("%Y-%m-%d")
    path.write_text(json.dumps({
        "execution_id": "exec1", "ticker": "AAA", "call": "BUY",
        "price_at_call": 50.0, "call_date": today, "logged_at": datetime.now().isoformat(),
    }) + "\n")

    result = score_outcomes(path)
    assert result["too_recent_to_score"] == 1
    assert result["total_scored"] == 0
    assert result["accuracy"] is None


def test_score_outcomes_scores_old_enough_buy_call_correctly(tmp_path, monkeypatch):
    path = tmp_path / "outcomes.jsonl"
    old_date = (datetime.now() - timedelta(days=MIN_HOLD_DAYS + 1)).strftime("%Y-%m-%d")
    path.write_text(json.dumps({
        "execution_id": "exec1", "ticker": "AAA", "call": "BUY",
        "price_at_call": 50.0, "call_date": old_date, "logged_at": datetime.now().isoformat(),
    }) + "\n")

    import small_cap_multi_agent_framework.evals.outcomes as outcomes_module
    monkeypatch.setattr(outcomes_module, "_fetch_current_price", lambda ticker: 60.0)

    result = score_outcomes(path)
    assert result["total_scored"] == 1
    assert result["accuracy"] == 1.0  # BUY + price went up = correct
    scored = result["results"][0]
    assert scored["correct"] is True
    assert scored["pct_change"] == 20.0


def test_score_outcomes_marks_a_wrong_sell_call_incorrect(tmp_path, monkeypatch):
    path = tmp_path / "outcomes.jsonl"
    old_date = (datetime.now() - timedelta(days=MIN_HOLD_DAYS + 1)).strftime("%Y-%m-%d")
    path.write_text(json.dumps({
        "execution_id": "exec1", "ticker": "BBB", "call": "SELL",
        "price_at_call": 50.0, "call_date": old_date, "logged_at": datetime.now().isoformat(),
    }) + "\n")

    import small_cap_multi_agent_framework.evals.outcomes as outcomes_module
    monkeypatch.setattr(outcomes_module, "_fetch_current_price", lambda ticker: 60.0)

    result = score_outcomes(path)
    assert result["results"][0]["correct"] is False  # SELL but price rose


def test_score_outcomes_never_rescores_an_already_scored_call(tmp_path, monkeypatch):
    path = tmp_path / "outcomes.jsonl"
    old_date = (datetime.now() - timedelta(days=MIN_HOLD_DAYS + 1)).strftime("%Y-%m-%d")
    path.write_text(json.dumps({
        "execution_id": "exec1", "ticker": "AAA", "call": "BUY", "price_at_call": 50.0,
        "call_date": old_date, "logged_at": datetime.now().isoformat(),
        "price_now": 999.0, "pct_change": 1800.0, "days_held": 999, "correct": True,
        "scored_at": datetime.now().isoformat(),
    }) + "\n")

    import small_cap_multi_agent_framework.evals.outcomes as outcomes_module
    fetched = []
    monkeypatch.setattr(outcomes_module, "_fetch_current_price", lambda ticker: fetched.append(ticker) or 1.0)

    result = score_outcomes(path)
    assert fetched == []  # never re-fetched - already scored
    assert result["results"][0]["price_now"] == 999.0  # untouched
