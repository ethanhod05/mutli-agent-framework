"""
Tests for the news sentiment classifier in hedge_fund_database.py - VADER
plus a small finance-jargon lexicon override, replacing the old 6-word
keyword list.
"""

from small_cap_multi_agent_framework.tools.hedge_fund_database import _classify_sentiment


def test_finance_jargon_override_flips_general_sentiment():
    # "crush" reads as generically negative to VADER's general lexicon, but
    # "crushed earnings views" is bullish - confirmed via a real headline
    # ("Micron Earnings Crush Views") that scored negative before the
    # finance-lexicon override was added.
    label, score = _classify_sentiment("Company Crushes Earnings Views")
    assert label == "Positive"
    assert score > 0


def test_downgrade_is_negative():
    label, score = _classify_sentiment("Analyst Downgrades Stock to Sell")
    assert label == "Negative"
    assert score < 0


def test_upgrade_is_positive():
    label, score = _classify_sentiment("Analyst Upgrades Stock on Strong Outlook")
    assert label == "Positive"
    assert score > 0


def test_neutral_headline_stays_neutral():
    label, score = _classify_sentiment("Company Announces Quarterly Earnings Call Date")
    assert label == "Neutral"
    assert -0.05 < score < 0.05
