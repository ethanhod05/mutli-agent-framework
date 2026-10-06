"""
SEC EDGAR Fallback Data Source
===============================

yfinance's `.info` endpoint is an unofficial scrape of Yahoo's internal
quoteSummary API, and it's known to come back as an empty/degenerate shell
for thinly-traded small and micro caps (quoteType 'NONE', no price or market
cap at all) even when the company is actively filing with the SEC. When that
happens, this module queries the SEC's own free XBRL "company facts" API -
no key, no signup, no meaningful rate limit - which returns every financial
figure a company has ever tagged in its actual 10-K/10-Q filings.

This is a genuine fallback, not a replacement: it has no market-price-derived
figures (no P/E, no market cap, no analyst target) since those aren't facts
in a filing, only raw statement data (revenue, margins, balance sheet). We
pair it with a direct yfinance price-history call (separate from the broken
`.info` endpoint) to recover a real last price when one is available, so we
can still derive P/E and market cap when possible. If neither source has
real data, the caller falls through to an honest "no data available"
message - nothing here is ever fabricated or estimated.
"""

import json
import logging
import re
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import requests

logger = logging.getLogger(__name__)

# SEC's edge/bot filter rejects with a 403 unless the User-Agent is
# email-shaped (confirmed empirically - a plain descriptive string like
# "my-tool/1.0 (github.com/...)" gets blocked, "Name contact@domain" does
# not). This is a placeholder project contact, not a real personal address -
# SEC's policy only asks for *a* way to reach the requester, not that it be
# the end user's own email.
_USER_AGENT = "small-cap-multi-agent-framework contact@example.com"

_CIK_CACHE_PATH = Path("data/sec_ticker_cik_cache.json")
_CIK_CACHE_MAX_AGE_SECONDS = 7 * 24 * 3600

_ticker_to_cik: Optional[Dict[str, str]] = None


def _load_ticker_cik_map() -> Dict[str, str]:
    """SEC publishes a free, static ticker->CIK mapping. Cached to disk for
    a week since it rarely changes and re-downloading it on every ticker
    lookup would be wasteful."""
    global _ticker_to_cik
    if _ticker_to_cik is not None:
        return _ticker_to_cik

    if _CIK_CACHE_PATH.exists():
        age = time.time() - _CIK_CACHE_PATH.stat().st_mtime
        if age < _CIK_CACHE_MAX_AGE_SECONDS:
            _ticker_to_cik = json.loads(_CIK_CACHE_PATH.read_text())
            return _ticker_to_cik

    try:
        resp = requests.get(
            "https://www.sec.gov/files/company_tickers.json",
            headers={"User-Agent": _USER_AGENT},
            timeout=10,
        )
        resp.raise_for_status()
        raw = resp.json()
        mapping = {
            entry["ticker"].upper(): str(entry["cik_str"]).zfill(10)
            for entry in raw.values()
        }
        _CIK_CACHE_PATH.parent.mkdir(exist_ok=True)
        _CIK_CACHE_PATH.write_text(json.dumps(mapping))
        _ticker_to_cik = mapping
        return mapping
    except Exception as e:
        logger.warning(f"Could not refresh SEC ticker/CIK map: {e}")
        if _CIK_CACHE_PATH.exists():
            _ticker_to_cik = json.loads(_CIK_CACHE_PATH.read_text())
        else:
            _ticker_to_cik = {}
        return _ticker_to_cik


def _resolve_cik_via_browse_edgar(ticker: str) -> Optional[str]:
    """SEC's static company_tickers.json has real, confirmed gaps even for
    small caps that actively file 10-Ks (e.g. SMLR, CPRX, CARA, VLD are all
    absent from it) - it simply isn't an exhaustive registry. SEC's
    browse-edgar company-search endpoint, by contrast, resolves a raw
    ticker symbol straight to a CIK server-side, so it's used as a second
    attempt before giving up on a ticker."""
    try:
        resp = requests.get(
            "https://www.sec.gov/cgi-bin/browse-edgar",
            params={
                "action": "getcompany",
                "CIK": ticker,
                "type": "10-K",
                "dateb": "",
                "owner": "include",
                "count": "1",
                "output": "atom",
            },
            headers={"User-Agent": _USER_AGENT},
            timeout=10,
        )
        if resp.status_code != 200:
            return None
        match = re.search(r"<cik>(\d+)</cik>", resp.text)
        return match.group(1).zfill(10) if match else None
    except Exception as e:
        logger.warning(f"SEC browse-edgar CIK resolution failed for {ticker}: {e}")
        return None


