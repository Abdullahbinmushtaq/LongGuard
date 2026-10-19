# Model pricing source audit

Verified on **2026-10-09** against official provider documentation. Prices below
are **USD per million tokens**, written as **input / output**. The Python registry
stores these amounts divided by 1,000,000. This is a standard, uncached text API
snapshot, not a live availability check or a guarantee of access for an account.

The supported-price tables below match the project's selected built-in registry
in `src/longguard/pricing.py`. A model can be excluded by project selection even
while its provider still offers it. The decision tables distinguish those
exclusions from retirement or unverifiable pricing. Use `list_supported_models()`
for the current supported IDs and explicit per-token overrides for excluded models.

## OpenAI

The official [pricing page](https://developers.openai.com/api/docs/pricing)
and individual model cards verify standard text rates for the selected entries.

| Model ID | Input / output | Source |
| --- | --- | --- |
| `gpt-6-astra` | 10 / 50 | [Astra](https://developers.openai.com/api/docs/models/gpt-6-astra) |
| `gpt-6.1-sol` | 2 / 10 | [6.1 Sol](https://developers.openai.com/api/docs/models/gpt-6.1-sol) |
| `gpt-6-sol` | 2 / 10 | [Sol](https://developers.openai.com/api/docs/models/gpt-6-sol) |
| `gpt-6-luna` | 0.10 / 0.50 | [Luna](https://developers.openai.com/api/docs/models/gpt-6-luna) |
| `gpt-5.6`, `gpt-5.6-sol` | 4 / 20 | [5.6 Sol and its alias](https://developers.openai.com/api/docs/models/gpt-5.6-sol) |
| `gpt-5.6-terra` | 2 / 12 | [Terra](https://developers.openai.com/api/docs/models/gpt-5.6-terra) |
| `gpt-5.6-luna` | 0.20 / 1.20 | [5.6 Luna](https://developers.openai.com/api/docs/models/gpt-5.6-luna) |
| `gpt-5.5` | 5 / 30 | [5.5](https://developers.openai.com/api/docs/models/gpt-5.5) |
| `gpt-5.4` | 2.50 / 15 | [5.4](https://developers.openai.com/api/docs/models/gpt-5.4) |
| `gpt-5.4-mini` | 0.75 / 4.50 | [5.4 Mini](https://developers.openai.com/api/docs/models/gpt-5.4-mini) |
| `gpt-5.4-nano` | 0.20 / 1.25 | [5.4 Nano](https://developers.openai.com/api/docs/models/gpt-5.4-nano) |
| `gpt-5.2` | 1.75 / 14 | [5.2](https://developers.openai.com/api/docs/models/gpt-5.2) |
| `gpt-5.1` | 1.25 / 10 | [5.1](https://developers.openai.com/api/docs/models/gpt-5.1) |
| `gpt-5` | 1.25 / 10 | [5](https://developers.openai.com/api/docs/models/gpt-5) |
| `gpt-5-mini` | 0.25 / 2 | [5 Mini](https://developers.openai.com/api/docs/models/gpt-5-mini) |
| `gpt-5-nano` | 0.05 / 0.40 | [5 Nano](https://developers.openai.com/api/docs/models/gpt-5-nano) |
| `gpt-4.1`, `gpt-4.1-2025-04-14` | 2 / 8 | [4.1](https://developers.openai.com/api/docs/models/gpt-4.1) |
| `gpt-4.1-mini` | 0.40 / 1.60 | [4.1 Mini](https://developers.openai.com/api/docs/models/gpt-4.1-mini) |
| `gpt-4.1-nano` | 0.10 / 0.40 | [4.1 Nano](https://developers.openai.com/api/docs/models/gpt-4.1-nano) |
| `gpt-4o`, `gpt-4o-2024-08-06`, `gpt-4o-2024-11-20` | 2.50 / 10 | [4o](https://developers.openai.com/api/docs/models/gpt-4o) |
| `gpt-4o-mini`, `gpt-4o-mini-2024-07-18` | 0.15 / 0.60 | [4o Mini](https://developers.openai.com/api/docs/models/gpt-4o-mini) |

GPT-6, GPT-5.6, GPT-5.5 and GPT-5.4 base rates apply through 272,000
input tokens; larger requests have 2x input and 1.5x output rates. GPT-5.4
Mini/Nano use their own model-card prices. GPT-5.6 Sol's promotional price is
guaranteed at least through November 21, 2026. Cache writes, cached inputs,
service tiers, regions and tool use incur separate rates. See the linked cards
and [pricing details](https://developers.openai.com/api/docs/pricing).

Provider retirement dates follow the authoritative
[deprecation schedule](https://developers.openai.com/api/docs/deprecations),
which takes precedence over a model card that still displays historical prices:

| Existing IDs | Decision and reason |
| --- | --- |
| `gpt-4-turbo-preview` | Remove; its underlying January 2024 preview retired March 26, 2026. |
| `o1-mini` | Remove; retired October 27, 2025. |
| `o3` | Excluded by project selection; its snapshot's scheduled provider retirement is December 11, 2026. |
| `gpt-4-turbo`, `gpt-4`, `gpt-3.5-turbo` | Excluded by project selection; scheduled provider retirement is October 23, 2026. |
| `o1`, `o3-mini`, `o4-mini` | Excluded by project selection; this does not assert provider retirement. |
| `gpt-4o`, `gpt-4o-mini`, `gpt-4o-mini-2024-07-18` | Retain their verified rates. |

The added GPT-5/5 Mini/5 Nano releases retire December 11, 2026;
GPT-5.1 and GPT-5.4 Nano retire April 1, 2027. Their presence estimates currently
billable usage, and is not a recommendation to choose a deprecated model.
Only listed snapshots resolve; no arbitrary suffix removal or provider-prefix
stripping is performed. GPT-4o's May 2024 snapshot is intentionally not mapped
to the cheaper August/November 2024 rates.

## Anthropic

The [pricing table](https://platform.claude.com/docs/en/about-claude/pricing)
and [model lifecycle table](https://platform.claude.com/docs/en/about-claude/model-deprecations)
support the following public Claude API entries:

| Model ID | Input / output |
| --- | --- |
| `claude-fable-5-1`, `claude-fable-5` | 10 / 50 |
| `claude-opus-5-5` | 4 / 20 |
| `claude-opus-5`, `claude-opus-4-8`, `claude-opus-4-7`, `claude-opus-4-6` | 5 / 25 |
| `claude-opus-4-5`, `claude-opus-4-5-20251101` | 5 / 25 |
| `claude-sonnet-5-5`, `claude-sonnet-5` | 2 / 10 |
| `claude-sonnet-4-6` | 3 / 15 |
| `claude-sonnet-4-5`, `claude-sonnet-4-5-20250929` | 3 / 15 |
| `claude-haiku-5-5` | 0.10 / 0.50 |
| `claude-haiku-4-5`, `claude-haiku-4-5-20251001` | 1 / 5 |

Haiku 5.5's base rate applies through **100,000 input tokens**; larger prompts
cost **0.50 / 2.50**. Sonnet 4.5 is deprecated but available through November 30,
2026. Restricted-access Mythos models are omitted. Standard prices exclude
caching, batch, fast mode, tools, and geography premiums. See the
[pricing details](https://platform.claude.com/docs/en/about-claude/pricing).

Aliases are verified in the official [Opus 4.5](https://platform.claude.com/docs/en/models/opus-4-5/overview),
[Sonnet 4.5](https://platform.claude.com/docs/en/models/sonnet-4-5/overview), and
[Haiku 4.5](https://platform.claude.com/docs/en/models/haiku-4-5/overview) cards.
From 4.6 onwards, dateless IDs are pinned releases; see
[model IDs and versioning](https://platform.claude.com/docs/en/about-claude/models/model-ids-and-versions).

Existing table audit, using the official
[retirement history](https://platform.claude.com/docs/en/about-claude/model-deprecations):

| Existing IDs | Decision and reason |
| --- | --- |
| `claude-3-5-sonnet`, `claude-3-5-sonnet-20241022` | Remove; Sonnet 3.5 retired October 28, 2025. |
| `claude-3-5-haiku`, `claude-3-5-haiku-20241022` | Remove; Haiku 3.5 retired February 19, 2026. |
| `claude-3-opus`, `claude-3-opus-20240229` | Remove; Opus 3 retired January 5, 2026. |
| `claude-3-sonnet` | Remove; Sonnet 3 retired July 21, 2025. |
| `claude-3-haiku`, `claude-3-haiku-20240307` | Remove; Haiku 3 retired April 20, 2026. |
| `claude-sonnet-4`, `claude-opus-4` | Remove; their dated releases retired June 15, 2026. |
| `claude-haiku-4` | Remove; no such public model ID verified in the current catalog. |

## Google Gemini Developer API

The [standard paid pricing table](https://ai.google.dev/gemini-api/docs/pricing)
verifies these text rates:

| Model ID | Input / output |
| --- | --- |
| `gemini-3.8-flash`, `gemini-3.7-flash`, `gemini-3.6-flash` | 0.75 / 3.75 |
| `gemini-3.5-flash` | 1.50 / 9 |
| `gemini-3.5-flash-lite` | 0.30 / 2.50 |
| `gemini-3.1-flash-lite` | 0.25 / 1.50 |
| `gemini-3.1-pro-preview`, `gemini-3.1-pro-preview-customtools` | 2 / 12 |
| `gemini-3-flash-preview` | 0.50 / 3 |

**Scheduled price change:** the 3.8, 3.7, and 3.6 Flash rates above expire
**December 31, 2026**; they become **1.50 / 7.50 on January 1, 2027**.
Pro rates apply through 200,000 input tokens: larger 3.1 Pro prompts cost
**4 / 18**. Output includes
thinking tokens. Audio input, caching, batch/flex/priority, and tools have
different rates. [Pricing](https://ai.google.dev/gemini-api/docs/pricing).

Gemini 2.5 models are excluded from the project's built-in registry. At the
verification date, the [deprecation table](https://ai.google.dev/gemini-api/docs/deprecations)
restricts them to existing users without an announced shutdown; their exclusion
does not assert that the provider has retired them.

| Existing ID | Decision and reason |
| --- | --- |
| `gemini-1.5-pro`, `gemini-1.5-flash`, `gemini-1.5-flash-8b` | Remove; shut down September 29, 2025, per [release notes](https://ai.google.dev/gemini-api/docs/changelog). |
| `gemini-2.0-flash`, `gemini-2.0-flash-lite` | Remove; shut down June 1, 2026, per [deprecations](https://ai.google.dev/gemini-api/docs/deprecations). |
| `gemini-2.5-pro`, `gemini-2.5-flash`, `gemini-2.5-flash-lite` | Excluded by project selection. |

## Groq

The [current model catalog](https://console.groq.com/docs/models) verifies:

| Model ID | Input / output | Availability |
| --- | --- | --- |
| `openai/gpt-oss-120b` | 0.15 / 0.60 | Production |
| `openai/gpt-oss-20b` | 0.075 / 0.30 | Production |
| `qwen/qwen3.8-27b` | 0.80 / 4 | Preview |

These are Groq-hosted prices, not OpenAI API or generic open-weight-model prices.
Speech and safety-only models are outside this text-generation scope.

| Existing ID | Decision and reason |
| --- | --- |
| `llama-3.1-8b-instant`, `llama-3.3-70b-versatile` | Remove fixed prices; free/developer shutdown August 16, 2026, while committed-spend enterprise access remains with contact-sales pricing. |
| `llama-3.1-70b-versatile` | Remove; shut down January 24, 2025. |
| `llama-3.1-405b-reasoning` | Remove; neither current availability nor its listed price was verified in the official Groq catalog. |

Shutdown dates and enterprise exceptions come from
[Groq deprecations](https://console.groq.com/docs/deprecations); custom-price
availability comes from the [catalog](https://console.groq.com/docs/models).

## Mistral

The [standard USD pricing table](https://docs.mistral.ai/inference/pricing)
and individual cards verify:

| Model ID | Input / output | Model card |
| --- | --- | --- |
| `mistral-large-4`, `mistral-large-4-0` | 0.68 / 2.09 | [Large 4](https://docs.mistral.ai/models/mistral-large-4-0) |
| `mistral-large-2512`, `mistral-large-latest` | 0.50 / 1.50 | [Large 3](https://docs.mistral.ai/models/mistral-large-3-25-12) |
| `mistral-medium-3-5`, `mistral-medium-latest` | 1.50 / 7.50 | [Medium 3.5](https://docs.mistral.ai/models/mistral-medium-3-5-26-04) |
| `mistral-small-2603`, `mistral-small-latest` | 0.15 / 0.60 | [Small 4](https://docs.mistral.ai/models/mistral-small-4-0-26-03) |
| `ministral-14b-2512`, `ministral-14b-latest` | 0.20 / 0.20 | [14B](https://docs.mistral.ai/models/ministral-3-14b-25-12) |
| `ministral-8b-2512`, `ministral-8b-latest` | 0.15 / 0.15 | [8B](https://docs.mistral.ai/models/ministral-3-8b-25-12) |
| `ministral-3b-2512`, `ministral-3b-latest` | 0.10 / 0.10 | [3B](https://docs.mistral.ai/models/ministral-3-3b-25-12) |
| `codestral-2508`, `codestral-latest` | 0.30 / 0.90 | [Codestral](https://docs.mistral.ai/models/codestral-25-08) |

**Short-lived launch sale:** Large 4's normal rate is **1.36 / 4.18**.
The [October 6 release](https://docs.mistral.ai/resources/changelogs) advertises
50% off for two weeks; refresh the snapshot around **October 20, 2026**. Large 4
is a public preview. Its `-4-0` ID is also used in official
[reasoning examples](https://docs.mistral.ai/studio/conversations/reasoning).

The `-latest` mappings are explicit in the
[Vibe CLI configuration documentation](https://docs.mistral.ai/vibe/code/cli/configuration).
In particular, `mistral-large-latest` still refers to Large 3, not the Large 4
preview. Aliases can change prices and behavior under the
[lifecycle policy](https://docs.mistral.ai/inference/model-lifecycle).

| Existing ID | Decision and reason |
| --- | --- |
| `mistral-large` | Remove; the bare identifier's current API mapping was not verified. Replace with the verified IDs above. |
| `mistral-small` | Remove; historical endpoint renamed in 2024, and current mapping not verified. Use `mistral-small-latest` or `mistral-small-2603`. |
| `mistral-nemo` | Remove; bare ID and price not verified in current catalog. Historical API ID was `open-mistral-nemo`. |
| `codestral` | Remove; bare ID's API mapping not verified. Use `codestral-latest` or `codestral-2508`; current rates differ from the old table. |

The historical Small/Nemo names come from the official
[changelog](https://docs.mistral.ai/resources/changelogs). These removals identify
unsupported or unverifiable registry entries, not a claim that every old Mistral
release has retired on every hosting platform.

## Cohere

The [live-model catalog](https://docs.cohere.com/docs/models) and model cards
verify the selected entries:

| Model ID | Input / output | Source |
| --- | --- | --- |
| `command-a-03-2025` | 2.50 / 10 | [Command A](https://docs.cohere.com/v2/docs/command-a) |
| `command-r-08-2024` | 0.15 / 0.60 | [Command R](https://docs.cohere.com/v1/docs/command-r) |
| `command-r7b-12-2024` | 0.0375 / 0.15 | [Command R7B](https://docs.cohere.com/v1/docs/command-r7b) |

| Excluded IDs | Decision and reason |
| --- | --- |
| `command-r`, `command-r-03-2024`, `command-r-plus`, `command-r-plus-04-2024` | Excluded by project selection; the generic aliases target older March/April 2024 snapshots. |
| `command-r-plus-08-2024` | Excluded by project selection; this does not assert provider retirement. |

The older snapshots are deprecated for new users, while existing-user access
continues until retirement under [Cohere's lifecycle definition](https://docs.cohere.com/docs/deprecations).
See the [legacy pricing FAQ](https://cohere.com/pricing) for historical pricing.

The live `command-a-plus-05-2026`, `command-a-reasoning-08-2025`,
`command-a-translate-08-2025`, and `command-a-vision-07-2025` have no verified
flat paid token rate. Their cards state free API access through rate limits,
with production through Model Vault or sales. Do not invent a paid rate or
represent contracted production as zero cost. Sources:
[A+](https://docs.cohere.com/v1/docs/command-a-plus),
[Reasoning](https://docs.cohere.com/v1/docs/command-a-reasoning),
[Translate](https://docs.cohere.com/v1/docs/command-a-translate),
[Vision](https://docs.cohere.com/v1/docs/command-a-vision).

## Estimation limits

The current `ModelPricing` interface has only input/output prices. It cannot
represent long-context tiers, cache hits/writes, region or service-tier
multipliers, modality rates, server-tool charges, or contract pricing. Built-in
entries therefore estimate ordinary uncached text usage at the base tier.
Supply explicit per-token overrides for other billing arrangements. Account
permissions and provider lifecycle changes can affect whether an API call works.
