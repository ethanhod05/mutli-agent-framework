"""
Grounding Eval
==============

Checks whether a generated investment report is actually grounded in the real
tool-call data captured by RunTracer, instead of a human manually
cross-referencing numbers by eye (which is what validated the Phase 1 fix).

Two checks:
1. Ticker grounding: every ticker discussed in the report must be one that
   was actually looked up via a real tool call in this run. This is the
   exact failure mode that caused the original hallucination bug (agent
   recommending tickers, like BBBY, that no tool ever returned).
2. Numeric grounding: every dollar/percent/ratio figure quoted in the report
   must match a number that actually appeared in that ticker's tool output,
   within a small tolerance for rounding/formatting.

This is intentionally a blunt, string-matching check, not a semantic one -
the goal is to catch fabricated numbers, not to grade writing quality.
"""

import re
from dataclasses import dataclass, field

from small_cap_multi_agent_framework.evals._report_parsing import TICKER_HEADING_RE

NUMBER_RE = re.compile(r"-?\$?\d[\d,]*\.?\d*%?")
TICKER_INPUT_RE = re.compile(r'"ticker"\s*:\s*"([A-Z.\-]+)"')
TICKER_MENTION_RE = re.compile(r"\b([A-Z]{1,6}(?:\.[A-Z])?)\b")

# Common uppercase finance acronyms that would otherwise look like tickers to
# a naive scan - only relevant to the fallback parser below.
_NON_TICKER_ACRONYMS = {
    "BUY", "SELL", "HOLD", "ROE", "ROA", "ROI", "ROIC", "PE", "EPS", "USD",
    "SEC", "CEO", "CFO", "GICS", "EV", "EBITDA", "TTM", "PEG", "PB", "PS",
    "CAGR", "ESG", "IPO", "NASDAQ", "NYSE", "FCF", "YOY", "QOQ", "ETF",
    "GDP", "CPI", "FDA", "AI", "N", "A",
}


def _extract_numbers(text: str) -> set:
    """Pull numeric tokens out of text, normalized to plain rounded floats."""
    numbers = set()
    for match in NUMBER_RE.findall(text):
        cleaned = match.replace("$", "").replace(",", "").replace("%", "")
        try:
            numbers.add(round(float(cleaned), 2))
        except ValueError:
            continue
    return numbers


def _ticker_section(report_text: str, ticker: str) -> str:
    """Extract the '## TICKER ...' section for one ticker from the report."""
    pattern = re.compile(
        rf"##\s*{re.escape(ticker)}\b.*?(?=\n##\s|\Z)", re.DOTALL | re.IGNORECASE
    )
    match = pattern.search(report_text)
    return match.group(0) if match else ""


def _numbers_match(claimed: float, traced_numbers: set) -> bool:
    return any(abs(claimed - t) < max(0.01, abs(t) * 0.01) for t in traced_numbers)


def _fallback_ticker_mentions(report_text: str, known_tickers: set) -> set:
    """When no '## TICKER' headings are found (a model formatted the report
    differently, e.g. a single-ticker report using '# Report: AAPL' instead),
    fall back to scanning the whole report for ticker-shaped tokens rather
    than silently reporting nothing. Known traced tickers are trusted;
    anything else uppercase and short is flagged as a possible extra/
    hallucinated ticker unless it's a common finance acronym.
    """
    found = set()
    for token in TICKER_MENTION_RE.findall(report_text):
        if token in known_tickers:
            found.add(token)
        elif token not in _NON_TICKER_ACRONYMS and len(token) >= 2:
            found.add(token)
    return found


def _numbers_from_events_mentioning_ticker(trace_events: list, ticker: str) -> set:
    """Numbers from any event whose text mentions this ticker by name.

    This picks up legitimate non-tool-call ground truth too - e.g. a CSV's
    market cap embedded in the data-quality task's description - not just
    live tool_call results. Ticker *existence* is still checked strictly via
    tool_input elsewhere; this only broadens what counts as a real number.
    """
    numbers = set()
    ticker_pattern = re.compile(rf"\b{re.escape(ticker)}\b")
    for event in trace_events:
        text = " ".join(str(event.get(k, "")) for k in ("tool_input", "result", "description", "raw_output"))
        if ticker_pattern.search(text):
            numbers |= _extract_numbers(text)
    return numbers


@dataclass
class TickerGrounding:
    ticker: str
    in_trace: bool
    claimed_numbers: set = field(default_factory=set)
    unverified_numbers: set = field(default_factory=set)


def evaluate_grounding(report_text: str, trace_events: list) -> dict:
    """Evaluate report_text against a RunTracer's event list.

    Returns a dict with overall grounding rates and a per-ticker breakdown,
    including any tickers mentioned in the report that never appeared in a
    real tool call.
    """
    tool_calls = [e for e in trace_events if e.get("type") == "tool_call"]

    traced_numbers_by_ticker: dict = {}
    for call in tool_calls:
        m = TICKER_INPUT_RE.search(call.get("tool_input") or "")
        if not m:
            continue
        ticker = m.group(1)
        traced_numbers_by_ticker.setdefault(ticker, set())
        traced_numbers_by_ticker[ticker] |= _extract_numbers(call.get("result", ""))

    traced_tickers = set(traced_numbers_by_ticker.keys())
    reported_tickers = set(TICKER_HEADING_RE.findall(report_text))

    used_fallback_parsing = False
    if not reported_tickers and report_text.strip():
        used_fallback_parsing = True
        reported_tickers = _fallback_ticker_mentions(report_text, traced_tickers)

    ungrounded_tickers = sorted(reported_tickers - traced_tickers)

    all_traced_numbers = set()
    for nums in traced_numbers_by_ticker.values():
        all_traced_numbers |= nums

    per_ticker = []
    for ticker in sorted(reported_tickers):
        # Without a '## TICKER' boundary we can't isolate which numbers belong
        # to which ticker, so fallback mode checks against the whole report
        # and the full pool of traced numbers - looser, but still catches a
        # ticker or number that's entirely made up.
        section = report_text if used_fallback_parsing else _ticker_section(report_text, ticker)
        claimed = _extract_numbers(section)
        traced = traced_numbers_by_ticker.get(ticker, set())
        traced |= _numbers_from_events_mentioning_ticker(trace_events, ticker)
        if used_fallback_parsing:
            traced |= all_traced_numbers
        unverified = {n for n in claimed if not _numbers_match(n, traced)}
        per_ticker.append(TickerGrounding(
            ticker=ticker,
            in_trace=ticker in traced_tickers,
            claimed_numbers=claimed,
            unverified_numbers=unverified,
        ))

    total_claims = sum(len(t.claimed_numbers) for t in per_ticker)
    total_unverified = sum(len(t.unverified_numbers) for t in per_ticker)

    return {
        "reported_tickers": sorted(reported_tickers),
        "traced_tickers": sorted(traced_tickers),
        "ungrounded_tickers": ungrounded_tickers,
        "used_fallback_parsing": used_fallback_parsing,
        "ticker_grounding_rate": round(
            (len(reported_tickers) - len(ungrounded_tickers)) / len(reported_tickers), 3
        ) if reported_tickers else 1.0,
        "numeric_grounding_rate": round(
            (total_claims - total_unverified) / total_claims, 3
        ) if total_claims else 1.0,
        "per_ticker": [
            {
                "ticker": t.ticker,
                "in_trace": t.in_trace,
                "claimed_numbers": sorted(t.claimed_numbers),
                "unverified_numbers": sorted(t.unverified_numbers),
            }
            for t in per_ticker
        ],
    }
