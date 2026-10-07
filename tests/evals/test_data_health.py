"""
Tests for the data-source health check (evals/data_health.py).

The individual _check_* functions hit real network calls, so those aren't
exercised directly here - they're thin wrappers whose only logic is "is the
result non-empty," already covered indirectly by sec_edgar's and
finnhub_fallback's own test suites. What's actually worth testing in
isolation is the pure classification logic: how a primary/fallback pair
rolls up into one capability verdict, and how several capabilities roll up
into one overall verdict - that's where a real bug could hide (e.g.
treating "skipped" as healthy, or letting one degraded capability mask an
actual failure elsewhere).
"""

from small_cap_multi_agent_framework.evals.data_health import _capability_status, _overall_status


def _status(status, detail="x"):
    return {"status": status, "detail": detail}


class TestCapabilityStatus:
    def test_ok_when_primary_works(self):
        result = _capability_status(_status("ok"), _status("fail"))
        assert result["status"] == "ok"
        assert result["via"] == "primary"

    def test_degraded_when_primary_down_but_fallback_works(self):
        result = _capability_status(_status("fail", "yahoo 404"), _status("ok", "finnhub worked"))
        assert result["status"] == "degraded"
        assert result["via"] == "fallback"
        assert result["primary_detail"] == "yahoo 404"
        assert result["fallback_detail"] == "finnhub worked"

    def test_fail_when_both_down(self):
        result = _capability_status(_status("fail"), _status("fail"))
        assert result["status"] == "fail"
        assert result["via"] == "none"

    def test_fail_when_primary_down_and_fallback_skipped(self):
        # a 'skipped' fallback (no API key configured) must NOT be treated
        # as coverage - this is a genuine blind spot, not a passing check.
        result = _capability_status(_status("fail"), _status("skipped", "no key"))
        assert result["status"] == "fail"

    def test_primary_ok_short_circuits_without_needing_fallback_data(self):
        # if the primary works, the fallback's status shouldn't matter at
        # all - a healthy primary should never be reported as degraded
        # just because a fallback happens to also be down or unconfigured.
        result = _capability_status(_status("ok"), _status("skipped"))
        assert result["status"] == "ok"


class TestOverallStatus:
    def test_all_ok_is_ok(self):
        coverage = {"a": _status("ok"), "b": _status("ok")}
        assert _overall_status(coverage) == "ok"

    def test_any_degraded_without_failure_is_degraded(self):
        coverage = {"a": _status("ok"), "b": _status("degraded")}
        assert _overall_status(coverage) == "degraded"

    def test_any_fail_is_fail_even_with_others_ok(self):
        coverage = {"a": _status("ok"), "b": _status("degraded"), "c": _status("fail")}
        assert _overall_status(coverage) == "fail"

    def test_fail_outranks_degraded(self):
        coverage = {"a": _status("degraded"), "b": _status("fail")}
        assert _overall_status(coverage) == "fail"

    def test_empty_coverage_is_ok(self):
        assert _overall_status({}) == "ok"
