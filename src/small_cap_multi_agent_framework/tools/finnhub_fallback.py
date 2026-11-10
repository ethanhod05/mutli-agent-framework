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
import re
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


_STOPWORDS = {
    "the", "a", "an", "and", "or", "of", "to", "in", "on", "for", "is", "are", "as", "at", "by",
    "with", "from", "its", "it", "this", "that", "be", "after", "over", "amid", "says", "said",
    "stock", "stocks", "shares", "share", "market", "today", "why", "how", "what", "will", "new",
    "inc", "corp", "co", "ltd", "company", "here", "your", "you", "up", "down", "more", "just",
}
# Ticker-agnostic markers of material, price-moving events. Generic corporate
# risk/event vocabulary only - nothing tied to any one company or story.
_MATERIAL_TERMS = (
    "probe", "investigat", "lawsuit", "sued", "class action", "class-action", "sec ", "doj", "fbi",
    "subpoena", "fraud", "scandal", "allegation", "alleged", "resign", "steps down", "fired",
    "ousted", "ceo", "cfo", "recall", "bankrupt", "default", "delist", "halt", "restate", "short seller",
    "downgrade", "upgrade", "guidance", "earnings", "acquire", "acquisition", "merger", "buyout",
    "offering", "dilution", "layoff", "ban", "sanction", "tariff", "export", "breach", "hack", "fda",
    "approval", "contract", "plunge", "surge", "soar", "tumble",
)


def _tokens(text: str) -> set:
    return {w for w in re.findall(r"[a-z0-9]+", text.lower()) if len(w) > 2 and w not in _STOPWORDS}


def _rank_articles(articles: List[Dict[str, Any]], ticker: str,
                   company_name: Optional[str], count: int) -> List[Dict[str, Any]]:
    """Pick the most decision-relevant `count` headlines from a raw feed.
    The feed is chronological and padded with listicles and market-wide
    pieces merely tagged with the ticker, so 'newest N' misses the real
    story. Score = relevance to this company + materiality + story volume
    (how many outlets are covering the same event) + mild recency, then
    greedily select while penalising near-duplicates for diversity."""
    ticker_l = ticker.lower()
    name_tokens = _tokens(company_name or "") - {ticker_l}
    now = datetime.now(timezone.utc).timestamp()

    prepared = []
    for a in articles:
        title = a["title"]
        low = title.lower()
        toks = _tokens(title)
        about = (
            ticker_l in toks
            or bool(name_tokens and name_tokens & toks)
        )
        prepared.append({**a, "_toks": toks, "_about": about, "_low": low})

    # Story volume: number of other articles sharing >=2 distinctive tokens.
    for a in prepared:
        a["_volume"] = sum(
            1 for b in prepared if b is not a and len(a["_toks"] & b["_toks"]) >= 2
        )
    max_vol = max((a["_volume"] for a in prepared), default=0) or 1

    for a in prepared:
        age_days = max(0.0, (now - a.get("_ts", now)) / 86400)
        material = sum(1 for t in _MATERIAL_TERMS if t in a["_low"])
        a["_score"] = (
            (3.0 if a["_about"] else 0.0)
            + min(material, 3) * 1.0
            + 3.0 * (a["_volume"] / max_vol)
            + max(0.0, 1.0 - age_days / 14)
        )

    chosen: List[Dict[str, Any]] = []
    pool = sorted(prepared, key=lambda x: x["_score"], reverse=True)
    while pool and len(chosen) < count:
        # Diversity: discount candidates overlapping heavily with picks.
        def adj(c):
            overlap = max((len(c["_toks"] & k["_toks"]) / max(1, len(c["_toks"] | k["_toks"]))
                           for k in chosen), default=0.0)
            return c["_score"] - 4.0 * overlap
        best = max(pool, key=adj)
        pool.remove(best)
        chosen.append(best)

    return [{k: v for k, v in a.items() if not k.startswith("_")} for a in chosen]


def get_finnhub_news(ticker: str, count: int = 5,
                     company_name: Optional[str] = None) -> Optional[List[Dict[str, Any]]]:
    """Real recent headlines from Finnhub's free company-news endpoint, or
    None if no API key is configured, the lookup fails, or there's
    genuinely no news in the lookback window. The full window is fetched
    and ranked for relevance/materiality (see _rank_articles) rather than
    truncated to the newest N. Returns raw article dicts
    (title/publisher/date/link) with no sentiment attached - the caller
    classifies headlines with this project's own finance-tuned VADER
    scorer, so sentiment stays consistent across sources."""
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
    seen = set()
    for item in data:
        headline = item.get("headline")
        if not headline or headline.lower() in seen:
            continue
        seen.add(headline.lower())
        ts = item.get("datetime")
        articles.append({
            "title": headline,
            "publisher": item.get("source") or "Unknown",
            "date": (
                datetime.fromtimestamp(ts, tz=timezone.utc).strftime("%Y-%m-%d")
                if ts else "Unknown date"
            ),
            "link": item.get("url") or "",
            "_ts": ts or datetime.now(timezone.utc).timestamp(),
        })
    if not articles:
        return None
    ranked = _rank_articles(articles, ticker, company_name, count)
    return ranked or None