def _get_cik(ticker: str) -> Optional[str]:
    ticker = ticker.upper()
    mapping = _load_ticker_cik_map()
    cik = mapping.get(ticker)
    if cik:
        return cik

    cik = _resolve_cik_via_browse_edgar(ticker)
    if cik:
        mapping[ticker] = cik
        try:
            _CIK_CACHE_PATH.parent.mkdir(exist_ok=True)
            _CIK_CACHE_PATH.write_text(json.dumps(mapping))
        except Exception:
            pass  # in-memory cache update below still helps this process
        global _ticker_to_cik
        _ticker_to_cik = mapping
    return cik


def _entries_for_tag(us_gaap: dict, *tags: str, unit_prefix: str = "USD") -> List[dict]:
    """Returns every reported value across ALL of the given alternative
    tags, merged into one list. Filers change which exact XBRL tag they use
    for the same concept over time - e.g. ASC 606 moved many companies from
    'Revenues' to 'RevenueFromContractWithCustomerExcludingAssessedTax'
    around 2018-2019 - so stopping at the first tag that exists at all
    would silently freeze on whichever tag the filer happened to use in its
    OLDEST filings (confirmed against a real filer: CPRX's 'Revenues' tag
    only has data through 2020, years out of date, while its real recent
    revenue lives under the newer tag). Merging means _latest_annual/
    _latest_instant always see the actual most recent figure regardless of
    which tag it was reported under."""
    merged: List[dict] = []
    for tag in tags:
        concept = us_gaap.get(tag)
        if not concept:
            continue
        units = concept.get("units", {})
        matched = False
        for unit_name, entries in units.items():
            if unit_prefix == "" or unit_name.startswith(unit_prefix):
                merged.extend(entries)
                matched = True
        if not matched and units:
            merged.extend(next(iter(units.values())))
    return merged


def _latest_annual(entries: List[dict]) -> Optional[Tuple[float, str]]:
    """Most recent full-year (10-K, fiscal-period 'FY') value, which is what
    an income-statement figure like revenue needs to mean the same thing as
    yfinance's trailing-twelve-month figures. Falls back to the single most
    recent entry of any form if the filer has no 10-K on record yet (e.g. a
    recent IPO) - still real, just possibly a quarterly, not annual, figure."""
    annual = [e for e in entries if e.get("form", "").startswith("10-K") and e.get("fp") == "FY"]
    pool = annual if annual else entries
    if not pool:
        return None
    best = max(pool, key=lambda e: e.get("end", ""))
    return best.get("val"), best.get("end")


def _latest_instant(entries: List[dict]) -> Optional[float]:
    """Most recent point-in-time value (balance-sheet items like Assets or
    shares outstanding aren't 'annual' or 'quarterly' - they're a snapshot as
    of a given filing date, so the newest one is simply the newest one)."""
    if not entries:
        return None
    best = max(entries, key=lambda e: e.get("end", ""))
    return best.get("val")


def _annual_growth(entries: List[dict]) -> Optional[float]:
    """Year-over-year growth from the two most recent distinct 10-K annual
    figures, or None if there aren't at least two to compare."""
    annual = sorted(
        {e.get("end"): e.get("val") for e in entries if e.get("form", "").startswith("10-K") and e.get("fp") == "FY"}.items()
    )
    if len(annual) < 2:
        return None
    (_, prior), (_, latest) = annual[-2], annual[-1]
    if not prior:
        return None
    return (latest - prior) / abs(prior)


