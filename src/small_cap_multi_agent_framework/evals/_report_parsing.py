"""
Shared Report-Parsing Helpers
==============================

Small regexes shared by grounding.py, thesis_consistency.py, and outcomes.py
to pull structured facts back out of the agent's freeform markdown report.
Centralized here on purpose: thesis_consistency.py and outcomes.py each used
to have their own copy of the call-extraction regex, and a naive version of
it (`re.search` for the first BUY/HOLD/SELL anywhere in a ticker's section)
produced a real, confirmed bug - a news headline like "...upgraded to Buy"
earlier in the section was picked up instead of the agent's actual verdict
further down, silently mislabeling both the thesis-consistency check and the
outcome-tracking log for that ticker. One shared, correct implementation
beats two copies that can drift out of sync with each other, or with the
report format they parse.
"""

import re

TICKER_HEADING_RE = re.compile(r"^##\s*([A-Z][A-Z.\-]{0,5})\b", re.MULTILINE)

# Matches a "**Investment Call:**" / "**Recommendation:**" / "**Call:**"
# label so the real verdict can be found even when an earlier line in the
# section mentions "buy"/"sell" in passing - e.g. a quoted news headline.
_CALL_HEADING_RE = re.compile(r"\*\*\s*(investment call|recommendation|call)\s*:?\s*\*\*", re.IGNORECASE)
_CALL_WORD_RE = re.compile(r"\b(BUY|HOLD|SELL)\b", re.IGNORECASE)


def ticker_section(report_text: str, ticker: str) -> str:
    """Extract the '## TICKER ...' section for one ticker from the report."""
    pattern = re.compile(
        rf"##\s*{re.escape(ticker)}\b.*?(?=\n##\s|\Z)", re.DOTALL | re.IGNORECASE
    )
    match = pattern.search(report_text)
    return match.group(0) if match else report_text


def extract_call(section_text: str) -> str:
    """The agent's real BUY/HOLD/SELL verdict for one ticker's section.

    Searches only after a "Call"/"Recommendation" heading when one is
    present - the real verdict - rather than the first match in the whole
    section, which can be an incidental mention (a news headline) that
    predates the agent's actual conclusion. Falls back to the *last* match
    in the section when no such heading exists, since a conclusion is far
    more likely to come at the end than an incidental early mention.
    """
    heading_match = _CALL_HEADING_RE.search(section_text)
    search_text = section_text[heading_match.start():] if heading_match else section_text

    matches = list(_CALL_WORD_RE.finditer(search_text))
    if not matches:
        return None

    chosen = matches[0] if heading_match else matches[-1]
    return chosen.group(1).upper()
