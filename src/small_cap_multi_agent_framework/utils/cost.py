"""
Cost Estimation
================

crewai tracks real token usage per run - `Crew.kickoff()`'s return value
carries a `UsageMetrics` with prompt/completion/cached token counts - so
turning that into an estimated dollar figure only needs a pricing table,
not a new tracking mechanism. This is what makes a run's actual cost
visible (per run, and summed/averaged in run_history trends) instead of
only guessable from token counts by hand.

Pricing is a hardcoded table, not fetched live (OpenAI doesn't publish a
pricing API) - verified against OpenAI's published per-token pricing as of
2026-10-07. If OpenAI changes prices, or a new OPENAI_MODEL is configured
that isn't in this table, estimate_cost_usd returns None rather than
guessing from an unrelated model's rate - cost is reported as "unknown",
never fabricated.
"""

import logging
from typing import Any, Optional

logger = logging.getLogger(__name__)

# USD per token (not per million). cached_prompt is the discounted rate for
# repeated prompt prefixes; there's no cached variant for completion
# tokens. prompt_tokens, per OpenAI's own usage reporting, already INCLUDES
# cached_prompt_tokens as a subset - not an additional amount on top.
PRICING_PER_TOKEN = {
    "gpt-4o-mini": {
        "prompt": 0.15 / 1_000_000,
        "cached_prompt": 0.075 / 1_000_000,
        "completion": 0.60 / 1_000_000,
    },
    "gpt-4o": {
        "prompt": 2.50 / 1_000_000,
        "cached_prompt": 1.25 / 1_000_000,
        "completion": 10.00 / 1_000_000,
    },
}


def estimate_cost_usd(usage: Any, model_name: str) -> Optional[float]:
    """Estimated dollar cost for a crewai UsageMetrics-shaped object (or
    anything with the same attributes), or None if `model_name` isn't in
    the pricing table above."""
    rates = PRICING_PER_TOKEN.get(model_name)
    if rates is None:
        logger.warning(f"No pricing data for model '{model_name}' - cost will be reported as unknown")
        return None

    prompt_tokens = getattr(usage, "prompt_tokens", 0) or 0
    cached_tokens = getattr(usage, "cached_prompt_tokens", 0) or 0
    completion_tokens = getattr(usage, "completion_tokens", 0) or 0
    uncached_prompt_tokens = max(prompt_tokens - cached_tokens, 0)

    return (
        uncached_prompt_tokens * rates["prompt"]
        + cached_tokens * rates["cached_prompt"]
        + completion_tokens * rates["completion"]
    )


def usage_summary(usage: Any, model_name: str) -> dict:
    """Flattened dict of token counts plus an estimated cost - this is the
    shape saved into execution summaries and run_history.jsonl."""
    return {
        "total_tokens": getattr(usage, "total_tokens", 0) or 0,
        "prompt_tokens": getattr(usage, "prompt_tokens", 0) or 0,
        "cached_prompt_tokens": getattr(usage, "cached_prompt_tokens", 0) or 0,
        "completion_tokens": getattr(usage, "completion_tokens", 0) or 0,
        "successful_requests": getattr(usage, "successful_requests", 0) or 0,
        "estimated_cost_usd": estimate_cost_usd(usage, model_name),
    }
