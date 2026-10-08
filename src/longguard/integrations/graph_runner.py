"""Same-process synchronous LangGraph continuation at checkpoint boundaries."""

from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass, field
from threading import Lock
from typing import Any

from ..config import GuardConfig
from ..core.breaker import BreakerState
from ..core.reporter import GuardReport
from .langgraph import LongGuard
from .messages import resolve_pending_tool_calls


@dataclass
class _Run:
    guard: LongGuard
    lock: Any = field(default_factory=Lock)
    status: str = "active"
    checkpoint_id: str | None = None
    pending_prompt: str | None = None


class GuardedGraph:
    """Drive a synchronous agent/tools graph through saved node boundaries.

    Call ``invoke`` once per new thread and ``resume`` explicitly for an eligible
    stopped thread. Run state is local to this controller; a checkpoint or a
    loaded report alone cannot restore it in another process. Only the tested
    single-agent/single-tool-node topology is accepted.
    """

    def __init__(
        self,
        graph: Any,
        config: GuardConfig | None = None,
        *,
        checkpointer: Any,
        agent_node: str = "agent",
        tool_node: str = "tools",
    ) -> None:
        if hasattr(graph, "__longguard__"):
            raise ValueError("Pass an unwrapped graph to the controlled runner")
        if checkpointer is None:
            raise ValueError("Guarded continuation requires a checkpointer")
        self.config = deepcopy(config) if config is not None else GuardConfig()
        self.agent_node = agent_node
        self.tool_node = tool_node
        self._graph = graph.compile(
            checkpointer=checkpointer,
            interrupt_after=[agent_node, tool_node],
        )
        shape = self._graph.get_graph()
        if set(shape.nodes) != {"__start__", "__end__", agent_node, tool_node}:
            raise ValueError("Supported graph contains only agent and tools nodes")
        edges = {(e.source, e.target) for e in shape.edges}
        if edges != {
            ("__start__", agent_node),
            (agent_node, tool_node),
            (agent_node, "__end__"),
            (tool_node, agent_node),
        }:
            raise ValueError("Unsupported graph topology; use START -> agent -> tools/END -> agent")
        self._runs: dict[str, _Run] = {}
        self._registry_lock = Lock()

    @staticmethod
    def _thread(config: dict[str, Any]) -> str:
        configurable = config.get("configurable", {})
        thread = configurable.get("thread_id")
        if not isinstance(thread, str) or not thread:
            raise ValueError("A nonempty string thread_id is required")
        if configurable.get("checkpoint_ns") or configurable.get("checkpoint_id"):
            raise ValueError("Checkpoint branching/namespaces are unsupported by this controller")
        return thread

    def get_report(self, thread_id: str) -> GuardReport:
        """Get the cumulative telemetry report for an identified local run."""
        if thread_id not in self._runs:
            raise ValueError("Unknown thread; no live guard state is available")
        return self._runs[thread_id].guard.get_report()

    def get_state(self, config: dict[str, Any]) -> Any:
        """Inspect the framework checkpoint; this does not authorize continuation."""
        self._thread(config)
        return self._graph.get_state(config)

    def invoke(self, inputs: dict[str, Any] | None, config: dict[str, Any]) -> dict[str, Any]:
        """Start a new guarded run. Existing threads require explicit resume."""
        config = {**config, "configurable": dict(config.get("configurable", {}))}
        thread = self._thread(config)
        with self._registry_lock:
            if thread in self._runs:
                raise ValueError("Existing threads require explicit resume or a new thread_id")
            if inputs is None or not isinstance(inputs.get("messages"), list):
                raise ValueError("A new run requires an input messages list")
            if self._graph.get_state(config).values:
                raise ValueError(
                    "Existing checkpoint has no matching live guard; cannot start unguarded"
                )
            run = _Run(LongGuard(deepcopy(self.config)))
            self._runs[thread] = run
        with run.lock:
            return self._drive(run, inputs, config)

    def _drive(
        self,
        run: _Run,
        inputs: dict[str, Any] | None,
        config: dict[str, Any],
    ) -> dict[str, Any]:
        from langchain_core.messages import SystemMessage

        next_nodes = (
            (self.agent_node,) if inputs is not None else self._graph.get_state(config).next
        )
        try:
            while next_nodes:
                if len(next_nodes) != 1 or next_nodes[0] not in {self.agent_node, self.tool_node}:
                    raise ValueError(
                        "Parallel execution or an unsupported node boundary was encountered"
                    )
                node = next_nodes[0]
                self._graph.invoke(inputs, config)
                inputs = None
                snapshot = self._graph.get_state(config)
                values = dict(snapshot.values)
                if node == self.agent_node:
                    step = run.guard._extract_step(values)
                    latest = values["messages"][-1]
                    usage = getattr(latest, "usage_metadata", None)
                    if usage and usage.get("total_tokens") is not None:
                        step.tokens_used = int(usage["total_tokens"])
                    else:
                        warning = (
                            "LangGraph token usage is estimated from observable text, "
                            "not provider billing."
                        )
                        if warning not in run.guard.get_report().usage_warnings:
                            run.guard.get_report().usage_warnings.append(warning)
                    decision = run.guard.breaker.check(step)
                    if decision.action == "kill":
                        return self._stop(run, values, config, decision.reason)
                    if decision.action == "reflect":
                        run.pending_prompt = decision.inject_prompt
                # Deliver reflection after tool results, before the next agent.
                if run.pending_prompt and (node == self.tool_node or not snapshot.next):
                    self._graph.update_state(
                        config,
                        {
                            "messages": [SystemMessage(content=run.pending_prompt)],
                        },
                        as_node=self.tool_node,
                    )
                    run.pending_prompt = None
                    snapshot = self._graph.get_state(config)
                next_nodes = snapshot.next
            run.status = "completed"
            run.guard.get_report().finalize(BreakerState.CLOSED)
            return dict(self._graph.get_state(config).values)
        except Exception:
            run.status = "failed"
            raise

    def _stop(
        self,
        run: _Run,
        values: dict[str, Any],
        config: dict[str, Any],
        reason: str,
    ) -> dict[str, Any]:
        from langchain_core.messages import AIMessage

        messages = values["messages"]
        cleanup = resolve_pending_tool_calls(messages, reason, protocol="langchain")
        if cleanup.unresolved_ids:
            raise ValueError("Running tools must finish before supported continuation")
        run.guard.get_report().tool_dispositions.extend(cleanup.dispositions)
        additions = cleanup.messages[len(messages) :]
        additions.append(AIMessage(content=f"[LongGuard] Agent terminated: {reason}"))
        self._graph.update_state(config, {"messages": additions}, as_node=self.agent_node)
        snapshot = self._graph.get_state(config)
        run.checkpoint_id = snapshot.config["configurable"]["checkpoint_id"]
        run.status = "stopped"
        run.pending_prompt = None
        return {**snapshot.values, "__longguard_terminated__": True, "__longguard_reason__": reason}

    def resume(
        self,
        config: dict[str, Any],
        *,
        correction: str,
        additional_reflections: int = 1,
    ) -> dict[str, Any]:
        """Continue an eligible stopped checkpoint after explicit corrective input."""
        from langchain_core.messages import HumanMessage

        config = {**config, "configurable": dict(config.get("configurable", {}))}
        thread = self._thread(config)
        run = self._runs.get(thread)
        if run is None:
            raise ValueError("Unknown thread; no live guard state is available")
        if not run.lock.acquire(blocking=False):
            raise ValueError("A continuation of this thread is already in progress")
        try:
            if run.status != "stopped":
                raise ValueError("Only a stopped checkpoint can resume")
            snapshot = self._graph.get_state(config)
            if snapshot.config["configurable"].get("checkpoint_id") != run.checkpoint_id:
                raise ValueError("Checkpoint changed; stopped guard state is incompatible")
            run.guard.breaker.validate_resume(
                correction=correction,
                additional_reflections=additional_reflections,
            )
            self._graph.update_state(
                config,
                {
                    "messages": [HumanMessage(content=correction)],
                },
                as_node=self.tool_node,
            )
            run.guard.breaker.resume(
                correction=correction,
                additional_reflections=additional_reflections,
            )
            run.status = "active"
            return self._drive(run, None, config)
        finally:
            run.lock.release()
