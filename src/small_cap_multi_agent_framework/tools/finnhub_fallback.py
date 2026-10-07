"""
Finnhub Fallback Data Source
=============================

Fallback for price/quote and news data, used when yfinance can't provide
either. This is the one source in the fallback chain that needs an API key
(free to get, 60 calls/minute on Finnhub's free tier), so it's fully
opt-in: with no FINNHUB_API_KEY set, every function here just returns None
and the caller falls through to the next source or an honest "no data"
message - nothing is required to get the rest of the fallback chain (SEC
EDGAR for fundamentals) working.

The news fallback specifically exists because of a confirmed Yahoo-side
outage, not a per-ticker coverage gap: since ~2026-09-28, the endpoint
yfinance's `.news` posts to (finance.yahoo.com/xhr/ncp) 404s for every
ticker, including mega-caps like AAPL/TSLA/MSFT - verified directly via
yfinance's own debug mode, which shows the raw HTTP 404 before yfinance
silently swallows it into an empty list. This is Yahoo's bug, not ours,
and it isn't fixed by upgrading yfinance (confirmed against yfinance
1.7.0, the latest release, which still hits the same dead endpoint).
"""

import logging
import os
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional

import requests

logger = logging.getLogger(__name__)

_BASE_URL = "https://finnhub.io/api/v1"


def get_finnhub_quote(ticker: str) -> Optional[Dict[str, Any]]:
    """A real quote from Finnhub's free tier, or None if no API key is
    configured or the lookup fails/returns an unknown symbol. Never
    fabricates a price."""
    api_key = os.getenv("FINNHUB_API_KEY")
    if not api_key:
        return None

    try:
        resp = requests.get(
            f"{_BASE_URL}/quote",
            params={"symbol": ticker.upper(), "token": api_key},
            timeout=10,
        )
        if resp.status_code != 200:
            return None
        data = resp.json()
    except Exception as e:
        logger.warning(f"Finnhub quote fetch failed for {ticker}: {e}")
        return None

    price = data.get("c")
    if not price:
        return None

    return {
        "current_price": price,
        "prev_close": data.get("pc"),
        "day_high": data.get("h"),
        "day_low": data.get("l"),
        "open": data.get("o"),
    }


def get_finnhub_news(ticker: str, count: int = 5) -> Optional[List[Dict[str, Any]]]:
    """Real recent headlines from Finnhub's free company-news endpoint, or
    None if no API key is configured, the lookup fails, or there's
    genuinely no news in the lookback window. Returns raw article dicts
    (title/publisher/date/link) with no sentiment attached - the caller
    classifies headlines with this project's own finance-tuned VADER
    scorer, the same one used for yfinance-sourced news, so sentiment
    stays consistent regardless of which source supplied the headline."""
    api_key = os.getenv("FINNHUB_API_KEY")
    if not api_key:
        return None

    to_date = datetime.now(timezone.utc).date()
    from_date = to_date - timedelta(days=14)

    try:
        resp = requests.get(
            f"{_BASE_URL}/company-news",
            params={
                "symbol": ticker.upper(),
                "from": from_date.isoformat(),
                "to": to_date.isoformat(),
                "token": api_key,
            },
            timeout=10,
        )
        if resp.status_code != 200:
            return None
        data = resp.json()
    except Exception as e:
        logger.warning(f"Finnhub company-news fetch failed for {ticker}: {e}")
        return None

    if not isinstance(data, list) or not data:
        return None

    articles = []
    for item in data[:count]:
        headline = item.get("headline")
        if not headline:
            continue
        articles.append({
            "title": headline,
            "publisher": item.get("source") or "Unknown",
            "date": (
                datetime.fromtimestamp(item["datetime"], tz=timezone.utc).strftime("%Y-%m-%d")
                if item.get("datetime") else "Unknown date"
            ),
            "link": item.get("url") or "",
        })
    return articles or None
