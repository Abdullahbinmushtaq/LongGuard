"""Public circuit-breaker stop and continuation contracts."""

import pytest

from longguard import AgentStep, CircuitBreaker, GuardConfig


def test_detector_trip_remains_terminal_on_clean_checks():
    breaker = CircuitBreaker(GuardConfig(tool_repeat_threshold=1, max_reflections=1))
    first = AgentStep(step_number=1, thought="search", action="search", tokens_used=1)
    second = AgentStep(step_number=2, thought="search", action="search", tokens_used=1)
    assert breaker.check(first).action == "reflect"
    stopped = breaker.check(second)
    assert stopped.action == "kill"
    snapshot = breaker.report.to_dict()

    for number in (3, 4):
        decision = breaker.check(AgentStep(step_number=number, thought="done", tokens_used=1))
        assert decision.action == "kill"
        assert decision.reason == stopped.reason
        assert breaker.report.to_dict() == snapshot

    breaker.reset()
    assert breaker.check(AgentStep(step_number=1, thought="new task", tokens_used=1)).action == (
        "continue"
    )


def test_explicit_recovery_resume_retains_consumption_and_records_allowance():
    breaker = CircuitBreaker(
        GuardConfig(
            tool_repeat_threshold=1,
            max_reflections=1,
            max_cost_usd=0.05,
            cost_per_input_token=0.001,
            cost_per_output_token=0.001,
        )
    )
    for number in (1, 2):
        breaker.check(AgentStep(number, "search", action="search", tokens_used=10))
    stopped_reason = breaker.report.kill_reason
    breaker.resume(correction="Use a different approach", additional_reflections=1)
    assert breaker.total_tokens == 20
    assert breaker.total_steps == 2
    assert breaker.report.reflections_injected == 1
    assert breaker.report.estimated_cost_usd == pytest.approx(0.02)
    assert breaker.report.continuations[0]["estimated_cost_usd"] == pytest.approx(0.02)
    assert breaker.report.continuations[0]["previous_reason"] == stopped_reason
    assert breaker.report.continuations[0]["additional_reflections"] == 1
    assert breaker.check(AgentStep(3, "different approach", tokens_used=1)).action == "continue"


def test_resume_rejects_exhausted_allowance_and_empty_correction():
    breaker = CircuitBreaker(GuardConfig(max_steps=1))
    breaker.check(AgentStep(1, "first"))
    breaker.check(AgentStep(2, "second"))
    with pytest.raises(ValueError, match="allowance|hard"):
        breaker.resume(correction="retry")
    with pytest.raises(ValueError, match="correction"):
        breaker.resume(correction=" ")


def test_clean_recoveries_do_not_replenish_reflection_budget():
    breaker = CircuitBreaker(GuardConfig(tool_repeat_threshold=1, max_reflections=1))
    assert breaker.check(AgentStep(1, "retry", action="search")).action == "reflect"
    assert breaker.check(AgentStep(2, "useful final answer")).action == "continue"
    assert breaker.check(AgentStep(3, "retry", action="different_tool")).action == "kill"
    assert breaker.report.reflections_injected == 1


def test_continuation_metadata_roundtrips_and_old_reports_load(tmp_path):
    from longguard import GuardReport

    breaker = CircuitBreaker(GuardConfig(tool_repeat_threshold=1, max_reflections=1))
    for number in (1, 2):
        breaker.check(AgentStep(number, "retry", action="search", tokens_used=4))
    before = breaker.report.to_dict()
    for allowance in (0, -1, True, 1.5):
        with pytest.raises(ValueError, match="positive integer"):
            breaker.resume(correction="finish", additional_reflections=allowance)
        assert breaker.report.to_dict() == before
    breaker.resume(correction="finish")
    report = breaker.report
    saved = tmp_path / "report.json"
    report.save(saved)
    assert GuardReport.load(saved).to_dict() == report.to_dict()
    import json

    old = report.to_dict()
    for key in ("run_id", "continuations", "tool_dispositions", "usage_warnings"):
        old.pop(key)
    saved.write_text(json.dumps(old))
    loaded = GuardReport.load(saved)
    assert loaded.total_tokens == 8
    assert loaded.continuations == []


def test_published_v014_report_fixture_loads():
    from pathlib import Path

    from longguard import GuardReport

    report = GuardReport.load(Path(__file__).parent / "fixtures" / "report_v014.json")
    assert report.total_steps == report.total_tokens == 0
    assert report.continuations == report.tool_dispositions == report.usage_warnings == []
    assert report.run_id
