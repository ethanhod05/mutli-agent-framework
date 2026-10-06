"""
Tests for the SEC EDGAR fallback (sec_edgar.py).

No real network calls - requests.get is always mocked, since this is meant
to run in CI/offline. The one thing worth testing for real is that the
helper functions correctly pick annual-vs-quarterly entries and compute
growth, since that logic is exactly what a real XBRL payload will exercise.
"""

import json
from unittest.mock import patch, MagicMock

import pytest

from small_cap_multi_agent_framework.tools import sec_edgar


def _entry(val, end, form="10-K", fp="FY", start="2022-01-01"):
    return {"val": val, "end": end, "form": form, "fp": fp, "start": start}


class TestLatestAnnual:
    def test_prefers_10k_over_10q(self):
        entries = [
            _entry(100, "2023-12-31", form="10-K", fp="FY"),
            _entry(40, "2024-03-31", form="10-Q", fp="Q1"),
        ]
        val, end = sec_edgar._latest_annual(entries)
        assert val == 100
        assert end == "2023-12-31"

    def test_falls_back_to_any_form_when_no_10k_exists(self):
        entries = [_entry(40, "2024-03-31", form="10-Q", fp="Q1")]
        val, end = sec_edgar._latest_annual(entries)
        assert val == 40

    def test_empty_entries_returns_none(self):
        assert sec_edgar._latest_annual([]) is None

    def test_picks_most_recent_of_multiple_10ks(self):
        entries = [
            _entry(80, "2022-12-31"),
            _entry(100, "2023-12-31"),
        ]
        val, end = sec_edgar._latest_annual(entries)
        assert val == 100


class TestLatestInstant:
    def test_picks_most_recent_snapshot(self):
        entries = [
            _entry(500, "2022-12-31", form="10-K"),
            _entry(600, "2023-12-31", form="10-K"),
        ]
        assert sec_edgar._latest_instant(entries) == 600

    def test_empty_returns_none(self):
        assert sec_edgar._latest_instant([]) is None


class TestAnnualGrowth:
    def test_computes_yoy_growth(self):
        entries = [
            _entry(100, "2022-12-31"),
            _entry(150, "2023-12-31"),
        ]
        growth = sec_edgar._annual_growth(entries)
        assert growth == 0.5

    def test_handles_negative_prior_value(self):
        entries = [
            _entry(-100, "2022-12-31"),
            _entry(-50, "2023-12-31"),
        ]
        growth = sec_edgar._annual_growth(entries)
        assert growth == 0.5  # (-50 - -100) / abs(-100)

    def test_single_annual_entry_returns_none(self):
        entries = [_entry(100, "2023-12-31")]
        assert sec_edgar._annual_growth(entries) is None

    def test_no_annual_entries_returns_none(self):
        entries = [_entry(100, "2024-03-31", form="10-Q", fp="Q1")]
        assert sec_edgar._annual_growth(entries) is None

    def test_zero_prior_value_returns_none(self):
        entries = [
            _entry(0, "2022-12-31"),
            _entry(50, "2023-12-31"),
        ]
        assert sec_edgar._annual_growth(entries) is None


class TestGetCik:
    def test_returns_none_when_ticker_not_in_map_and_browse_edgar_also_fails(self):
        with patch.object(sec_edgar, "_load_ticker_cik_map", return_value={"AAPL": "0000320193"}), \
             patch.object(sec_edgar, "_resolve_cik_via_browse_edgar", return_value=None):
            assert sec_edgar._get_cik("NOTATICKER") is None

    def test_returns_cik_for_known_ticker_without_hitting_browse_edgar(self):
        with patch.object(sec_edgar, "_load_ticker_cik_map", return_value={"AAPL": "0000320193"}), \
             patch.object(sec_edgar, "_resolve_cik_via_browse_edgar") as mock_browse:
            assert sec_edgar._get_cik("aapl") == "0000320193"
            mock_browse.assert_not_called()

    def test_falls_back_to_browse_edgar_when_static_map_is_missing_ticker(self, tmp_path, monkeypatch):
        cache_path = tmp_path / "cik_cache.json"
        monkeypatch.setattr(sec_edgar, "_CIK_CACHE_PATH", cache_path)
        with patch.object(sec_edgar, "_load_ticker_cik_map", return_value={"AAPL": "0000320193"}), \
             patch.object(sec_edgar, "_resolve_cik_via_browse_edgar", return_value="0001554859"):
            assert sec_edgar._get_cik("SMLR") == "0001554859"
        # the resolved CIK should be persisted so the next lookup is free
        assert json.loads(cache_path.read_text())["SMLR"] == "0001554859"


