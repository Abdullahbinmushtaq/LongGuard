"""LongGuard model pricing registry.

Provides a best-effort pricing table for common LLM models so that
GuardReport can estimate dollar cost without any external API calls.

Pricing Resolution Tiers
------------------------
1. **User-supplied** (highest priority): Set ``cost_per_input_token`` and
   ``cost_per_output_token`` in :class:`~longguard.config.GuardConfig`.
2. **Built-in table**: This module — a snapshot of provider list prices at
   the time of the LongGuard release.  Updated each minor release.
3. **Graceful fallback**: If the model is not recognised and no per-token
   prices are supplied, ``estimated_cost_usd`` will be ``None`` in the
   report and any ``max_cost_usd`` cap will be silently skipped.

Prices are in **USD per token** (not per 1 000 tokens). They cover standard,
uncached text generation at each provider's base context tier. Cache reads
and writes, batch/priority processing, long-context premiums, other modalities,
and tool fees are not included. Use user-supplied prices for those cases.

Last verified: 2026-10-09. Sources and availability decisions are recorded in
``docs/guides/model-pricing-sources.md``.
"""

from __future__ import annotations

from typing import TypedDict


class ModelPricing(TypedDict):
    """Per-token pricing for a single model."""

    input: float   # USD per input token
    output: float  # USD per output token


# ---------------------------------------------------------------------------
# Built-in pricing table
# Keys are normalised model identifiers.  The lookup is case-insensitive and
# strips leading/trailing whitespace. Only explicitly listed aliases and
# snapshots resolve: arbitrary date suffixes are not stripped because snapshots
# can have different prices or be retired independently.
#
# Source: official provider list prices verified on 2026-10-09.
# See docs/guides/model-pricing-sources.md for the complete source audit.
# ---------------------------------------------------------------------------

