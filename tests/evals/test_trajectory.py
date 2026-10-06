"""
Tests for evals/trajectory.py - grading the path an agent took, not just
its final output. Grounding and thesis-consistency can both pass while an
agent flails; this is the eval that can see flailing.

The core regression case (test_repeated_calls_on_an_incomplete_task_is_
flagged) models the real HROW incident: the fundamentals agent called the
same tool input 36 times and the task never completed at all. That incident
was invisible to every other eval in this project - grounding and
thesis-consistency both passed it.
"""

from small_cap_multi_agent_framework.evals.trajectory import evaluate_trajectory


def _tool_call(ticker, query_type="fundamental"):
    return {
        "type": "tool_call",
        "timestamp": "2026-01-01T00:00:00",
        "tool": "query_institutional_database",
        "tool_input": f'{{"ticker": "{ticker}", "query_type": "{query_type}"}}',
        "result": "some real result",
    }


def _task_complete(agent, ticker=None, description=None):
    return {
        "type": "task_complete",
        "timestamp": "2026-01-01T00:00:00",
        "agent": agent,
        "description": description or (f"ticker '{ticker}'" if ticker else "synthesis"),
        "raw_output": "ok",
    }


def test_healthy_single_call_per_task_passes():
    trace = [
        _tool_call("AAA", "fundamental"),
        _task_complete("Quantitative Financial Analyst", "AAA"),
        _tool_call("AAA", "news"),
        _task_complete("Market Intelligence Analyst", "AAA"),
        _task_complete("Senior Portfolio Manager"),
    ]
    result = evaluate_trajectory(trace)
    assert result["severity"] == "ok"
    assert result["trajectory_passed"] is True
    assert result["repeated_call_tickers"] == []


def test_healthy_multi_ticker_run_passes():
    trace = []
    for ticker in ["AAA", "BBB", "CCC"]:
        trace.append(_tool_call(ticker, "fundamental"))
        trace.append(_task_complete("Quantitative Financial Analyst", ticker))
        trace.append(_tool_call(ticker, "news"))
        trace.append(_task_complete("Market Intelligence Analyst", ticker))
    trace.append(_task_complete("Senior Portfolio Manager"))
    result = evaluate_trajectory(trace)
    assert result["severity"] == "ok"
    assert result["total_tasks"] == 7
    assert result["total_tool_calls"] == 6


def test_repeated_calls_on_a_completed_task_is_flagged():
    trace = [
        _tool_call("AAA", "fundamental"),
        _tool_call("AAA", "fundamental"),
        _tool_call("AAA", "fundamental"),
        _task_complete("Quantitative Financial Analyst", "AAA"),
    ]
    result = evaluate_trajectory(trace)
    assert result["severity"] == "fail"
    assert result["trajectory_passed"] is False
    assert result["repeated_call_tickers"] == ["AAA"]


def test_repeated_calls_on_an_incomplete_task_is_flagged():
    # The real HROW incident: 36 identical calls and the task never
    # completed at all - no task_complete event ever closes it out. This is
    # the exact shape that was invisible to grounding and thesis-consistency.
    trace = [_tool_call("HROW", "fundamental") for _ in range(36)]
    result = evaluate_trajectory(trace)
    assert result["severity"] == "fail"
    assert result["trajectory_passed"] is False
    assert result["repeated_call_tickers"] == ["HROW"]
    segment = result["segments"][0]
    assert segment["completed"] is False
    assert segment["tool_call_count"] == 36
    assert any("never completed" in v for v in segment["violations"])
    assert any("36 times" in v for v in segment["violations"])


def test_two_repeats_is_a_warning_not_a_failure():
    trace = [
        _tool_call("AAA", "fundamental"),
        _tool_call("AAA", "fundamental"),
        _task_complete("Quantitative Financial Analyst", "AAA"),
    ]
    result = evaluate_trajectory(trace)
    assert result["severity"] == "warn"
    assert result["trajectory_passed"] is True  # warn still passes, fail doesn't


def test_incomplete_task_with_no_repeats_is_only_a_warning():
    # The trace just stops after one clean call - unfinished, but not loopy.
    trace = [_tool_call("AAA", "fundamental")]
    result = evaluate_trajectory(trace)
    assert result["severity"] == "warn"
    assert result["segments"][0]["completed"] is False


def test_zero_tool_calls_from_an_agent_that_requires_one_is_flagged():
    trace = [_task_complete("Quantitative Financial Analyst", "AAA")]
    result = evaluate_trajectory(trace)
    assert result["severity"] == "fail"
    assert any("no tool call at all" in v for v in result["segments"][0]["violations"])


def test_tool_call_from_a_no_tool_role_is_flagged():
    # Senior Portfolio Manager has tools=[] in agents.py - it should never
    # show up with a tool call in its segment (a delegation leak or similar).
    trace = [
        _tool_call("AAA", "fundamental"),
        _task_complete("Senior Portfolio Manager"),
    ]
    result = evaluate_trajectory(trace)
    assert result["severity"] == "fail"
    assert any("should never call a tool" in v for v in result["segments"][0]["violations"])


def test_wrong_ticker_call_is_flagged():
    # The task was described as being for AAA but the actual call was for a
    # different ticker entirely - cross-contamination between tasks.
    trace = [
        _tool_call("BBB", "fundamental"),
        _task_complete("Quantitative Financial Analyst", "AAA"),
    ]
    result = evaluate_trajectory(trace)
    assert result["severity"] == "fail"
    assert any("called the tool for BBB instead" in v for v in result["segments"][0]["violations"])


def test_empty_trace_is_trivially_ok():
    result = evaluate_trajectory([])
    assert result["severity"] == "ok"
    assert result["trajectory_passed"] is True
    assert result["total_tasks"] == 0
