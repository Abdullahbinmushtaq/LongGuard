"""Public decorator contracts for extraction, termination and run lifecycle."""

from types import SimpleNamespace

import pytest

from longguard import AgentStep, CircuitBreaker, CircuitBreakerTrippedError, GuardConfig, guarded


def test_keyword_step_and_explicit_breaker_preserve_usage_without_double_observation():
    breaker = CircuitBreaker(GuardConfig(max_steps=3))

    @guarded(breaker=breaker)
    def execute(*, step):
        return AgentStep(99, "returned step", tokens_used=100)

    assert execute(step=AgentStep(1, "requested step", tokens_used=7)).step_number == 99
    assert execute.report is breaker.report
    assert execute.report.total_steps == 1
    assert execute.report.total_tokens == 7


def test_custom_extractor_can_observe_only_the_completed_result():
    def extract(*, result=None):
        return None if result is None else AgentStep(1, result, tokens_used=9)

    @guarded(config=GuardConfig(), step_extractor=extract)
    def operation():
        return "completed observation"

    assert operation() == "completed observation"
    assert operation.report.total_steps == 1
    assert operation.report.total_tokens == 9


def test_anthropic_response_extracts_tool_and_usage():
    response = SimpleNamespace(
        role="assistant",
        content=[
            SimpleNamespace(type="text", text="A useful answer"),
            SimpleNamespace(type="tool_use", name="search", input={"q": "answer"}),
        ],
        usage=SimpleNamespace(input_tokens=8, output_tokens=3),
    )

    @guarded
    def request():
        return response

    assert request() is response
    assert request.report.total_tokens == 11
    assert request.report.steps[0]["action"] == "search"


def test_openai_response_extracts_usage():
    response = SimpleNamespace(
        choices=[
            SimpleNamespace(
                message=SimpleNamespace(
                    content="A useful answer",
                    tool_calls=None,
                )
            )
        ],
        usage=SimpleNamespace(total_tokens=12),
    )

    @guarded
    def request(*, previous):
        return response

    assert request(previous="result") is response
    assert request.report.total_tokens == 12


@pytest.mark.parametrize(
    "value",
    [
        42,
        {"unrelated": "value"},
        SimpleNamespace(choices=[]),
        SimpleNamespace(role="assistant", content=42),
    ],
)
def test_unobservable_results_do_not_invent_steps(value):
    @guarded
    def operation():
        return value

    assert operation() is value
    assert operation.report.total_steps == 0


def test_post_call_trip_blocks_later_sync_side_effects():
    effects = []

    @guarded(tool_repeat_threshold=1, max_reflections=1)
    def request():
        effects.append("request")
        return AgentStep(len(effects), "repeat", action="search")

    request()
    with pytest.raises(CircuitBreakerTrippedError):
        request()
    assert effects == ["request", "request"]
    with pytest.raises(CircuitBreakerTrippedError):
        request()
    assert effects == ["request", "request"]


@pytest.mark.asyncio
async def test_post_call_trip_blocks_later_async_side_effects():
    effects = []

    @guarded(tool_repeat_threshold=1, max_reflections=1)
    async def request():
        effects.append("request")
        return AgentStep(len(effects), "repeat", action="search")

    await request()
    assert request.last_reflection_prompt
    with pytest.raises(CircuitBreakerTrippedError):
        await request()
    with pytest.raises(CircuitBreakerTrippedError):
        await request()
    assert effects == ["request", "request"]


@pytest.mark.asyncio
async def test_async_reset_exposes_fresh_report_and_clears_advice():
    @guarded(tool_repeat_threshold=1)
    async def operation(step):
        return "done"

    await operation(AgentStep(1, "repeat", action="search"))
    previous = operation.report
    assert operation.last_reflection_prompt
    operation.reset()
    assert operation.report is not previous
    assert operation.report.total_steps == 0
    assert operation.last_reflection_prompt is None
    await operation(AgentStep(1, "clean", tokens_used=4))
    assert operation.report.total_tokens == 4
    assert previous.total_tokens == 0


def test_generator_reset_exposes_fresh_report_and_clears_advice():
    @guarded(tool_repeat_threshold=1)
    def operation():
        yield AgentStep(1, "repeat", action="search")

    list(operation())
    previous = operation.report
    assert operation.last_reflection_prompt
    operation.reset()
    assert operation.report is not previous
    assert operation.report.total_steps == 0
    assert operation.last_reflection_prompt is None