PRICING_TABLE: dict[str, ModelPricing] = {
    # ── OpenAI ───────────────────────────────────────────────────────────
    # https://developers.openai.com/api/docs/pricing
    # https://developers.openai.com/api/docs/models
    "gpt-6-astra": {"input": 10e-6, "output": 50e-6},
    "gpt-6.1-sol": {"input": 2e-6, "output": 10e-6},
    "gpt-6-sol": {"input": 2e-6, "output": 10e-6},
    "gpt-6-luna": {"input": 0.1e-6, "output": 0.5e-6},
    "gpt-5.6": {"input": 4e-6, "output": 20e-6},
    "gpt-5.6-sol": {"input": 4e-6, "output": 20e-6},
    "gpt-5.6-terra": {"input": 2e-6, "output": 12e-6},
    "gpt-5.6-luna": {"input": 0.2e-6, "output": 1.2e-6},
    "gpt-5.5": {"input": 5e-6, "output": 30e-6},
    "gpt-5.4": {"input": 2.5e-6, "output": 15e-6},
    "gpt-5.4-mini": {"input": 0.75e-6, "output": 4.5e-6},
    "gpt-5.4-nano": {"input": 0.2e-6, "output": 1.25e-6},
    "gpt-5.2": {"input": 1.75e-6, "output": 14e-6},
    "gpt-5.1": {"input": 1.25e-6, "output": 10e-6},
    "gpt-5": {"input": 1.25e-6, "output": 10e-6},
    "gpt-5-mini": {"input": 0.25e-6, "output": 2e-6},
    "gpt-5-nano": {"input": 0.05e-6, "output": 0.4e-6},
    "gpt-4.1": {"input": 2e-6, "output": 8e-6},
    "gpt-4.1-2025-04-14": {"input": 2e-6, "output": 8e-6},
    "gpt-4.1-mini": {"input": 0.4e-6, "output": 1.6e-6},
    "gpt-4.1-nano": {"input": 0.1e-6, "output": 0.4e-6},
    "gpt-4o": {"input": 2.5e-6, "output": 10e-6},
    "gpt-4o-2024-08-06": {"input": 2.5e-6, "output": 10e-6},
    "gpt-4o-2024-11-20": {"input": 2.5e-6, "output": 10e-6},
    "gpt-4o-mini": {"input": 0.15e-6, "output": 0.6e-6},
    "gpt-4o-mini-2024-07-18": {"input": 0.15e-6, "output": 0.6e-6},
    # ── Anthropic ────────────────────────────────────────────────────────
    # https://platform.claude.com/docs/en/about-claude/pricing
    "claude-fable-5-1": {"input": 10e-6, "output": 50e-6},
    "claude-fable-5": {"input": 10e-6, "output": 50e-6},
    "claude-opus-5-5": {"input": 4e-6, "output": 20e-6},
    "claude-opus-5": {"input": 5e-6, "output": 25e-6},
    "claude-opus-4-8": {"input": 5e-6, "output": 25e-6},
    "claude-opus-4-7": {"input": 5e-6, "output": 25e-6},
    "claude-opus-4-6": {"input": 5e-6, "output": 25e-6},
    "claude-opus-4-5": {"input": 5e-6, "output": 25e-6},
    "claude-opus-4-5-20251101": {"input": 5e-6, "output": 25e-6},
    "claude-sonnet-5-5": {"input": 2e-6, "output": 10e-6},
    "claude-sonnet-5": {"input": 2e-6, "output": 10e-6},
    "claude-sonnet-4-6": {"input": 3e-6, "output": 15e-6},
    "claude-sonnet-4-5": {"input": 3e-6, "output": 15e-6},
    "claude-sonnet-4-5-20250929": {"input": 3e-6, "output": 15e-6},
    # Haiku base rates apply to prompts with <=100K input tokens.
    "claude-haiku-5-5": {"input": 0.1e-6, "output": 0.5e-6},
    "claude-haiku-4-5": {"input": 1e-6, "output": 5e-6},
    "claude-haiku-4-5-20251001": {"input": 1e-6, "output": 5e-6},
    # ── Google ───────────────────────────────────────────────────────────
    # https://ai.google.dev/gemini-api/docs/pricing
    # Promotional rates for 3.6/3.7/3.8 Flash run through 2026-12-31.
    "gemini-3.8-flash": {"input": 0.75e-6, "output": 3.75e-6},
    "gemini-3.7-flash": {"input": 0.75e-6, "output": 3.75e-6},
    "gemini-3.6-flash": {"input": 0.75e-6, "output": 3.75e-6},
    "gemini-3.5-flash": {"input": 1.5e-6, "output": 9e-6},
    "gemini-3.5-flash-lite": {"input": 0.3e-6, "output": 2.5e-6},
    "gemini-3.1-pro-preview": {"input": 2e-6, "output": 12e-6},
    "gemini-3.1-pro-preview-customtools": {"input": 2e-6, "output": 12e-6},
    "gemini-3.1-flash-lite": {"input": 0.25e-6, "output": 1.5e-6},
    "gemini-3-flash-preview": {"input": 0.5e-6, "output": 3e-6},

    # ── Groq (provider-specific hosted model prices) ─────────────────────
    # https://console.groq.com/docs/models
    "openai/gpt-oss-120b": {"input": 0.15e-6, "output": 0.6e-6},
    "openai/gpt-oss-20b": {"input": 0.075e-6, "output": 0.3e-6},
    "qwen/qwen3.8-27b": {"input": 0.8e-6, "output": 4e-6},
    # ── Mistral ──────────────────────────────────────────────────────────
    # https://docs.mistral.ai/inference/pricing
    # Large 4 launch prices: 50% off for two weeks from 2026-10-06.
    "mistral-large-4": {"input": 0.68e-6, "output": 2.09e-6},
    "mistral-large-4-0": {"input": 0.68e-6, "output": 2.09e-6},
    "mistral-large-2512": {"input": 0.5e-6, "output": 1.5e-6},
    "mistral-large-latest": {"input": 0.5e-6, "output": 1.5e-6},
    "mistral-medium-3-5": {"input": 1.5e-6, "output": 7.5e-6},
    "mistral-medium-latest": {"input": 1.5e-6, "output": 7.5e-6},
    "mistral-small-2603": {"input": 0.15e-6, "output": 0.6e-6},
    "mistral-small-latest": {"input": 0.15e-6, "output": 0.6e-6},
    "codestral-2508": {"input": 0.3e-6, "output": 0.9e-6},
    "codestral-latest": {"input": 0.3e-6, "output": 0.9e-6},
    "ministral-14b-2512": {"input": 0.2e-6, "output": 0.2e-6},
    "ministral-14b-latest": {"input": 0.2e-6, "output": 0.2e-6},
    "ministral-8b-2512": {"input": 0.15e-6, "output": 0.15e-6},
    "ministral-8b-latest": {"input": 0.15e-6, "output": 0.15e-6},
    "ministral-3b-2512": {"input": 0.1e-6, "output": 0.1e-6},
    "ministral-3b-latest": {"input": 0.1e-6, "output": 0.1e-6},
    # ── Cohere ───────────────────────────────────────────────────────────
    # https://cohere.com/pricing
    # The bare aliases target older, deprecated snapshots for existing users.

    "command-r-08-2024": {"input": 0.15e-6, "output": 0.6e-6},
    "command-r7b-12-2024": {"input": 0.0375e-6, "output": 0.15e-6},
    "command-a-03-2025": {"input": 2.5e-6, "output": 10e-6},
}


