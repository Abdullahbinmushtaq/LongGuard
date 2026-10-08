"""Configuration, detector-extension and recovery boundary behavior."""

import pytest

from longguard import (
    AbstractLoopDetector,
    AgentStep,
    CircuitBreaker,
    DetectionResult,
    GuardConfig,
    HashBasedEmbedder,
    ReflectAndPivotInjector,
    SemanticOscillationDetector,
    TokenVelocityDetector,
)


@pytest.mark.parametrize(
    "settings,message",
    [
        ({"token_velocity_window": 1}, "token_velocity_window"),
        ({"max_cost_usd": 0}, "max_cost_usd"),
        ({"cost_per_input_token": 0.1}, "set together"),
        ({"cost_per_input_token": -0.1, "cost_per_output_token": 0}, "cost_per_input_token"),
        ({"cost_per_input_token": 0, "cost_per_output_token": -0.1}, "cost_per_output_token"),
    ],
)
def test_invalid_budget_or_detector_settings_fail_before_execution(settings, message):
    with pytest.raises(ValueError, match=message):
        GuardConfig(**settings)


@pytest.mark.parametrize(
    "settings,message",
    [
        ({"detected": True, "confidence": 0.5}, "pattern"),
        ({"detected": True, "pattern": "custom", "confidence": -0.1}, "confidence"),
        ({"detected": True, "pattern": "custom", "confidence": 1.1}, "confidence"),
    ],
)
def test_detector_results_reject_invalid_positive_evidence(settings, message):
    with pytest.raises(ValueError, match=message):
        DetectionResult(**settings)


@pytest.mark.parametrize(
    "first,second,expected",
    [
        (DetectionResult(), DetectionResult(), None),
        (DetectionResult(True, "first", 0.2), DetectionResult(), "first"),
        (DetectionResult(), DetectionResult(True, "second", 0.8), "second"),
        (DetectionResult(True, "first", 0.2), DetectionResult(True, "second", 0.8), "second"),
        (DetectionResult(True, "first", 0.8), DetectionResult(True, "second", 0.8), "first"),
    ],
)
def test_result_merge_keeps_the_strongest_detection_with_stable_ties(first, second, expected):
    merged = first.merge(second)
    assert merged.detected is (expected is not None)
    assert merged.pattern == (expected or "")
    if expected is not None:
        assert merged is (first if expected == "first" else second)


def test_failing_application_detector_and_event_callback_do_not_disable_guard(caplog):
    class FailedDetector(AbstractLoopDetector):
        def analyze(self, step):
            raise RuntimeError("Unavailable application signal")

        def reset(self):
            pass

        @property
        def name(self):
            return "FailedDetector"

    def unavailable_observer(event, data):
        raise RuntimeError("Unavailable telemetry destination")

    breaker = CircuitBreaker(
        GuardConfig(tool_repeat_threshold=1), event_callback=unavailable_observer
    )
    detector = FailedDetector()
    breaker.detectors.append(detector)
    assert repr(detector) == "FailedDetector()"
    decision = breaker.check(AgentStep(1, "repeat", action="search"))
    assert decision.action == "reflect"
    assert breaker.report.reflections_injected == 1
    assert "Unavailable application signal" in caplog.text
    assert "Event callback raised" in caplog.text


@pytest.mark.parametrize(
    "template,expected", [("Use {unknown}", "Use {unknown}"), ("Use {", "Use {")]
)
def test_custom_pivot_templates_handle_missing_keys_and_bad_braces(template, expected):
    injector = ReflectAndPivotInjector({"custom": template})
    result = injector.generate(DetectionResult(True, "custom", 0.8), AgentStep(1, "retry"))
    assert result.endswith(expected)
    assert result.startswith("[LONGGUARD-")


def test_zero_warmup_and_zero_usage_baseline_do_not_fabricate_velocity_spikes():
    detector = TokenVelocityDetector(window=1, warmup=0)
    assert not detector.analyze(AgentStep(1, "no usage", tokens_used=0)).detected
    assert not detector.analyze(AgentStep(2, "known usage", tokens_used=100)).detected
    spike = detector.analyze(AgentStep(3, "large usage", tokens_used=1000))
    assert spike.detected
    assert spike.evidence["baseline_velocity"] == 100
    assert spike.evidence["velocity_ratio"] == 10
    assert spike.evidence["acceleration"] == 0


def test_actual_hash_embeddings_respect_a_strict_variance_threshold():
    detector = SemanticOscillationDetector(
        window=2, variance_threshold=1e-12, embedder=HashBasedEmbedder(dimension=2)
    )
    first = AgentStep(1, "Read the first database row")
    second = AgentStep(2, "Publish the completed astronomy calculation")
    assert not detector.analyze(first).detected
    assert not detector.analyze(second).detected
    assert first.thought_vector != second.thought_vector


def test_missing_embedding_extra_gives_an_actionable_install_instruction(monkeypatch):
    import builtins

    from longguard import SentenceTransformerEmbedder

    real_import = builtins.__import__

    def without_sentence_transformers(name, *args, **kwargs):
        if name == "sentence_transformers":
            raise ImportError("Optional embedding package is absent")
        return real_import(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", without_sentence_transformers)
    with pytest.raises(ImportError, match=r"pip install longguard\[embeddings\]"):
        SentenceTransformerEmbedder()
