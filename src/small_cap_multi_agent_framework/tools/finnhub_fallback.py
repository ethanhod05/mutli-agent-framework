"""
Finnhub Fallback Data Source
=============================

Secondary fallback for price/quote data, used when yfinance has no price
for a ticker - typically the same thinly-traded small caps where its
`.info` endpoint is also empty. This is the one source in the fallback
chain that needs an API key (free to get, 60 calls/minute on Finnhub's free
tier), so it's fully opt-in: with no FINNHUB_API_KEY set, every function
here just returns None and the caller falls through to the next source or
an honest "no data" message - nothing is required to get the rest of the
fallback chain (SEC EDGAR) working.
"""

import logging
import os
from typing import Any, Dict, Optional

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