@pytest.mark.parametrize("policy", ["return", "callback", "raise"])
def test_generator_preserves_completion_value_and_stops_with_configured_policy(policy):
    def on_kill(decision, **kwargs):
        return {"stopped": decision.reason}

    @guarded(max_steps=1, on_kill=on_kill if policy == "callback" else policy)
    def operation():
        yield {"thought": "first"}
        yield {"thought": "second"}
        raise AssertionError("Generator must stop before further work")

    stream = operation()
    assert next(stream) == {"thought": "first"}
    if policy == "raise":
        with pytest.raises(CircuitBreakerTrippedError):
            next(stream)
    else:
        stopped = next(stream)
        assert "max_steps" in (stopped["stopped"] if isinstance(stopped, dict) else stopped)
    with pytest.raises(StopIteration):
        next(stream)


def test_generator_custom_extraction_and_completion_value():
    @guarded(step_extractor=lambda *args, result, **kwargs: AgentStep(1, result, tokens_used=3))
    def operation():
        yield "progress"
        return "finished"

    stream = operation()
    assert next(stream) == "progress"
    with pytest.raises(StopIteration) as stop:
        next(stream)
    assert stop.value.value == "finished"
    assert operation.report.total_tokens == 3


@pytest.mark.asyncio
@pytest.mark.parametrize("policy", ["return", "callback"])
@pytest.mark.parametrize("pre_call", [False, True])
async def test_async_termination_policies_preserve_argument_and_result_boundaries(policy, pre_call):
    effects = []

    def on_kill(decision, *args, **kwargs):
        return {"stopped": decision.reason}

    @guarded(max_steps=1, on_kill=on_kill if policy == "callback" else policy)
    async def operation(*args):
        effects.append("executed")
        return AgentStep(len(effects), "completed")

    args = (AgentStep(1, "requested"),) if pre_call else ()
    await operation(*args)
    stopped = await operation(*args)
    assert "max_steps" in (stopped["stopped"] if isinstance(stopped, dict) else stopped)
    assert len(effects) == (1 if pre_call else 2)


@pytest.mark.parametrize("policy", ["raise", "return", "callback"])
@pytest.mark.parametrize("kind", ["sync", "generator", "async"])
@pytest.mark.asyncio
async def test_already_open_circuit_never_starts_callable_work(kind, policy):
    effects = []
    breaker = CircuitBreaker(GuardConfig(max_steps=1))
    breaker.check(AgentStep(1, "first"))
    breaker.check(AgentStep(2, "crosses cap"))
    before = breaker.report.to_dict()

    def on_kill(decision):
        return {"stopped": decision.reason}

    if kind == "sync":

        def operation():
            effects.append("executed")
            return "done"
    elif kind == "generator":

        def operation():
            effects.append("executed")
            yield "done"
    else:

        async def operation():
            effects.append("executed")
            return "done"

    wrapped = guarded(breaker=breaker, on_kill=on_kill if policy == "callback" else policy)(
        operation
    )

    async def invoke():
        if kind == "generator":
            return list(wrapped())[0]
        if kind == "async":
            return await wrapped()
        return wrapped()

    if policy == "raise":
        with pytest.raises(CircuitBreakerTrippedError, match="max_steps"):
            await invoke()
    else:
        stopped = await invoke()
        assert "max_steps" in (stopped["stopped"] if isinstance(stopped, dict) else stopped)
    assert effects == []
    assert breaker.report.to_dict() == before


def test_generator_kwargs_observation_and_unobservable_items():
    @guarded(max_steps=1, on_kill="return")
    def operation(**kwargs):
        yield "first"
        yield "second"
        raise AssertionError("No third step may run")

    items = list(operation(thought="observable request", tokens_used=5))
    assert items[0] == "first"
    assert "max_steps" in items[1]
    assert operation.report.total_steps == 2
    assert operation.report.total_tokens == 10

    @guarded
    def opaque():
        yield object()

    assert len(list(opaque())) == 1
    assert opaque.report.total_steps == 0


@pytest.mark.asyncio
async def test_async_custom_post_extractor_observes_usage_and_delivers_advice():
    def extract(*, result=None):
        return None if result is None else AgentStep(1, result, action="search", tokens_used=8)

    @guarded(step_extractor=extract, tool_repeat_threshold=1)
    async def operation():
        return "search again"

    assert await operation() == "search again"
    assert operation.report.total_tokens == 8
    assert operation.report.reflections_injected == 1
    assert operation.last_reflection_prompt
