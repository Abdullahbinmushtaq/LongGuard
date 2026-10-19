"""CrewAI integration — Step and Crew circuit breaker middleware for LongGuard."""

from __future__ import annotations

import logging
from collections.abc import Callable
from functools import wraps
from inspect import signature
from threading import Lock
from typing import Any

from ..config import GuardConfig
from ..core.breaker import BreakerDecision, CircuitBreaker
from ..core.reporter import GuardReport
from ..core.step import AgentStep

logger = logging.getLogger("longguard.crewai")


class GuardTerminatedException(Exception):  # noqa: N818
    """Raised when LongGuard kills an agent during a CrewAI run.

    Attributes:
        reason: Human-readable kill reason string.
        report: The GuardReport at the time of termination.
        decision: The BreakerDecision that triggered the kill.
    """

    def __init__(
        self,
        reason: str,
        report: GuardReport | None = None,
        decision: BreakerDecision | None = None,
    ) -> None:
        self.reason = reason
        self.report = report
        self.decision = decision
        super().__init__(f"Agent terminated by LongGuard: {reason}")


def _extract_step_from_crewai(
    step_data: Any,
    step_number: int,
) -> AgentStep:
    """Extract an AgentStep from CrewAI's AgentAction, AgentFinish, or dict."""
    if isinstance(step_data, AgentStep):
        return step_data

    thought: str = ""
    action: str | None = None
    action_input: Any | None = None
    observation: str | None = None
    tokens_used: int = 0

    # 1. Dictionary representation
    if isinstance(step_data, dict):
        thought = str(step_data.get("thought", "") or step_data.get("log", ""))
        action = step_data.get("tool") or step_data.get("action")
        action_input = step_data.get("tool_input") or step_data.get("action_input")
        observation = step_data.get("result") or step_data.get("observation")
        tokens_used = int(step_data.get("tokens_used", 0) or step_data.get("tokens", 0))

    # 2. CrewAI AgentAction / AgentFinish object
    elif hasattr(step_data, "tool") or hasattr(step_data, "output"):
        # AgentAction has tool and tool_input
        if hasattr(step_data, "tool"):
            action = getattr(step_data, "tool", None)
            action_input = getattr(step_data, "tool_input", None)
        # Thought or reasoning log
        if hasattr(step_data, "thought"):
            thought = str(getattr(step_data, "thought") or "")
        elif hasattr(step_data, "log"):
            thought = str(getattr(step_data, "log") or "")
        elif hasattr(step_data, "text"):
            thought = str(getattr(step_data, "text") or "")

        # Result / observation
        if hasattr(step_data, "result"):
            observation = str(getattr(step_data, "result") or "")
        elif hasattr(step_data, "observation"):
            observation = str(getattr(step_data, "observation") or "")
        elif hasattr(step_data, "output"):
            observation = str(getattr(step_data, "output") or "")

        if hasattr(step_data, "tokens_used"):
            tokens_used = int(getattr(step_data, "tokens_used") or 0)

    # 3. Tuple of (AgentAction, observation)
    elif isinstance(step_data, (tuple, list)) and len(step_data) >= 1:
        first = step_data[0]
        if hasattr(first, "tool"):
            action = getattr(first, "tool", None)
            action_input = getattr(first, "tool_input", None)
            thought = str(getattr(first, "log", "") or getattr(first, "thought", ""))
        if len(step_data) >= 2:
            observation = str(step_data[1])

    # 4. Fallback string representation
    else:
        thought = str(step_data)

    return AgentStep(
        step_number=step_number,
        thought=thought,
        action=action,
        action_input=action_input,
        observation=observation,
        tokens_used=tokens_used,
    )


