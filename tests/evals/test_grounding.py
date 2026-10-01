"""
Tests for evals/grounding.py - the anti-hallucination check. These are
regression tests for the project's original bug class: an agent discussing a
ticker (or a number) that was never actually returned by a real tool call.
"""

from small_cap_multi_agent_framework.evals.grounding import evaluate_grounding


def _tool_call(ticker, result, query_type="fundamental"):
    return {
        "type": "tool_call",
        "timestamp": "2026-01-01T00:00:00",
        "tool": "query_institutional_database",
        "tool_input": f'{{"ticker": "{ticker}", "query_type": "{query_type}"}}',
        "result": result,
    }


def test_fully_grounded_report_scores_100_percent():
    trace = [_tool_call("AAPL", "Market Cap: $3,000,000,000,000, P/E Ratio: 30.5")]
    report = "## AAPL: Apple Inc\n- Market Cap: $3,000,000,000,000\n- P/E Ratio: 30.5\nCall: BUY"
    result = evaluate_grounding(report, trace)
    assert result["ticker_grounding_rate"] == 1.0
    assert result["numeric_grounding_rate"] == 1.0
    assert result["ungrounded_tickers"] == []


def test_hallucinated_ticker_is_flagged():
    # The original production bug: an agent recommending a ticker (BBBY) that
    # no tool call ever actually returned.
    trace = [_tool_call("AAPL", "Market Cap: $3,000,000,000,000")]
    report = (
        "## AAPL: Apple Inc\n- Market Cap: $3,000,000,000,000\nCall: BUY\n\n"
        "## BBBY: Bed Bath & Beyond\n- Market Cap: $50,000,000\nCall: SELL"
    )
    result = evaluate_grounding(report, trace)
    assert result["ungrounded_tickers"] == ["BBBY"]
    assert result["ticker_grounding_rate"] == 0.5


def test_fabricated_number_is_flagged_as_unverified():
    trace = [_tool_call("AAPL", "Market Cap: $3,000,000,000,000, P/E Ratio: 30.5")]
    report = "## AAPL: Apple Inc\n- Market Cap: $3,000,000,000,000\n- P/E Ratio: 999.99\nCall: BUY"
    result = evaluate_grounding(report, trace)
    per_ticker = {t["ticker"]: t for t in result["per_ticker"]}
    assert 999.99 in per_ticker["AAPL"]["unverified_numbers"]
    assert result["numeric_grounding_rate"] < 1.0


def test_csv_context_numbers_count_as_grounded_even_without_a_tool_call():
    # A data-quality task's description (e.g. a CSV's own market cap) is
    # legitimate ground truth too, not just live tool_call results.
    trace = [
        {
            "type": "task_complete",
            "timestamp": "2026-01-01T00:00:00",
            "agent": "Financial Data Quality Specialist",
            "description": "AAPL: Apple Inc | Tech | Market Cap $2,500,000,000",
            "raw_output": "OK",
        },
        _tool_call("AAPL", "P/E Ratio: 30.5"),
    ]
    report = "## AAPL: Apple Inc\n- Market Cap: $2,500,000,000\n- P/E Ratio: 30.5\nCall: HOLD"
    result = evaluate_grounding(report, trace)
    assert result["numeric_grounding_rate"] == 1.0


def test_fallback_parsing_when_no_heading_format_is_used():
    # A single-ticker report can be formatted as '# Report: AAPL' instead of
    # the expected '## AAPL: ...' heading - the eval must not silently report
    # a vacuous 100% by finding zero tickers to check.
    trace = [_tool_call("AAPL", "Market Cap: $3,000,000,000,000")]
    report = "# Investment Report: AAPL\nMarket Cap: $3,000,000,000,000\nCall: BUY"
    result = evaluate_grounding(report, trace)
    assert result["used_fallback_parsing"] is True
    assert "AAPL" in result["reported_tickers"]
    assert result["ticker_grounding_rate"] == 1.0


def test_fallback_parsing_still_catches_a_hallucinated_ticker():
    trace = [_tool_call("AAPL", "Market Cap: $3,000,000,000,000")]
    report = "# Report\nAAPL looks fine. We also like BBBY, Market Cap $50,000,000. Call: BUY"
    result = evaluate_grounding(report, trace)
    assert "BBBY" in result["ungrounded_tickers"]
