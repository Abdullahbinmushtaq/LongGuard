# LangGraph Integration

LongGuard provides seamless, non-invasive integration for **LangGraph 1.0+**.

---

## 1-Line StateGraph Wrapping

The easiest way to guard your LangGraph workflow is `add_guard_to_graph()`:

```python
from langgraph.graph import StateGraph, START, END
from longguard.integrations.langgraph import add_guard_to_graph
from longguard import GuardConfig

# 1. Build your StateGraph as usual
workflow = StateGraph(AgentState)
workflow.add_node("agent", agent_node)
workflow.add_node("tools", tool_node)
workflow.add_edge(START, "agent")
workflow.add_conditional_edges("agent", should_continue, ["tools", END])
workflow.add_edge("tools", "agent")

# 2. Add LongGuard in one line
workflow = add_guard_to_graph(workflow, GuardConfig(
    tool_repeat_threshold=3,
    max_tokens_per_run=50_000,
    max_steps=25,
))

app = workflow.compile()
```

---

## What Happens When Terminated?

When the circuit breaker opens and kills the agent:
1. LongGuard preserves the full `messages` history.
2. It appends an explanation message to `messages`:
   ```
   [LongGuard] Agent terminated: reflection_failed: tool_repeat (confidence: 100%).
   The agent was stuck in a reasoning loop and could not recover after reflection attempts.
   ```
3. It sets `__longguard_terminated__ = True` and `__longguard_reason__ = "..."` on the state dictionary.
4. Your `should_continue` conditional edge can safely terminate to `END` without unhandled crashes:

```python
def should_continue(state: AgentState):
    if state.get("__longguard_terminated__"):
        return END
    if not state["messages"][-1].tool_calls:
        return END
    return "tools"
```

---

## Excluding Execution Nodes

By default, `add_guard_to_graph` ignores execution-only nodes (`"tools"`, `"action"`, `"__start__"`, `"__end__"`). You can customize this list:

```python
workflow = add_guard_to_graph(
    workflow,
    GuardConfig(),
    exclude_nodes=["tools", "my_custom_db_writer"],
)
```

---

## Accessing Telemetry

After execution, the guard report is stored on the graph instance:

```python
guard = workflow.__longguard__
print(guard.get_report().summary())
```


## Explicit checkpoint continuation (development preview)

For isolated runs and safe explicit continuation, use the additive controller:

```python
from langgraph.checkpoint.memory import InMemorySaver
from longguard import GuardConfig, compile_guarded_graph

# graph must have START -> agent -> tools/END and tools -> agent.
runner = compile_guarded_graph(graph, GuardConfig(max_steps=30), checkpointer=InMemorySaver())
config = {"configurable": {"thread_id": "job-1"}}
result = runner.invoke({"messages": messages}, config)
if result.get("__longguard_terminated__"):
    print(runner.get_report("job-1").kill_reason)
    # Human/application must explicitly choose correction; a hard-cap stop is ineligible.
    result = runner.resume(config, correction="Use the existing results and finish",
                           additional_reflections=1)
```

The controller stops at persisted node boundaries before dispatching a killed turn's tools.
Original-ID pending calls receive truthful skipped/error results; completed results remain.
Advice is delivered after pending tool results and before the next agent. Run a copyable
stop/resume example with `python examples/langgraph_resume.py` after installing the graph extra.

Only detector-recovery failures with budget remaining can resume. A nonempty correction and
positive finite reflection grant are required. Tokens, steps, estimated cost, detections and
reflection count remain cumulative. A changed checkpoint, implicit reinvocation, unknown run,
completed run or concurrent continuation is rejected. A different `thread_id` starts a new run
with an independent report. A loaded report or checkpoint alone cannot reconstruct the live
guard in a different process.

Support is synchronous, one agent node plus one tool node. Async, streaming, parallel graph
nodes, subgraphs, branching and namespaces are outside the tested contract. See
[tested compatibility](../guides/compatibility.md). Completed tools are not replayed by the
supported resume path; arbitrary application crashes and external side effects still require
application idempotency.

The existing `add_guard_to_graph` retains its API. Excluded tool/action nodes now raise
`CircuitBreakerTrippedError` if routing attempts to dispatch them after termination. Reusing
that legacy graph shares one mutable guard; explicitly reset for a new run. Use the controlled
runner for independent thread accounting.
