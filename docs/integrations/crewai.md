# CrewAI integration

Use the existing `add_guard_to_crew` API for the tested sequential synchronous ReAct mode.
It preserves prior agent and crew callbacks, injects Reflect & Pivot into the next model
context, and raises `GuardTerminatedException` on unrecoverable loops or hard caps.

```python
from crewai.agents.crew_agent_executor import CrewAgentExecutor
from longguard import GuardConfig
from longguard.integrations.crewai import add_guard_to_crew, GuardTerminatedException

# Configure your Agent with executor_class=CrewAgentExecutor, allow_delegation=False,
# a ReAct LLM (supports_function_calling() is False), and synchronous tasks.
crew = add_guard_to_crew(crew, GuardConfig(tool_repeat_threshold=3, max_steps=30))
try:
    result = crew.kickoff()
except GuardTerminatedException as exc:
    print(exc.reason)
    exc.report.save("stopped-crew.json")
```

See [tested compatibility](../guides/compatibility.md) before adapting an existing crew.
The declared dependency minimum is broader than the execution-hook versions tested. Missing
public scoped-hook APIs produce a clear error. Async, native tool batches, streaming,
hierarchical processing, checkpoint continuation and additional model paths are unsupported.
The deprecated public `CrewAgentExecutor` is selected explicitly; no private executor methods
are replaced. LongGuard wraps the public kickoff entry point and scopes its hooks to execution.

Every kickoff starts a fresh report and budget. Concurrent kickoff of the same guarded crew
is rejected. Reattaching the same guard is idempotent; changing an attached configuration
requires a new crew. Execution callbacks receive their normal events. ToolResult and the
complete AgentAction can both arrive for a tool turn; the action is accounted once.

CrewAI can suppress identical tool execution itself. Repeated model tool requests are still
observed. Missing usage appears in `usage_warnings`; cost is estimated, not billed spend.
A tool in the current turn may finish before its action callback trips the circuit.

Callback-only `CrewGuard.step_callback` remains available. It exposes `last_reflection` but
cannot automatically deliver it or govern every execution path. Use full attachment for the
tested advice/termination contract.

The credential-free `examples/crewai_guarded.py` runs actual CrewAI with a deterministic local
model and tool. No provider SDK calls, secrets or paid requests are required. Tests isolate
only CrewAI credential-file storage and unrelated event listeners; execution remains real.
