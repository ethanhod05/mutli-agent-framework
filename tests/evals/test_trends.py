"""Tests for run-trend aggregation (evals/trends.py)."""

from small_cap_multi_agent_framework.evals.trends import compute_trends


def _record(
    grounding_passed=True, thesis_passed=True, trajectory_passed=True,
    tool_calls_made=5, elapsed_seconds=30.0, estimated_cost_usd=0.01,
    prompt_version="v2", model="gpt-4o-mini",
):
    return {
        "grounding_passed": grounding_passed,
        "thesis_passed": thesis_passed,
        "trajectory_passed": trajectory_passed,
        "tool_calls_made": tool_calls_made,
        "elapsed_seconds": elapsed_seconds,
        "estimated_cost_usd": estimated_cost_usd,
        "prompt_version": prompt_version,
        "model": model,
    }


class TestComputeTrends:
    def test_empty_history_returns_none_rates_not_zero(self):
        result = compute_trends([])
        assert result["overall"]["run_count"] == 0
        assert result["overall"]["grounding_pass_rate"] is None

    def test_all_passing_runs_gives_rate_of_one(self):
        records = [_record() for _ in range(5)]
        result = compute_trends(records)
        assert result["overall"]["grounding_pass_rate"] == 1.0
        assert result["overall"]["thesis_pass_rate"] == 1.0
        assert result["overall"]["trajectory_pass_rate"] == 1.0

    def test_mixed_pass_fail_computes_correct_fraction(self):
        records = [_record(grounding_passed=True)] * 3 + [_record(grounding_passed=False)] * 1
        result = compute_trends(records)
        assert result["overall"]["grounding_pass_rate"] == 0.75

    def test_window_limits_to_most_recent_n(self):
        old_failing = [_record(grounding_passed=False) for _ in range(10)]
        recent_passing = [_record(grounding_passed=True) for _ in range(5)]
        result = compute_trends(old_failing + recent_passing, window=5)
        assert result["overall"]["run_count"] == 5
        assert result["overall"]["grounding_pass_rate"] == 1.0

    def test_window_zero_or_none_uses_all_records(self):
        records = [_record() for _ in range(3)]
        result = compute_trends(records, window=0)
        assert result["overall"]["run_count"] == 3

    def test_records_missing_a_field_do_not_count_against_its_rate(self):
        # a run from before an eval existed shouldn't silently fail it.
        with_field = [_record(trajectory_passed=True)] * 2
        missing_field = [{"grounding_passed": True, "thesis_passed": True}]
        result = compute_trends(with_field + missing_field)
        assert result["overall"]["trajectory_pass_rate"] == 1.0

    def test_cost_and_tool_call_averages(self):
        records = [
            _record(tool_calls_made=4, elapsed_seconds=20.0, estimated_cost_usd=0.01),
            _record(tool_calls_made=6, elapsed_seconds=40.0, estimated_cost_usd=0.03),
        ]
        result = compute_trends(records)
        assert result["overall"]["avg_tool_calls"] == 5.0
        assert result["overall"]["avg_elapsed_seconds"] == 30.0
        assert result["overall"]["total_estimated_cost_usd"] == 0.04
        assert result["overall"]["avg_estimated_cost_usd"] == 0.02

    def test_groups_by_prompt_version(self):
        v1_records = [_record(prompt_version="v1", grounding_passed=False)] * 2
        v2_records = [_record(prompt_version="v2", grounding_passed=True)] * 3
        result = compute_trends(v1_records + v2_records)

        assert result["by_prompt_version"]["v1"]["run_count"] == 2
        assert result["by_prompt_version"]["v1"]["grounding_pass_rate"] == 0.0
        assert result["by_prompt_version"]["v2"]["run_count"] == 3
        assert result["by_prompt_version"]["v2"]["grounding_pass_rate"] == 1.0

    def test_missing_prompt_version_groups_as_unknown(self):
        record = _record()
        del record["prompt_version"]
        result = compute_trends([record])
        assert "unknown" in result["by_prompt_version"]
        assert result["by_prompt_version"]["unknown"]["run_count"] == 1

    def test_groups_by_model_for_a_model_swap_comparison(self):
        baseline = [_record(model="gpt-4o-mini", grounding_passed=True, estimated_cost_usd=0.0015)] * 5
        candidate = [_record(model="gpt-5.4-nano", grounding_passed=True, estimated_cost_usd=0.0008)] * 5
        result = compute_trends(baseline + candidate)

        assert result["by_model"]["gpt-4o-mini"]["run_count"] == 5
        assert result["by_model"]["gpt-4o-mini"]["avg_estimated_cost_usd"] == 0.0015
        assert result["by_model"]["gpt-5.4-nano"]["run_count"] == 5
        assert result["by_model"]["gpt-5.4-nano"]["avg_estimated_cost_usd"] == 0.0008

    def test_missing_model_groups_as_unknown(self):
        record = _record()
        del record["model"]
        result = compute_trends([record])
        assert result["by_model"]["unknown"]["run_count"] == 1