class TestGetEdgarFundamentals:
    def test_returns_none_when_ticker_has_no_cik(self):
        with patch.object(sec_edgar, "_get_cik", return_value=None):
            assert sec_edgar.get_edgar_fundamentals("NOSUCHTICKER") is None

    def test_returns_none_on_non_200_response(self):
        mock_resp = MagicMock(status_code=404)
        with patch.object(sec_edgar, "_get_cik", return_value="0000320193"), \
             patch("small_cap_multi_agent_framework.tools.sec_edgar.requests.get", return_value=mock_resp):
            assert sec_edgar.get_edgar_fundamentals("FAKE") is None

    def test_returns_none_when_no_us_gaap_facts(self):
        mock_resp = MagicMock(status_code=200)
        mock_resp.json.return_value = {"facts": {}}
        with patch.object(sec_edgar, "_get_cik", return_value="0000320193"), \
             patch("small_cap_multi_agent_framework.tools.sec_edgar.requests.get", return_value=mock_resp):
            assert sec_edgar.get_edgar_fundamentals("FAKE") is None

    def test_parses_a_realistic_companyfacts_payload(self):
        payload = {
            "facts": {
                "us-gaap": {
                    "Revenues": {
                        "units": {"USD": [
                            _entry(900, "2022-12-31"),
                            _entry(1000, "2023-12-31"),
                        ]}
                    },
                    "NetIncomeLoss": {
                        "units": {"USD": [_entry(50, "2023-12-31")]}
                    },
                    "Assets": {
                        "units": {"USD": [_entry(2000, "2023-12-31")]}
                    },
                    "StockholdersEquity": {
                        "units": {"USD": [_entry(800, "2023-12-31")]}
                    },
                    "CommonStockSharesOutstanding": {
                        "units": {"shares": [_entry(10_000_000, "2023-12-31")]}
                    },
                    "EarningsPerShareDiluted": {
                        "units": {"USD/shares": [_entry(5.0, "2023-12-31")]}
                    },
                }
            }
        }
        mock_resp = MagicMock(status_code=200)
        mock_resp.json.return_value = payload
        with patch.object(sec_edgar, "_get_cik", return_value="0000320193"), \
             patch("small_cap_multi_agent_framework.tools.sec_edgar.requests.get", return_value=mock_resp):
            result = sec_edgar.get_edgar_fundamentals("FAKE")

        assert result is not None
        assert result["revenue"] == 1000
        assert result["revenue_growth"] == pytest.approx(100 / 900)
        assert result["net_income"] == 50
        assert result["assets"] == 2000
        assert result["equity"] == 800
        assert result["shares_outstanding"] == 10_000_000
        assert result["eps_diluted"] == 5.0
        assert result["as_of"] == "2023-12-31"

    def test_returns_none_when_core_figures_all_missing(self):
        payload = {"facts": {"us-gaap": {"SomeUnrelatedTag": {"units": {"USD": [_entry(1, "2023-12-31")]}}}}}
        mock_resp = MagicMock(status_code=200)
        mock_resp.json.return_value = payload
        with patch.object(sec_edgar, "_get_cik", return_value="0000320193"), \
             patch("small_cap_multi_agent_framework.tools.sec_edgar.requests.get", return_value=mock_resp):
            assert sec_edgar.get_edgar_fundamentals("FAKE") is None