class CrewGuard:
    """Circuit breaker manager for CrewAI agents and crews.

    Provides a `step_callback` method that hooks directly into CrewAI's
    agent and crew execution loop, monitoring in-flight tool calls and thoughts.

    Usage::

        from crewai import Agent, Crew, Task
        from longguard import GuardConfig
        from longguard.integrations.crewai import CrewGuard

        guard = CrewGuard(GuardConfig(max_cost_usd=0.50, tool_repeat_threshold=3))

        # Attach to an individual agent:
        researcher = Agent(
            role="Researcher",
            goal="Find market data",
            backstory="...",
            step_callback=guard.step_callback,
        )

        # Or attach to an entire Crew:
        crew = Crew(
            agents=[researcher],
            tasks=[task],
            step_callback=guard.step_callback,
        )

        # Access telemetry afterwards:
        print(guard.summary())

    Args:
        config: GuardConfig with detection thresholds and caps.
        breaker: Optional pre-configured CircuitBreaker instance.
    """

    def __init__(
        self,
        config: GuardConfig | None = None,
        breaker: CircuitBreaker | None = None,
    ) -> None:
        self.config = config or GuardConfig()
        self.breaker = breaker or CircuitBreaker(self.config)
        self.last_reflection: str | None = None
        self._previous_step_callback: Callable[[Any], Any] | None = None
        self._active = False
        self._attached_crew: Any = None
        self._run_lock = Lock()
        self._pending_reflection: str | None = None
        self._last_output: Any = None
        self._notified_callbacks: set[int] = set()
        self._pending_tokens = 0
        self._usage_before: int | None = None
        self._model_serial = 0
        self._observed_serial = -1

    @property
    def report(self) -> GuardReport:
        """The GuardReport of the underlying CircuitBreaker."""
        return self.breaker.report

    def get_report(self) -> GuardReport:
        """Return the GuardReport."""
        return self.breaker.report

    def summary(self) -> str:
        """Return human-readable summary of the run telemetry."""
        return self.breaker.report.summary()

    def reset(self) -> None:
        """Reset breaker state and step history for a new crew run."""
        self.breaker.reset()
        self.last_reflection = None
        self._pending_reflection = None
        self._last_output = None
        self._notified_callbacks.clear()
        self._pending_tokens = 0
        self._model_serial = 0
        self._observed_serial = -1

    def step_callback(self, step_output: Any) -> None:
        """CrewAI step callback hook.

        Inspects the step, evaluates circuit breaker conditions, and terminates
        with `GuardTerminatedException` if a loop or hard cap is tripped.
        """
        callbacks = [self._previous_step_callback] if self._previous_step_callback else []
        self._observe(step_output, callbacks)

    def _observe(self, step_output: Any, callbacks: list[Callable[[Any], Any]]) -> None:
        # CrewAgentExecutor reports ToolResult, then a complete AgentAction.
        # Preserve both callback events; count only the complete action.
        if (
            self._active
            and hasattr(step_output, "result")
            and not (hasattr(step_output, "tool") or hasattr(step_output, "output"))
        ):
            for callback in callbacks:
                callback(step_output)
            return
        if self._active and self._model_serial == self._observed_serial:
            for callback in callbacks:
                if id(callback) not in self._notified_callbacks:
                    callback(step_output)
                    self._notified_callbacks.add(id(callback))
            return
        self._last_output = step_output
        self._observed_serial = self._model_serial
        self._notified_callbacks.clear()
        step_number = len(self.breaker.report.steps) + 1
        agent_step = _extract_step_from_crewai(step_output, step_number=step_number)
        if not agent_step.tokens_used:
            agent_step.tokens_used = self._pending_tokens
        self._pending_tokens = 0
        if not agent_step.tokens_used:
            warning = (
                "CrewAI token usage unavailable; recorded zero is a compatibility default, "
                "not known zero usage."
            )
            if warning not in self.report.usage_warnings:
                self.report.usage_warnings.append(warning)

        decision = self.breaker.check(agent_step)
        for callback in callbacks:
            callback(step_output)
            self._notified_callbacks.add(id(callback))

        if decision.action == "reflect":
            self.last_reflection = decision.inject_prompt
            self._pending_reflection = decision.inject_prompt
            logger.warning(
                "[LongGuard] Reflection triggered on step %d: %s",
                step_number,
                decision.reason,
            )
        elif decision.action == "kill":
            logger.error(
                "[LongGuard] Circuit tripped on step %d: %s",
                step_number,
                decision.reason,
            )
            raise GuardTerminatedException(
                reason=decision.reason,
                report=self.breaker.report,
                decision=decision,
            )

    def _before_model(self, context: Any) -> None:
        if self.breaker.is_open:
            from crewai.hooks.dispatch import HookAborted

            raise HookAborted(reason=self.report.kill_reason or "LongGuard stopped")
        self._model_serial += 1
        if self._pending_reflection:
            context.messages.append({"role": "system", "content": self._pending_reflection})
            self._pending_reflection = None
        summary = getattr(context.llm, "get_token_usage_summary", None)
        self._usage_before = int(summary().total_tokens) if callable(summary) else None

    def _after_model(self, context: Any) -> None:
        summary = getattr(context.llm, "get_token_usage_summary", None)
        if callable(summary) and self._usage_before is not None:
            self._pending_tokens += max(0, int(summary().total_tokens) - self._usage_before)

    def _before_tool(self, context: Any) -> bool | None:
        return False if self.breaker.is_open else None


def _validate_crew_mode(crew: Any) -> None:
    process = getattr(crew, "process", "sequential")
    if getattr(process, "value", process) != "sequential" or getattr(crew, "stream", False):
        raise ValueError("LongGuard supports sequential synchronous non-streaming CrewAI execution")
    if any(getattr(task, "async_execution", False) for task in getattr(crew, "tasks", [])):
        raise ValueError("LongGuard supports synchronous CrewAI tasks only")
    if getattr(crew, "planning", False) or getattr(crew, "memory", False):
        raise ValueError("CrewAI planning/memory model paths are outside the tested guard mode")
    for agent in crew.agents:
        if getattr(agent, "allow_delegation", False) or getattr(agent, "reasoning", False):
            raise ValueError("CrewAI delegation/reasoning model paths are unsupported")
        executor_class = getattr(agent, "executor_class", None)
        if executor_class is not None and executor_class.__name__ != "CrewAgentExecutor":
            raise ValueError(
                "Supported synchronous ReAct mode requires executor_class=CrewAgentExecutor"
            )
        llm = getattr(agent, "llm", None)
        supports_native = getattr(llm, "supports_function_calling", None)
        if callable(supports_native) and supports_native():
            raise ValueError(
                "LongGuard's tested CrewAI mode is synchronous ReAct; "
                "native tool batches are unsupported"
            )


