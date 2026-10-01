"""
Outcome Tracking
================

Grounding checks whether a report is honest; thesis-consistency checks
whether it's internally coherent. Neither checks whether the system is
actually any good at picking stocks - that requires waiting to see what the
price actually did. This module is that: log every BUY/HOLD/SELL call with
the real price at call time, then later check the real price again and
record whether the call was directionally right.

A call is left unscored until a minimum holding period has passed - there is
no honest way to grade a call made five minutes ago. Scoring is a separate,
explicit step (score_outcomes), not something that happens automatically at
report time, because it depends on real elapsed calendar time, not on
anything the pipeline itself can produce faster by trying harder.
"""

import json
import re
from datetime import datetime
from pathlib import Path

import yfinance as yf

MIN_HOLD_DAYS = 7
HOLD_BAND_PCT = 5.0  # a HOLD is scored "correct" if price moved less than this either way

CALL_RE = re.compile(r"\b(BUY|HOLD|SELL)\b", re.IGNORECASE)
TICKER_HEADING_RE = re.compile(r"^##\s*([A-Z][A-Z.\-]{0,5})\b", re.MULTILINE)
TICKER_INPUT_RE = re.compile(r'"ticker"\s*:\s*"([A-Z.\-]+)"')
PRICE_RE = re.compile(r"Current Price[:\s]+\$?(-?[\d,]+\.?\d*)", re.IGNORECASE)


def _ticker_section(report_text: str, ticker: str) -> str:
    pattern = re.compile(
        rf"##\s*{re.escape(ticker)}\b.*?(?=\n##\s|\Z)", re.DOTALL | re.IGNORECASE
    )
    match = pattern.search(report_text)
    return match.group(0) if match else report_text


def _fundamentals_text_for_ticker(trace_events: list, ticker: str) -> str:
    for event in trace_events:
        if event.get("type") != "tool_call":
            continue
        tool_input = event.get("tool_input") or ""
        if "fundamental" not in tool_input:
            continue
        m = TICKER_INPUT_RE.search(tool_input)
        if m and m.group(1) == ticker:
            return event.get("result", "")
    return ""


def extract_calls_for_logging(report_text: str, trace_events: list, execution_id: str) -> list:
    """One loggable record per ticker with both a real call and a real
    price-at-call - pulled verbatim from the report/trace, nothing invented.
    A ticker with no call, or no real price (e.g. thin-coverage tickers with
    no fundamental data), is simply not logged - there's nothing honest to
    log for it.
    """
    tickers = sorted(set(TICKER_HEADING_RE.findall(report_text)))
    records = []
    for ticker in tickers:
        section = _ticker_section(report_text, ticker)
        call_match = CALL_RE.search(section)
        if not call_match:
            continue

        fundamentals_text = _fundamentals_text_for_ticker(trace_events, ticker)
        price_match = PRICE_RE.search(fundamentals_text)
        if not price_match:
            continue

        # The underlying tool defaults a missing price field to 0 rather than
        # omitting it (hedge_fund_database.py's `info.get(..., 0)`), so a
        # literal "$0.00" in the text means "no real price", not a real price
        # of zero. Never log that as an actual call-time price.
        price_at_call = float(price_match.group(1).replace(",", ""))
        if price_at_call <= 0:
            continue

        records.append({
            "execution_id": execution_id,
            "ticker": ticker,
            "call": call_match.group(1).upper(),
            "price_at_call": price_at_call,
            "call_date": datetime.now().strftime("%Y-%m-%d"),
            "logged_at": datetime.now().isoformat(),
        })
    return records


def log_outcomes(records: list, path: Path) -> None:
    if not records:
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "a") as f:
        for record in records:
            f.write(json.dumps(record) + "\n")


def _fetch_current_price(ticker: str):
    try:
        hist = yf.Ticker(ticker).history(period="5d")
        return float(hist["Close"].iloc[-1]) if not hist.empty else None
    except Exception:
        return None


def score_outcomes(path: Path, min_hold_days: int = MIN_HOLD_DAYS) -> dict:
    """Score every logged call old enough to honestly grade, using a real
    current price lookup. Already-scored calls are left untouched (so
    accuracy on a past call never silently changes), and results are
    rewritten back to the same file so re-running doesn't re-fetch prices
    for calls already scored.
    """
    if not path.exists():
        return {"total_logged": 0, "newly_scored": 0, "too_recent_to_score": 0, "total_scored": 0,
                "accuracy": None, "results": []}

    records = [json.loads(line) for line in path.read_text().splitlines() if line.strip()]
    price_cache = {}
    today = datetime.now()
    newly_scored = 0
    too_recent = 0

    for record in records:
        if "correct" in record:
            continue

        call_date = datetime.strptime(record["call_date"], "%Y-%m-%d")
        days_held = (today - call_date).days
        if days_held < min_hold_days:
            too_recent += 1
            continue

        ticker = record["ticker"]
        if ticker not in price_cache:
            price_cache[ticker] = _fetch_current_price(ticker)
        current_price = price_cache[ticker]
        if current_price is None:
            continue

        pct_change = round((current_price - record["price_at_call"]) / record["price_at_call"] * 100, 2)
        call = record["call"]
        if call == "BUY":
            correct = pct_change > 0
        elif call == "SELL":
            correct = pct_change < 0
        else:
            correct = abs(pct_change) <= HOLD_BAND_PCT

        record["price_now"] = current_price
        record["pct_change"] = pct_change
        record["days_held"] = days_held
        record["correct"] = correct
        record["scored_at"] = datetime.now().isoformat()
        newly_scored += 1

    with open(path, "w") as f:
        for record in records:
            f.write(json.dumps(record) + "\n")

    scored = [r for r in records if "correct" in r]
    accuracy = round(sum(1 for r in scored if r["correct"]) / len(scored), 3) if scored else None

    return {
        "total_logged": len(records),
        "newly_scored": newly_scored,
        "too_recent_to_score": too_recent,
        "total_scored": len(scored),
        "accuracy": accuracy,
        "results": records,
    }
