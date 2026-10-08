"""Conversation cleanup through the public protocol helper."""

import pytest

from longguard.integrations.messages import resolve_pending_tool_calls


@pytest.mark.parametrize("protocol", ["openai", "anthropic", "langchain"])
def test_cleanup_preserves_partial_completion_and_is_repeatable(protocol):
    if protocol == "anthropic":
        messages = [
            {
                "role": "assistant",
                "content": [
                    {"type": "tool_use", "id": "done", "name": "read", "input": {}},
                    {"type": "tool_use", "id": "pending", "name": "write", "input": {}},
                ],
            },
            {
                "role": "user",
                "content": [
                    {"type": "tool_result", "tool_use_id": "done", "content": "real result"},
                ],
            },
        ]
    else:
        messages = [
            {
                "role": "assistant",
                "tool_calls": [
                    {"id": "done", "function": {"name": "read", "arguments": "{}"}},
                    {"id": "pending", "function": {"name": "write", "arguments": "{}"}},
                ],
            },
            {"role": "tool", "tool_call_id": "done", "content": "real result"},
        ]
    result = resolve_pending_tool_calls(messages, "loop stopped", protocol=protocol)
    assert result.messages[0] == messages[0]
    if protocol == "anthropic":
        assert result.messages[1]["content"][0] == messages[1]["content"][0]
        assert len(messages[1]["content"]) == 1
    else:
        assert result.messages[1] == messages[1]
    assert result.dispositions == [
        {"tool_call_id": "pending", "name": "write", "status": "skipped", "reason": "loop stopped"}
    ]
    assert "not executed" in str(result.messages)
    assert resolve_pending_tool_calls(
        result.messages, "loop stopped", protocol=protocol
    ).messages == (result.messages)


def test_running_call_is_not_fabricated_as_finished():
    messages = [
        {
            "role": "assistant",
            "tool_calls": [
                {"id": "running", "function": {"name": "write", "arguments": "{}"}},
            ],
        }
    ]
    result = resolve_pending_tool_calls(messages, "stop", running_ids={"running"})
    assert result.messages == messages
    assert result.unresolved_ids == ["running"]
    assert result.dispositions[0]["status"] == "running"


def test_missing_tool_identifier_is_rejected():
    with pytest.raises(ValueError, match="identifier"):
        resolve_pending_tool_calls(
            [{"role": "assistant", "tool_calls": [{"name": "write"}]}], "stop"
        )


@pytest.mark.parametrize("protocol", ["openai", "anthropic", "langchain"])
def test_no_tool_and_multiple_unstarted_calls(protocol):
    ordinary = [{"role": "assistant", "content": "Finished"}]
    assert resolve_pending_tool_calls(ordinary, "stop", protocol=protocol).messages == ordinary
    if protocol == "anthropic":
        requests = [
            {
                "role": "assistant",
                "content": [
                    {"type": "tool_use", "id": call_id, "name": "write", "input": {}}
                    for call_id in ("a", "b", "c")
                ],
            }
        ]
    else:
        requests = [
            {
                "role": "assistant",
                "tool_calls": [
                    {"id": call_id, "function": {"name": "write", "arguments": "{}"}}
                    for call_id in ("a", "b", "c")
                ],
            }
        ]
    result = resolve_pending_tool_calls(requests, "stop", protocol=protocol)
    assert [d["tool_call_id"] for d in result.dispositions] == ["a", "b", "c"]
    assert all(d["status"] == "skipped" for d in result.dispositions)
    if protocol == "anthropic":
        assert all(block["is_error"] for block in result.messages[-1]["content"])
    assert resolve_pending_tool_calls(result.messages, "stop", protocol=protocol).dispositions == []


def test_anthropic_missing_results_precede_user_text_without_reordering_existing_blocks():
    messages = [
        {
            "role": "assistant",
            "content": [
                {"type": "tool_use", "id": "a", "name": "read", "input": {}},
                {"type": "tool_use", "id": "b", "name": "write", "input": {}},
            ],
        },
        {
            "role": "user",
            "content": [
                {"type": "tool_result", "tool_use_id": "a", "content": "real result"},
                {"type": "text", "text": "Use these results"},
            ],
        },
    ]
    result = resolve_pending_tool_calls(messages, "stop", protocol="anthropic")
    blocks = result.messages[-1]["content"]
    assert blocks[0] == messages[-1]["content"][0]
    assert blocks[1]["tool_use_id"] == "b"
    assert blocks[2] == messages[-1]["content"][1]
    assert len(messages[-1]["content"]) == 2
