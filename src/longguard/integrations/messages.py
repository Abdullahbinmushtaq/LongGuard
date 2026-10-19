"""Protocol-specific cleanup of unstarted tool calls; never dispatches tools."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Literal


@dataclass
class ToolCleanup:
    """Preserved conversation plus honest dispositions for unresolved calls."""

    messages: list[Any]
    dispositions: list[dict[str, Any]] = field(default_factory=list)
    unresolved_ids: list[str] = field(default_factory=list)


def _value(message: Any, key: str, default: Any = None) -> Any:
    return (
        message.get(key, default) if isinstance(message, dict) else getattr(message, key, default)
    )


def resolve_pending_tool_calls(
    messages: list[Any],
    reason: str,
    *,
    protocol: Literal["langchain", "openai", "anthropic"] = "openai",
    running_ids: set[str] | None = None,
) -> ToolCleanup:
    """Preserve history and add failed/skipped results for unstarted calls.

    The caller must stop dispatch before using this helper. Running calls are
    left unresolved: wait for their real result before continuing. Message
    objects and provider dictionaries are retained rather than rewritten.
    """
    if protocol not in {"langchain", "openai", "anthropic"}:
        raise ValueError(f"Unsupported tool protocol: {protocol}")
    pending: dict[str, str] = {}
    completed: set[str] = set()
    for message in messages:
        role = _value(message, "role", _value(message, "type", ""))
        if role in {"tool", "function"}:
            result_id = _value(message, "tool_call_id")
            if result_id:
                completed.add(str(result_id))
        content = _value(message, "content", [])
        if isinstance(content, list):
            for block in content:
                if not isinstance(block, dict):
                    continue
                if block.get("type") == "tool_result":
                    completed.add(str(block["tool_use_id"]))
                elif block.get("type") == "tool_use":
                    call_id = block.get("id")
                    if not call_id:
                        raise ValueError("A tool request is missing its original identifier")
                    pending[str(call_id)] = str(block.get("name", ""))
        calls = _value(message, "tool_calls", None)
        if not calls:
            calls = _value(message, "additional_kwargs", {}).get("tool_calls", [])
        for call in calls:
            call_id = call.get("id")
            if not call_id:
                raise ValueError("A tool request is missing its original identifier")
            pending[str(call_id)] = str(
                call.get("name") or call.get("function", {}).get("name", "")
            )

    result = ToolCleanup(messages=list(messages))
    blocks: list[dict[str, Any]] = []
    for call_id, name in pending.items():
        if call_id in completed:
            continue
        running = call_id in (running_ids or set())
        result.dispositions.append(
            {
                "tool_call_id": call_id,
                "name": name,
                "status": "running" if running else "skipped",
                "reason": reason,
            }
        )
        if running:
            result.unresolved_ids.append(call_id)
            continue
        content_text = f"[LongGuard] Tool not executed; skipped because execution stopped: {reason}"
        if protocol == "anthropic":
            blocks.append(
                {
                    "type": "tool_result",
                    "tool_use_id": call_id,
                    "content": content_text,
                    "is_error": True,
                }
            )
        elif protocol == "langchain" and any(not isinstance(m, dict) for m in messages):
            from langchain_core.messages import ToolMessage

            result.messages.append(
                ToolMessage(
                    content=content_text,
                    tool_call_id=call_id,
                    name=name,
                    status="error",
                )
            )
        else:
            result.messages.append(
                {
                    "role": "tool",
                    "type": "tool",
                    "tool_call_id": call_id,
                    "content": content_text,
                }
                if protocol == "langchain"
                else {
                    "role": "tool",
                    "tool_call_id": call_id,
                    "content": content_text,
                }
            )
    if blocks:
        # Anthropic groups all tool results in the user turn immediately after
        # tool_use. Merge with an existing partial result turn without changing
        # the original blocks or mutating the caller's list.
        last = result.messages[-1] if result.messages else None
        if (
            isinstance(last, dict)
            and last.get("role") == "user"
            and isinstance(last.get("content"), list)
        ):
            original_blocks = last["content"]
            # Provider protocol puts tool results before any user text. Preserve
            # existing block order while filling the incomplete result prefix.
            boundary = next(
                (
                    index
                    for index, block in enumerate(original_blocks)
                    if not isinstance(block, dict) or block.get("type") != "tool_result"
                ),
                len(original_blocks),
            )
            result.messages[-1] = {
                **last,
                "content": [*original_blocks[:boundary], *blocks, *original_blocks[boundary:]],
            }
        else:
            result.messages.append({"role": "user", "content": blocks})
    return result
