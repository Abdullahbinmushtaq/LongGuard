"""Run with the langgraph extra; no credentials or provider requests are needed."""

from langchain_core.messages import AIMessage, HumanMessage, ToolMessage
from langgraph.checkpoint.memory import InMemorySaver
from langgraph.graph import END, START, MessagesState, StateGraph

from longguard import GuardConfig, compile_guarded_graph


def main() -> None:
    effects: list[str] = []

    def agent(state):
        if any(isinstance(m, HumanMessage) and m.content == "finish" for m in state["messages"]):
            return {"messages": [AIMessage(content="Finished using existing results.")]}
        index = sum(isinstance(m, AIMessage) for m in state["messages"])
        return {
            "messages": [
                AIMessage(
                    content="Search again",
                    tool_calls=[
                        {"id": f"search_{index}", "name": "search", "args": {"query": "same"}}
                    ],
                )
            ]
        }

    def tools(state):
        messages = []
        for call in state["messages"][-1].tool_calls:
            effects.append(call["id"])
            messages.append(ToolMessage(content="Existing evidence", tool_call_id=call["id"]))
        return {"messages": messages}

    graph = StateGraph(MessagesState)
    graph.add_node("agent", agent)
    graph.add_node("tools", tools)
    graph.add_edge(START, "agent")
    graph.add_conditional_edges(
        "agent",
        lambda state: "tools" if state["messages"][-1].tool_calls else END,
        {"tools": "tools", END: END},
    )
    graph.add_edge("tools", "agent")
    runner = compile_guarded_graph(
        graph, GuardConfig(tool_repeat_threshold=2, max_reflections=1), checkpointer=InMemorySaver()
    )
    config = {"configurable": {"thread_id": "local-example"}}
    stopped = runner.invoke({"messages": [HumanMessage(content="Find an answer")]}, config)
    assert stopped["__longguard_terminated__"]
    completed_effects = list(effects)
    result = runner.resume(config, correction="finish", additional_reflections=1)
    assert effects == completed_effects  # Resume does not execute completed tool calls again.
    print(result["messages"][-1].content)
    print("Completed tools:", effects)
    print(runner.get_report("local-example").summary())


if __name__ == "__main__":
    main()
