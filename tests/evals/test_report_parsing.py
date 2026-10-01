"""
Tests for evals/_report_parsing.py - the shared ticker-section and
call-extraction helpers used by grounding.py, thesis_consistency.py, and
outcomes.py.

extract_call() in particular is a direct regression suite for a real,
confirmed bug: it used to grab the *first* BUY/HOLD/SELL word anywhere in a
ticker's section, which matched an incidental mention inside a quoted news
headline ("...upgraded to Buy") instead of the agent's actual verdict
further down. That bug had already corrupted a real thesis-eval result and
written a false call into call_outcomes.jsonl before it was caught by hand.
"""

from small_cap_multi_agent_framework.evals._report_parsing import ticker_section, extract_call


def test_ticker_section_extracts_the_right_block():
    report = "## AAA: Company A\nSome text about AAA.\n\n## BBB: Company B\nSome text about BBB."
    section = ticker_section(report, "BBB")
    assert "Company B" in section
    assert "Company A" not in section


def test_ticker_section_falls_back_to_whole_report_when_not_found():
    report = "## AAA: Company A\nSome text."
    assert ticker_section(report, "ZZZ") == report


def test_extract_call_finds_the_verdict_after_the_heading():
    section = """
    **Fundamental Metrics:** some numbers here.
    **Investment Call:**
    SELL. Rationale about weak fundamentals.
    """
    assert extract_call(section) == "SELL"


def test_extract_call_ignores_incidental_mentions_before_the_heading():
    # Regression test: this exact shape of report (a "Buy" mentioned inside a
    # quoted news headline, with the real verdict being SELL further down)
    # used to extract "BUY" instead of the agent's actual call.
    section = """
    **News Sentiment:**
    1. Zacks, which upgraded the stock to Buy, sees further growth.

    **Investment Call:**
    SELL. Despite the upgrade, fundamentals remain weak.
    """
    assert extract_call(section) == "SELL"


def test_extract_call_handles_recommendation_heading_variant():
    section = "**Recommendation:** HOLD\nMixed signals overall."
    assert extract_call(section) == "HOLD"


def test_extract_call_handles_bare_call_heading_variant():
    section = "**Call:**\nBUY. Strong fundamentals."
    assert extract_call(section) == "BUY"


def test_extract_call_falls_back_to_last_mention_with_no_heading():
    # No "**...Call:**" label exists at all in this section - the last
    # mention is more likely to be the conclusion than an earlier aside.
    section = "The stock was previously a Sell candidate but conditions have shifted and it's now a BUY."
    assert extract_call(section) == "BUY"


def test_extract_call_returns_none_when_no_call_present():
    section = "Just some fundamental metrics with no recommendation at all."
    assert extract_call(section) is None


def test_news_sentiment_heading_does_not_false_match_as_a_call_heading():
    # "**News Sentiment:**" must not be mistaken for a "**...call...**"
    # heading just because "sentiment" and "call" are both label-like words.
    section = """
    **News Sentiment:**
    Mixed coverage this week.
    **Investment Call:**
    HOLD.
    """
    assert extract_call(section) == "HOLD"
