"""
Tests for evals/thesis_consistency.py - checks that a BUY/HOLD/SELL call
actually follows from the real fundamentals it was given. Distinct from
grounding: a report can be 100% grounded (every number real) and still fail
this check if the conclusion doesn't match the data.
"""

from small_cap_multi_agent_framework.evals.thesis_consistency import (
    evaluate_thesis_consistency,
    compute_fundamental_score,
)


def _fundamentals(
    revenue_growth=10.0, earnings_growth=5.0, upside=20.0,
    net_margin=10.0, operating_margin=12.0, current_ratio=1.5, debt_equity=50.0,
):
    return f"""
Revenue Growth: {revenue_growth}%
Earnings Growth: {earnings_growth}%
Upside Potential: {upside}%
Net Margins: {net_margin}%
Operating Margins: {operating_margin}%
Current Ratio: {current_ratio}
Debt/Equity: {debt_equity}
"""


def _tool_call(ticker, result):
    return {
        "type": "tool_call",
        "timestamp": "2026-01-01T00:00:00",
        "tool_input": f'{{"ticker": "{ticker}", "query_type": "fundamental"}}',
        "result": result,
    }


def test_buy_call_with_strong_fundamentals_is_consistent():
    trace = [_tool_call("AAA", _fundamentals(revenue_growth=20, earnings_growth=25, upside=30))]
    report = "## AAA: Company\n**Investment Call:**\nBUY. Strong growth."
    result = evaluate_thesis_consistency(report, trace)
    assert result["inconsistent_tickers"] == []
    assert result["thesis_consistency_rate"] == 1.0


def test_sell_call_against_bullish_fundamentals_is_flagged():
    # The real case found live: a SELL call issued despite a strongly
    # positive fundamental picture (45%+ analyst upside, positive margins).
    trace = [_tool_call("VRX", _fundamentals(
        revenue_growth=10.5, upside=45.6, net_margin=0.5,
        operating_margin=3.4, current_ratio=0.87, debt_equity=145.13,
    ))]
    report = "## VRX: Company\n**Investment Call:**\nSELL. Overvalued."
    result = evaluate_thesis_consistency(report, trace)
    assert "VRX" in result["inconsistent_tickers"]


def test_buy_call_against_bearish_fundamentals_is_flagged():
    trace = [_tool_call("BAD", _fundamentals(
        revenue_growth=-20, earnings_growth=-30, upside=-15,
        net_margin=-25, operating_margin=-30, debt_equity=300,
    ))]
    report = "## BAD: Company\n**Investment Call:**\nBUY. Looks cheap."
    result = evaluate_thesis_consistency(report, trace)
    assert "BAD" in result["inconsistent_tickers"]


def test_hold_call_is_lenient_across_most_of_the_score_range():
    trace = [_tool_call("AAA", _fundamentals(
        revenue_growth=-20, earnings_growth=-20, upside=-10,
        net_margin=-15, operating_margin=-20,
    ))]
    report = "## AAA: Company\n**Investment Call:**\nHOLD. Mixed signals."
    result = evaluate_thesis_consistency(report, trace)
    assert result["inconsistent_tickers"] == []


def test_no_fundamental_data_marks_ticker_not_applicable_not_a_failure():
    trace = [_tool_call("ZZZ", "No fundamental data available for ZZZ")]
    report = "## ZZZ: Company\n**Investment Call:**\nHOLD. No data available."
    result = evaluate_thesis_consistency(report, trace)
    per_ticker = {t["ticker"]: t for t in result["per_ticker"]}
    assert per_ticker["ZZZ"]["applicable"] is False
    # Nothing applicable to check -> vacuously fine, not a failure.
    assert result["thesis_consistency_rate"] == 1.0
    assert result["inconsistent_tickers"] == []


def test_call_extraction_ignores_incidental_mention_in_news_section():
    # Same regression covered in test_report_parsing.py, verified again here
    # at the full-eval level: a "Buy" mentioned inside a news headline must
    # not be mistaken for the agent's real call when checking consistency.
    trace = [_tool_call("CDX", _fundamentals(
        revenue_growth=-2.7, earnings_growth=0, upside=10,
        net_margin=-39.6, operating_margin=-75.3, debt_equity=220.24,
    ))]
    report = """## CDX: Company
**News Sentiment:**
1. Zacks, which upgraded the stock to Buy, sees growth.

**Investment Call:**
SELL. Weak fundamentals despite the upgrade mention.
"""
    result = evaluate_thesis_consistency(report, trace)
    per_ticker = {t["ticker"]: t for t in result["per_ticker"]}
    assert per_ticker["CDX"]["call"] == "SELL"
    # SELL against genuinely bearish fundamentals is consistent - this must
    # NOT be flagged as "BUY vs. bearish" the way the pre-fix bug would.
    assert "CDX" not in result["inconsistent_tickers"]


def test_compute_fundamental_score_signals_are_explainable():
    score_info = compute_fundamental_score(_fundamentals(revenue_growth=20, earnings_growth=-5))
    names = [s[0] for s in score_info["signals"]]
    assert "Revenue Growth" in names
    assert "Earnings Growth" in names
    assert isinstance(score_info["score"], float)