def _normalise(model: str) -> str:
    """Normalise a model identifier for table lookup."""
    return model.strip().lower()


def lookup(model: str) -> ModelPricing | None:
    """Look up pricing for a model.

    The lookup is case-insensitive.  Returns ``None`` if the model is not
    in the built-in table (use user-supplied prices in that case).

    Args:
        model: Model identifier, e.g. ``"gpt-6.1-sol"`` or ``"claude-sonnet-5-5"``.

    Returns:
        A :class:`ModelPricing` dict with ``"input"`` and ``"output"`` per-token
        prices in USD, or ``None`` if the model is not recognised.

    Example::

        from longguard.pricing import lookup
        pricing = lookup("gpt-4o")
        # {"input": 2.5e-06, "output": 1e-05}
    """
    return PRICING_TABLE.get(_normalise(model))


def compute_cost(
    model: str | None,
    input_tokens: int,
    output_tokens: int,
    *,
    cost_per_input_token: float | None = None,
    cost_per_output_token: float | None = None,
) -> float | None:
    """Compute estimated USD cost for a generation.

    Resolution order:
    1. ``cost_per_input_token`` / ``cost_per_output_token`` — if both supplied,
       they win unconditionally.
    2. Built-in ``PRICING_TABLE`` lookup by ``model``.
    3. ``None`` — returned when pricing cannot be determined.

    Args:
        model: Model identifier (used for table lookup). May be ``None``.
        input_tokens: Number of input tokens in the generation.
        output_tokens: Number of output tokens in the generation.
        cost_per_input_token: Override price per input token (USD).
        cost_per_output_token: Override price per output token (USD).

    Returns:
        Estimated cost in USD, or ``None`` if pricing is unavailable.

    Example::

        cost = compute_cost("gpt-4o", input_tokens=1000, output_tokens=500)
        # 0.0075 (= 1000 * 2.5e-6 + 500 * 10e-6)
    """
    # Tier 1: user-supplied prices
    if cost_per_input_token is not None and cost_per_output_token is not None:
        return (
            input_tokens * cost_per_input_token
            + output_tokens * cost_per_output_token
        )

    # Tier 2: built-in table
    if model is not None:
        pricing = lookup(model)
        if pricing is not None:
            return (
                input_tokens * pricing["input"]
                + output_tokens * pricing["output"]
            )

    # Tier 3: graceful fallback
    return None


def list_supported_models() -> list[str]:
    """Return a sorted list of model identifiers in the built-in pricing table.

    Returns:
        Sorted list of supported model identifier strings.

    Example::

        from longguard.pricing import list_supported_models
        models = list_supported_models()
        # Includes 'claude-sonnet-5-5', 'gemini-3.8-flash', 'gpt-6.1-sol', ...
    """
    return sorted(PRICING_TABLE.keys())