def get_edgar_fundamentals(ticker: str) -> Optional[Dict[str, Any]]:
    """Raw fundamentals from SEC's free XBRL company-facts API, or None if
    this ticker isn't in SEC's filer map or has no usable XBRL facts (e.g. a
    foreign private issuer that doesn't file XBRL the same way). Returning
    None here is the honest signal to the caller to fall through to a
    'no data available' message, not an error to paper over."""
    cik = _get_cik(ticker)
    if not cik:
        return None

    try:
        resp = requests.get(
            f"https://data.sec.gov/api/xbrl/companyfacts/CIK{cik}.json",
            headers={"User-Agent": _USER_AGENT},
            timeout=10,
        )
        if resp.status_code != 200:
            return None
        facts = resp.json()
    except Exception as e:
        logger.warning(f"SEC EDGAR companyfacts fetch failed for {ticker}: {e}")
        return None

    us_gaap = facts.get("facts", {}).get("us-gaap", {})
    if not us_gaap:
        return None

    revenue_entries = _entries_for_tag(
        us_gaap, "Revenues", "RevenueFromContractWithCustomerExcludingAssessedTax", "SalesRevenueNet"
    )
    net_income_entries = _entries_for_tag(us_gaap, "NetIncomeLoss")
    gross_profit_entries = _entries_for_tag(us_gaap, "GrossProfit")
    operating_income_entries = _entries_for_tag(us_gaap, "OperatingIncomeLoss")

    revenue = _latest_annual(revenue_entries)
    net_income = _latest_annual(net_income_entries)
    gross_profit = _latest_annual(gross_profit_entries)
    operating_income = _latest_annual(operating_income_entries)

    assets = _latest_instant(_entries_for_tag(us_gaap, "Assets"))
    liabilities = _latest_instant(_entries_for_tag(us_gaap, "Liabilities"))
    equity = _latest_instant(_entries_for_tag(us_gaap, "StockholdersEquity"))
    cash = _latest_instant(_entries_for_tag(
        us_gaap, "CashAndCashEquivalentsAtCarryingValue",
        "CashAndCashEquivalentsAtCarryingValueIncludingDiscontinuedOperations",
    ))
    current_assets = _latest_instant(_entries_for_tag(us_gaap, "AssetsCurrent"))
    current_liabilities = _latest_instant(_entries_for_tag(us_gaap, "LiabilitiesCurrent"))
    long_term_debt = _latest_instant(_entries_for_tag(us_gaap, "LongTermDebtNoncurrent", "LongTermDebt"))
    short_term_debt = _latest_instant(_entries_for_tag(us_gaap, "DebtCurrent", "ShortTermBorrowings"))
    shares_outstanding = _latest_instant(_entries_for_tag(us_gaap, "CommonStockSharesOutstanding", unit_prefix="shares"))
    eps_diluted = _latest_annual(_entries_for_tag(us_gaap, "EarningsPerShareDiluted", unit_prefix="USD/shares"))

    if revenue is None and net_income is None and assets is None:
        return None

    total_debt = None
    if long_term_debt is not None or short_term_debt is not None:
        total_debt = (long_term_debt or 0) + (short_term_debt or 0)

    if revenue:
        as_of = revenue[1]
    elif net_income:
        as_of = net_income[1]
    else:
        as_of = None

    return {
        "as_of": as_of,
        "revenue": revenue[0] if revenue else None,
        "revenue_growth": _annual_growth(revenue_entries),
        "net_income": net_income[0] if net_income else None,
        "earnings_growth": _annual_growth(net_income_entries),
        "gross_profit": gross_profit[0] if gross_profit else None,
        "operating_income": operating_income[0] if operating_income else None,
        "assets": assets,
        "liabilities": liabilities,
        "equity": equity,
        "cash": cash,
        "current_assets": current_assets,
        "current_liabilities": current_liabilities,
        "total_debt": total_debt,
        "shares_outstanding": shares_outstanding,
        "eps_diluted": eps_diluted[0] if eps_diluted else None,
    }
