"""Tests for cost estimation (utils/cost.py)."""

from types import SimpleNamespace

from small_cap_multi_agent_framework.utils.cost import estimate_cost_usd, usage_summary


def _usage(total_tokens=0, prompt_tokens=0, cached_prompt_tokens=0, completion_tokens=0, successful_requests=0):
    return SimpleNamespace(
        total_tokens=total_tokens,
        prompt_tokens=prompt_tokens,
        cached_prompt_tokens=cached_prompt_tokens,
        completion_tokens=completion_tokens,
        successful_requests=successful_requests,
    )


class TestEstimateCostUsd:
    def test_known_model_computes_real_rate(self):
        usage = _usage(prompt_tokens=1_000_000, completion_tokens=1_000_000)
        cost = estimate_cost_usd(usage, "gpt-4o-mini")
        assert cost == 0.15 + 0.60

    def test_cached_tokens_use_the_discounted_rate_not_full_price(self):
        # 1M prompt tokens, all of them cache hits - should be billed at
        # the cached rate (0.075/1M), not the full prompt rate (0.15/1M).
        usage = _usage(prompt_tokens=1_000_000, cached_prompt_tokens=1_000_000)
        cost = estimate_cost_usd(usage, "gpt-4o-mini")
        assert cost == 0.075

    def test_mixed_cached_and_uncached_prompt_tokens(self):
        usage = _usage(prompt_tokens=1_000_000, cached_prompt_tokens=400_000)
        cost = estimate_cost_usd(usage, "gpt-4o-mini")
        expected = 600_000 * (0.15 / 1_000_000) + 400_000 * (0.075 / 1_000_000)
        assert cost == expected

    def test_unknown_model_returns_none_not_a_guess(self):
        usage = _usage(prompt_tokens=1_000_000, completion_tokens=1_000_000)
        assert estimate_cost_usd(usage, "some-future-model-not-in-table") is None

    def test_zero_usage_is_zero_cost(self):
        assert estimate_cost_usd(_usage(), "gpt-4o-mini") == 0.0

    def test_gpt_5_4_nano_pricing(self):
        usage = _usage(prompt_tokens=1_000_000, completion_tokens=1_000_000)
        assert estimate_cost_usd(usage, "gpt-5.4-nano") == 0.20 + 1.25

    def test_cached_tokens_never_exceed_prompt_tokens_worth_of_billing(self):
        # defensive: if cached_prompt_tokens were ever inconsistent (larger
        # than prompt_tokens), uncached shouldn't go negative and silently
        # flip the sign of part of the cost.
        usage = _usage(prompt_tokens=100, cached_prompt_tokens=500)
        cost = estimate_cost_usd(usage, "gpt-4o-mini")
        assert cost == 500 * (0.075 / 1_000_000)
        assert cost >= 0


class TestUsageSummary:
    def test_includes_all_raw_counts_and_estimated_cost(self):
        usage = _usage(
            total_tokens=300, prompt_tokens=200, cached_prompt_tokens=50,
            completion_tokens=100, successful_requests=4,
        )
        summary = usage_summary(usage, "gpt-4o-mini")
        assert summary["total_tokens"] == 300
        assert summary["prompt_tokens"] == 200
        assert summary["cached_prompt_tokens"] == 50
        assert summary["completion_tokens"] == 100
        assert summary["successful_requests"] == 4
        assert summary["estimated_cost_usd"] is not None

    def test_unknown_model_still_returns_raw_counts_with_none_cost(self):
        usage = _usage(total_tokens=300, prompt_tokens=200, completion_tokens=100)
        summary = usage_summary(usage, "some-future-model")
        assert summary["total_tokens"] == 300
        assert summary["estimated_cost_usd"] is None
