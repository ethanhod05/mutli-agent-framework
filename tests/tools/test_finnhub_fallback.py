"""
Tests for the Finnhub fallback (finnhub_fallback.py). No real network calls.
"""

from unittest.mock import patch, MagicMock

from small_cap_multi_agent_framework.tools import finnhub_fallback


class TestGetFinnhubQuote:
    def test_returns_none_when_no_api_key_configured(self, monkeypatch):
        monkeypatch.delenv("FINNHUB_API_KEY", raising=False)
        assert finnhub_fallback.get_finnhub_quote("AAPL") is None

    def test_returns_none_on_non_200_response(self, monkeypatch):
        monkeypatch.setenv("FINNHUB_API_KEY", "fake-key")
        mock_resp = MagicMock(status_code=500)
        with patch("small_cap_multi_agent_framework.tools.finnhub_fallback.requests.get", return_value=mock_resp):
            assert finnhub_fallback.get_finnhub_quote("AAPL") is None

    def test_returns_none_when_price_is_zero_unknown_symbol(self, monkeypatch):
        monkeypatch.setenv("FINNHUB_API_KEY", "fake-key")
        mock_resp = MagicMock(status_code=200)
        mock_resp.json.return_value = {"c": 0, "pc": 0, "h": 0, "l": 0, "o": 0}
        with patch("small_cap_multi_agent_framework.tools.finnhub_fallback.requests.get", return_value=mock_resp):
            assert finnhub_fallback.get_finnhub_quote("NOSUCHTICKER") is None

    def test_returns_quote_on_success(self, monkeypatch):
        monkeypatch.setenv("FINNHUB_API_KEY", "fake-key")
        mock_resp = MagicMock(status_code=200)
        mock_resp.json.return_value = {"c": 12.5, "pc": 12.0, "h": 13.0, "l": 11.5, "o": 12.1}
        with patch("small_cap_multi_agent_framework.tools.finnhub_fallback.requests.get", return_value=mock_resp):
            result = finnhub_fallback.get_finnhub_quote("TINY")

        assert result == {
            "current_price": 12.5,
            "prev_close": 12.0,
            "day_high": 13.0,
            "day_low": 11.5,
            "open": 12.1,
        }

    def test_network_exception_returns_none(self, monkeypatch):
        monkeypatch.setenv("FINNHUB_API_KEY", "fake-key")
        with patch(
            "small_cap_multi_agent_framework.tools.finnhub_fallback.requests.get",
            side_effect=ConnectionError("boom"),
        ):
            assert finnhub_fallback.get_finnhub_quote("AAPL") is None
