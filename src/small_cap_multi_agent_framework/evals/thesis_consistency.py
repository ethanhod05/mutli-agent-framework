"""
Thesis Consistency Eval
========================

Grounding (evals/grounding.py) answers "is every number in this report real."
It can't catch a different failure: a report that cites genuinely real,
correctly-transcribed numbers and then reaches a conclusion that doesn't
follow from them - e.g. negative earnings growth, negative margins, and
price already above the analyst target, with a BUY recommendation anyway.
This eval answers that second question.

Deliberately NOT another LLM call: an LLM judging an LLM's thesis has its own
hallucination/bias risk, and would make this eval exactly as unverifiable as
the thing it's checking. Instead this is a small, explainable, rule-based
directional score computed straight from the same real tool output the
report was given - auditable, deterministic, reproducible.

This is intentionally a blunt instrument: it flags clear contradictions
(strongly negative fundamentals + BUY, or the reverse), not borderline cases.
A HOLD call is accepted across almost the whole score range, since "mixed
signals, stay put" is a defensible call in more situations than a strong
BUY or SELL is.
"""

import re

CALL_RE = re.compile(r"\b(BUY|HOLD|SELL)\b", re.IGNORECASE)
TICKER_HEADING_RE = re.compile(r"^##\s*([A-Z][A-Z.\-]{0,5})\b", re.MULTILINE)
TICKER_INPUT_RE = re.compile(r'"ticker"\s*:\s*"([A-Z.\-]+)"')

# Inconsistency threshold: the fundamental score must point clearly against
# the call (not just slightly) before it's flagged - avoids nagging about
# close calls where a human analyst could reasonably go either way.
INCONSISTENCY_THRESHOLD = 1.0


def _ticker_section(report_text: str, ticker: str) -> str:
    pattern = re.compile(
        rf"##\s*{re.escape(ticker)}\b.*?(?=\n##\s|\Z)", re.DOTALL | re.IGNORECASE
    )
    match = pattern.search(report_text)
    return match.group(0) if match else report_text


def _fundamentals_text_for_ticker(trace_events: list, ticker: str) -> str:
    """The real fundamentals tool_call result for this ticker, verbatim."""
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


def _metric(text: str, pattern: str):
    m = re.search(pattern, text, re.IGNORECASE)
    return float(m.group(1)) if m else None


def compute_fundamental_score(fundamentals_text: str) -> dict:
    """A small, explainable directional score from real tool output.

    Positive = bullish signals outweigh bearish ones; negative = the reverse.
    Each signal is named and kept in the result so the score is auditable,
    not a black box.
    """
    signals = []

    revenue_growth = _metric(fundamentals_text, r"Revenue Growth[:\s]+(-?[\d.]+)%")
    if revenue_growth is not None:
        signals.append(("Revenue Growth", f"{revenue_growth}%", 1.0 if revenue_growth > 0 else -1.0))

    earnings_growth = _metric(fundamentals_text, r"Earnings Growth[:\s]+(-?[\d.]+)%")
    if earnings_growth is not None:
        signals.append(("Earnings Growth", f"{earnings_growth}%", 1.0 if earnings_growth > 0 else -1.0))

    upside = _metric(fundamentals_text, r"Upside Potential[:\s]+(-?[\d.]+)%")
    if upside is not None:
        signals.append(("Upside Potential", f"{upside}%", 1.5 if upside > 0 else -1.5))

    net_margin = _metric(fundamentals_text, r"Net Margins?[:\s]+(-?[\d.]+)%")
    if net_margin is not None:
        signals.append(("Net Margin", f"{net_margin}%", 1.0 if net_margin > 0 else -1.0))

    op_margin = _metric(fundamentals_text, r"Operating Margins?[:\s]+(-?[\d.]+)%")
    if op_margin is not None:
        signals.append(("Operating Margin", f"{op_margin}%", 0.75 if op_margin > 0 else -0.75))

    current_ratio = _metric(fundamentals_text, r"Current Ratio[:\s]+([\d.]+)")
    if current_ratio is not None:
        signals.append(("Current Ratio", current_ratio, 0.5 if current_ratio >= 1.0 else -0.5))

    debt_equity = _metric(fundamentals_text, r"Debt/Equity[:\s]+([\d.]+)")
    if debt_equity is not None:
        # A rough, absolute red-flag line, not sector-relative - intentionally simple.
        signals.append(("Debt/Equity", debt_equity, -0.75 if debt_equity > 200 else 0.25))

    score = round(sum(weight for _, _, weight in signals), 2)
    return {"score": score, "signals": signals}


def _check_call_against_score(call: str, score: float) -> dict:
    call = call.upper()
    if call == "BUY" and score <= -INCONSISTENCY_THRESHOLD:
        return {"consistent": False, "reason": f"BUY recommended but fundamental score is {score} (net bearish)"}
    if call == "SELL" and score >= INCONSISTENCY_THRESHOLD:
        return {"consistent": False, "reason": f"SELL recommended but fundamental score is {score} (net bullish)"}
    return {"consistent": True, "reason": None}


def evaluate_thesis_consistency(report_text: str, trace_events: list) -> dict:
    """Check each ticker's call against a real-data-derived directional score.

    A ticker is skipped (not counted for/against the rate) when there's no
    call to check, or no real fundamental data to check it against - e.g.
    the thin-coverage small-caps we already know yfinance sometimes has
    nothing for. Skipping is the honest move there, not a free pass: there's
    nothing for an inconsistency check to compare against.
    """
    tickers = sorted(set(TICKER_HEADING_RE.findall(report_text)))

    per_ticker = []
    for ticker in tickers:
        section = _ticker_section(report_text, ticker)
        call_match = CALL_RE.search(section)
        call = call_match.group(1).upper() if call_match else None

        fundamentals_text = _fundamentals_text_for_ticker(trace_events, ticker)
        has_real_data = bool(fundamentals_text) and "No fundamental data available" not in fundamentals_text

        if not call or not has_real_data:
            per_ticker.append({"ticker": ticker, "applicable": False, "call": call})
            continue

        score_info = compute_fundamental_score(fundamentals_text)
        check = _check_call_against_score(call, score_info["score"])
        per_ticker.append({
            "ticker": ticker,
            "applicable": True,
            "call": call,
            "fundamental_score": score_info["score"],
            "signals": score_info["signals"],
            "consistent": check["consistent"],
            "reason": check["reason"],
        })

    applicable = [t for t in per_ticker if t["applicable"]]
    inconsistent = [t for t in applicable if not t["consistent"]]

    return {
        "per_ticker": per_ticker,
        "inconsistent_tickers": [t["ticker"] for t in inconsistent],
        "thesis_consistency_rate": round(
            (len(applicable) - len(inconsistent)) / len(applicable), 3
        ) if applicable else 1.0,
    }
