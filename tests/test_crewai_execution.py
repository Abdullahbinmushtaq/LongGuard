"""Real CrewAI sequential ReAct execution using a local model/tool boundary."""

# Imports follow optional dependency detection and credential isolation.
# ruff: noqa: E402

import os
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

import pytest

os.environ.setdefault("OTEL_SDK_DISABLED", "true")
os.environ.setdefault("CREWAI_DISABLE_TELEMETRY", "true")
os.environ.setdefault("CREWAI_STORAGE_DIR", "/tmp/longguard-crewai-tests")
os.environ.setdefault("CREWAI_TRACING_ENABLED", "false")
token_module = pytest.importorskip("crewai_core.token_manager")
credential_directory = TemporaryDirectory(prefix="longguard-test-credentials-")
with patch.object(
    token_module.TokenManager,
    "_get_secure_storage_path",
    return_value=Path(credential_directory.name),
):
    pytest.importorskip("crewai")

from crewai import Agent, BaseLLM, Crew, Task
from crewai.agents.crew_agent_executor import CrewAgentExecutor
from crewai.events.event_bus import crewai_event_bus
from crewai.tools import tool

from longguard import GuardConfig
from longguard.integrations.crewai import GuardTerminatedException, add_guard_to_crew


@pytest.fixture(autouse=True)
def isolate_framework_credentials():
    """Stub only external credential-file location; use actual framework execution."""
    with (
        patch.object(
            token_module.TokenManager,
            "_get_secure_storage_path",
            return_value=Path(credential_directory.name),
        ),
        crewai_event_bus.scoped_handlers(),
    ):
        yield


@pytest.fixture(scope="session", autouse=True)
def close_framework_event_loop():
    yield
    crewai_event_bus.shutdown(wait=False)


class LocalModel(BaseLLM):
    def __init__(self, *, recover, finish_first=False):
        super().__init__(model="local-fixture")
        self.calls = 0
        self.recover = recover
        self.finish_first = finish_first
        self.received_reflection = False

    def call(self, messages, **kwargs):
        self.calls += 1
        self.received_reflection |= any(
            "Reflect" in str(m) or "LONGGUARD" in str(m).upper() for m in messages
        )
        if self.finish_first or (self.recover and self.received_reflection):
            return "Thought: I will finish with available evidence.\nFinal Answer: finished"
        return 'Thought: Search again.\nAction: search\nAction Input: {"q": "same"}'

    def supports_function_calling(self):
        return False


def make_crew(*, recover=False, max_steps=30, finish_first=False):
    effects = []
    callbacks = []

    @tool
    def search(q: str) -> str:
        """Return a deterministic search result."""
        effects.append(q)
        return "same result"

    model = LocalModel(recover=recover, finish_first=finish_first)
    agent = Agent(
        role="Researcher",
        goal="Complete the task",
        backstory="Local fixture",
        llm=model,
        tools=[search],
        allow_delegation=False,
        max_iter=10,
        step_callback=lambda step: callbacks.append("agent"),
        executor_class=CrewAgentExecutor,
    )
    task = Task(description="Find the answer", expected_output="An answer", agent=agent)
    crew = Crew(
        agents=[agent],
        tasks=[task],
        cache=False,
        tracing=False,
        step_callback=lambda step: callbacks.append("crew"),
    )
    add_guard_to_crew(
        crew, GuardConfig(tool_repeat_threshold=2, max_reflections=1, max_steps=max_steps)
    )
    return crew, model, effects, callbacks


def test_real_crew_receives_reflection_and_recovers():
    crew, model, effects, callbacks = make_crew(recover=True)
    result = crew.kickoff()
    assert result.raw == "finished"
    assert model.received_reflection
    assert crew.__longguard__.report.reflections_injected == 1
    assert callbacks.count("agent") == callbacks.count("crew") == 5
    assert crew.__longguard__.report.total_steps == 3
    # CrewAI suppresses identical tool re-execution; repeated requests are
    # still observed, and their callbacks must not count twice per model turn.
    assert effects == ["same"]


def test_real_failed_recovery_stops_and_reattachment_is_idempotent():
    crew, model, effects, callbacks = make_crew()
    guard = crew.__longguard__
    assert add_guard_to_crew(crew).__longguard__ is guard
    with pytest.raises(GuardTerminatedException):
        crew.kickoff()
    assert model.calls == 3
    assert effects == ["same"]
    assert guard.report.total_steps == 3
    assert callbacks.count("agent") == callbacks.count("crew") == 6
    prior = guard.report
    with pytest.raises(GuardTerminatedException):
        crew.kickoff()
    assert guard.report.run_id != prior.run_id
    assert guard.report.total_steps == prior.total_steps == 3


def test_real_hard_cap_prevents_next_model_call_and_async_is_rejected():
    crew, model, effects, _ = make_crew(max_steps=1)
    with pytest.raises(GuardTerminatedException, match="max_steps"):
        crew.kickoff()
    assert model.calls == 2
    assert effects == ["same"]
    with pytest.raises(ValueError, match="synchronous"):
        crew.kickoff_async()


def test_real_normal_completion_has_no_unnecessary_intervention():
    crew, model, effects, callbacks = make_crew(finish_first=True)
    assert crew.kickoff().raw == "finished"
    assert model.calls == 1
    assert effects == []
    assert callbacks == ["crew", "agent"]
    assert crew.__longguard__.report.reflections_injected == 0
    assert crew.__longguard__.report.usage_warnings


def test_unsupported_mode_is_rejected_without_partial_attachment():
    crew, _, _, _ = make_crew(finish_first=True)
    # A separate real crew has the unsupported execution mode before attachment.
    fresh = Crew(
        agents=crew.agents,
        tasks=crew.tasks,
        process="hierarchical",
        manager_llm=LocalModel(recover=False),
        tracing=False,
    )
    prior = fresh.step_callback
    with pytest.raises(ValueError, match="sequential"):
        add_guard_to_crew(fresh)
    assert fresh.step_callback is prior
    assert not hasattr(fresh, "__longguard__")


def test_shared_guarded_agents_are_rejected_before_callbacks_are_changed():
    crew, _, _, _ = make_crew(finish_first=True)
    fresh = Crew(agents=crew.agents, tasks=crew.tasks, tracing=False)
    prior = fresh.step_callback
    with pytest.raises(ValueError, match="Sharing"):
        add_guard_to_crew(fresh)
    assert fresh.step_callback is prior
    assert not hasattr(fresh, "__longguard__")