def _wrap_kickoff(crew: Any, guard: CrewGuard) -> None:
    original = crew.kickoff

    @wraps(original)
    def kickoff(*args: Any, **kwargs: Any) -> Any:
        _validate_crew_mode(crew)
        bound = signature(original).bind(*args, **kwargs)
        if bound.arguments.get("from_checkpoint") is not None:
            raise ValueError("CrewAI checkpoint continuation is unsupported by LongGuard")
        try:
            from crewai.hooks.dispatch import HookAborted, InterceptionPoint, scoped_hooks
        except ImportError as exc:
            raise ValueError(
                "This CrewAI version lacks the supported execution-scoped hook API"
            ) from exc
        if not guard._run_lock.acquire(blocking=False):
            raise ValueError("Concurrent execution of the same guarded crew is unsupported")
        try:
            guard.reset()
            guard._active = True
            with scoped_hooks(
                {
                    InterceptionPoint.PRE_MODEL_CALL: [guard._before_model],
                    InterceptionPoint.POST_MODEL_CALL: [guard._after_model],
                    InterceptionPoint.PRE_TOOL_CALL: [guard._before_tool],
                }
            ):
                result = original(*args, **kwargs)
            guard.report.finalize(guard.breaker.state)
            return result
        except HookAborted as exc:
            if guard.breaker.is_open:
                raise GuardTerminatedException(
                    guard.report.kill_reason or "LongGuard stopped",
                    guard.report,
                ) from exc
            raise
        finally:
            guard._active = False
            guard._run_lock.release()

    def unsupported(*args: Any, **kwargs: Any) -> Any:
        raise ValueError("LongGuard supports crew.kickoff() synchronous execution only")

    # Wrap documented public execution entry points, not private executors.
    # Crew is a Pydantic model; object assignment preserves its model fields.
    object.__setattr__(crew, "kickoff", kickoff)
    for name in (
        "kickoff_async",
        "akickoff",
        "kickoff_for_each",
        "kickoff_for_each_async",
        "akickoff_for_each",
    ):
        if hasattr(crew, name):
            object.__setattr__(crew, name, unsupported)


def add_guard_to_crew(
    crew: Any,
    config: GuardConfig | None = None,
    guard: CrewGuard | None = None,
) -> Any:
    """Attach LongGuard protection to all agents in a CrewAI Crew in 1 line.

    Usage::

        from crewai import Crew
        from longguard.integrations.crewai import add_guard_to_crew

        crew = Crew(agents=[...], tasks=[...])
        crew = add_guard_to_crew(crew)
        result = crew.kickoff()

        # Telemetry:
        print(crew.__longguard__.summary())

    Args:
        crew: CrewAI Crew instance.
        config: GuardConfig settings.
        guard: Optional existing CrewGuard instance.

    Returns:
        The same crew instance with LongGuard attached.
    """
    attached = getattr(crew, "__longguard__", None)
    if isinstance(attached, CrewGuard):
        if (guard is not None and guard is not attached) or (
            config is not None and config != attached.config
        ):
            raise ValueError("A different guard/configuration is already attached")
        return crew
    if callable(getattr(crew, "kickoff", None)):
        _validate_crew_mode(crew)
    g = guard or CrewGuard(config=config)
    if g._attached_crew is not None and g._attached_crew is not crew:
        raise ValueError("Use a separate guard for each crew")
    for agent in getattr(crew, "agents", []):
        owner = getattr(agent, "__longguard__", None)
        if isinstance(owner, CrewGuard) and owner is not g:
            raise ValueError("Sharing an already guarded agent between crews is unsupported")
    g._attached_crew = crew

    # 1. Attach to crew step_callback
    existing_crew_cb = getattr(crew, "step_callback", None)
    if existing_crew_cb is not None and existing_crew_cb != g.step_callback:
        g._previous_step_callback = existing_crew_cb
    setattr(crew, "step_callback", g.step_callback)

    # 2. Attach to all agents in the crew
    agents = getattr(crew, "agents", None)
    if agents and isinstance(agents, (list, tuple)):
        for agent in agents:
            object.__setattr__(agent, "__longguard__", g)
            existing_agent_cb = getattr(agent, "step_callback", None)
            if existing_agent_cb is None or existing_agent_cb == g.step_callback:
                setattr(agent, "step_callback", g.step_callback)
            else:
                callbacks = [cb for cb in (existing_crew_cb, existing_agent_cb) if cb is not None]

                def chained(step: Any, callbacks: list[Callable[[Any], Any]] = callbacks) -> None:
                    g._observe(step, callbacks)

                setattr(agent, "step_callback", chained)

    # 3. Store reference for easy retrieval
    setattr(crew, "__longguard__", g)
    if callable(getattr(crew, "kickoff", None)):
        _validate_crew_mode(crew)
        _wrap_kickoff(crew, g)
    return crew
