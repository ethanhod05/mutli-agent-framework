"""
Data-Source Health Check
=========================

Every other eval in this package grades something the agent produced
(grounding, thesis consistency, trajectory) - they all operate on a saved
trace, after the fact. This one is different: it's a live, ticker-agnostic
check of whether the underlying data sources themselves are actually
working right now, run against a canary ticker (AAPL - always liquid,
always covered, so any gap is the source's fault, not the ticker's).

This is the eval that would have caught the real 2026-09-28 incident
(Yahoo quietly broke yfinance's news endpoint for every ticker) on the
very next run, instead of a human noticing silence in the UI days later.
It checks each source independently, then combines each primary source
with its fallback into a per-capability verdict:

- "ok"       - the primary source itself is working
- "degraded" - the primary is down, but the fallback covers it (the
               system is still honest and functional, just one layer in)
- "fail"     - neither the primary nor the fallback has real data right
               now - a genuine blind spot, not just a downgrade

Hits real APIs, so this isn't meant to run on every pytest invocation -
see scripts/eval_data_health.py for a standalone CLI, and crew.py's
_validate_system_health for where it's wired into a live run (as a
non-blocking warning, not a hard stop - a degraded data source shouldn't
prevent an analysis, just be visible).
"""

import logging
import os
from datetime import datetime, timezone
from typing import Any, Dict

import yfinance as yf

from small_cap_multi_agent_framework.tools.sec_edgar import get_edgar_fundamentals
from small_cap_multi_agent_framework.tools.finnhub_fallback import get_finnhub_news, get_finnhub_quote

logger = logging.getLogger(__name__)

CANARY_TICKER = "AAPL"


def _check_yfinance_fundamentals(ticker: str) -> Dict[str, Any]:
    try:
        info = yf.Ticker(ticker).info
    except Exception as e:
        return {"status": "fail", "detail": f"exception: {e}"}

    has_real_data = (
        info
        and info.get("quoteType") not in (None, "NONE")
        and (info.get("currentPrice") or info.get("regularMarketPrice") or info.get("marketCap"))
    )
    if has_real_data:
        return {"status": "ok", "detail": "real fundamentals returned"}
    return {"status": "fail", "detail": "empty/degenerate info for a canary ticker that should always have data"}


def _check_yfinance_news(ticker: str) -> Dict[str, Any]:
    try:
        news = yf.Ticker(ticker).news
    except Exception as e:
        return {"status": "fail", "detail": f"exception: {e}"}

    if news:
        return {"status": "ok", "detail": f"{len(news)} articles returned"}
    return {"status": "fail", "detail": "0 articles for a canary ticker that should always have news"}


def _check_yfinance_market(ticker: str) -> Dict[str, Any]:
    try:
        hist = yf.Ticker(ticker).history(period="5d")
    except Exception as e:
        return {"status": "fail", "detail": f"exception: {e}"}

    if not hist.empty:
        return {"status": "ok", "detail": "price history returned"}
    return {"status": "fail", "detail": "no price history for a canary ticker that should always have one"}


def _check_sec_edgar_fundamentals(ticker: str) -> Dict[str, Any]:
    try:
        result = get_edgar_fundamentals(ticker)
    except Exception as e:
        return {"status": "fail", "detail": f"exception: {e}"}

    if result:
        return {"status": "ok", "detail": "real XBRL filings data returned"}
    return {"status": "fail", "detail": "no usable XBRL facts for a canary ticker that should always have them"}


def _check_finnhub_quote(ticker: str) -> Dict[str, Any]:
    if not os.getenv("FINNHUB_API_KEY"):
        return {"status": "skipped", "detail": "FINNHUB_API_KEY not configured"}
    try:
        result = get_finnhub_quote(ticker)
    except Exception as e:
        return {"status": "fail", "detail": f"exception: {e}"}

    if result:
        return {"status": "ok", "detail": "real quote returned"}
    return {"status": "fail", "detail": "no quote for a canary ticker that should always have one"}


def _check_finnhub_news(ticker: str) -> Dict[str, Any]:
    if not os.getenv("FINNHUB_API_KEY"):
        return {"status": "skipped", "detail": "FINNHUB_API_KEY not configured"}
    try:
        result = get_finnhub_news(ticker)
    except Exception as e:
        return {"status": "fail", "detail": f"exception: {e}"}

    if result:
        return {"status": "ok", "detail": f"{len(result)} articles returned"}
    return {"status": "fail", "detail": "0 articles for a canary ticker that should always have news"}


def _capability_status(primary: Dict[str, Any], fallback: Dict[str, Any]) -> Dict[str, Any]:
    """Combine one capability's primary-source status with its fallback's
    status into a single verdict. A 'skipped' fallback (no API key
    configured) counts the same as a down one here - if the primary is
    also down, there is genuinely no coverage right now, regardless of
    whether that's because the fallback failed or was never turned on."""
    if primary["status"] == "ok":
        return {"status": "ok", "via": "primary", "primary_detail": primary["detail"]}
    if fallback["status"] == "ok":
        return {
            "status": "degraded",
            "via": "fallback",
            "primary_detail": primary["detail"],
            "fallback_detail": fallback["detail"],
        }
    return {
        "status": "fail",
        "via": "none",
        "primary_detail": primary["detail"],
        "fallback_detail": fallback["detail"],
    }


def _overall_status(coverage: Dict[str, Dict[str, Any]]) -> str:
    statuses = {c["status"] for c in coverage.values()}
    if "fail" in statuses:
        return "fail"
    if "degraded" in statuses:
        return "degraded"
    return "ok"


def run_data_source_health_check(ticker: str = CANARY_TICKER) -> Dict[str, Any]:
    """Runs all source checks against a canary ticker and rolls them up
    into per-capability and overall verdicts. Safe to call often - every
    check is a single real request with its own exception handling, so one
    slow/erroring source can't take down the others or raise out of here."""
    sources = {
        "yfinance_fundamentals": _check_yfinance_fundamentals(ticker),
        "yfinance_news": _check_yfinance_news(ticker),
        "yfinance_market": _check_yfinance_market(ticker),
        "sec_edgar_fundamentals": _check_sec_edgar_fundamentals(ticker),
        "finnhub_quote": _check_finnhub_quote(ticker),
        "finnhub_news": _check_finnhub_news(ticker),
    }

    coverage = {
        "fundamentals": _capability_status(sources["yfinance_fundamentals"], sources["sec_edgar_fundamentals"]),
        "news": _capability_status(sources["yfinance_news"], sources["finnhub_news"]),
        "market": _capability_status(sources["yfinance_market"], sources["finnhub_quote"]),
    }

    return {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "canary_ticker": ticker,
        "sources": sources,
        "coverage": coverage,
        "overall": _overall_status(coverage),
    }
