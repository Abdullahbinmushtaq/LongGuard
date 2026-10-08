"""Local real CrewAI execution; install the crewai extra, then run this file."""

import os

os.environ.setdefault("CREWAI_DISABLE_TELEMETRY", "true")
os.environ.setdefault("OTEL_SDK_DISABLED", "true")
os.environ.setdefault("CREWAI_TRACING_ENABLED", "false")

from crewai import Agent, BaseLLM, Crew, Task  # noqa: E402
from crewai.agents.crew_agent_executor import CrewAgentExecutor  # noqa: E402
from crewai.events.event_bus import crewai_event_bus  # noqa: E402
from crewai.tools import tool  # noqa: E402

from longguard import GuardConfig  # noqa: E402
from longguard.integrations.crewai import add_guard_to_crew  # noqa: E402


class LocalModel(BaseLLM):
    """Deterministic model response fixture; the framework execution is real."""

    def __init__(self):
        super().__init__(model="local-example")

    def supports_function_calling(self):
        return False

    def call(self, messages, **kwargs):
        if "LONGGUARD" in str(messages).upper():
            return "Thought: Use the available result.\nFinal Answer: recovered"
        return 'Thought: Search again.\nAction: search\nAction Input: {"query": "same"}'


@tool
def search(query: str) -> str:
    """Return a local search result without external effects."""
    return "Existing evidence"


def main() -> None:
    agent = Agent(
        role="Researcher",
        goal="Finish the task",
        backstory="Local example",
        llm=LocalModel(),
        tools=[search],
        executor_class=CrewAgentExecutor,
        allow_delegation=False,
        max_iter=10,
    )
    task = Task(description="Find an answer", expected_output="An answer", agent=agent)
    crew = Crew(agents=[agent], tasks=[task], tracing=False, cache=False)
    add_guard_to_crew(crew, GuardConfig(tool_repeat_threshold=2, max_reflections=1))
    # Use the public event-listener scope to keep this local example quiet.
    # Model/tool execution and LongGuard's execution hooks still run normally.
    with crewai_event_bus.scoped_handlers():
        result = crew.kickoff()
    assert result.raw == "recovered"
    print(result.raw)
    print(crew.__longguard__.summary())


if __name__ == "__main__":
    try:
        main()
    finally:
        crewai_event_bus.shutdown(wait=False)
