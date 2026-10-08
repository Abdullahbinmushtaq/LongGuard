# Framework coverage and controlled continuation for the v0.2.0 preview

A detector trip could return `continue` on the next clean observation, CrewAI advice was stored
without delivered recovery, and LangGraph termination could leave pending calls or dispatch
excluded tools. This preview keeps OPEN terminal, bounds advice across recoveries, delivers
advice in the supported CrewAI ReAct mode, and adds explicit checkpoint continuation using the
existing breaker with cumulative consumption and original-ID skipped tool results.

It preserves core APIs/defaults, optional dependencies, old report loading, provider converters,
decorator behavior and estimated pricing. New reporting fields are additive. The graph controller
supports one synchronous agent/tools cycle in the same process. CrewAI support requires the
tested public sequential ReAct executor; unsupported modes fail clearly.

Validation: original baseline suite, Python 3.10/3.11 core checks, real framework contract tests,
Ruff, strict MyPy, documentation/build checks, local examples and clean-install/upgrade checks.
Exact current results and commands are in `docs/guides/development-evidence.md` and generated
`release-evidence.json`. Hash/Jaccard benchmark counts are unchanged from baseline; weak classes
are disclosed. Synthetic labels still require human review.

Release workflow generates literal notes, verifies requested source/tag/version, runs actual
gates and creates candidate-aware drafts. This is unpublished `0.2.0.dev0`, not stable release
approval. Human labels/quality acceptance, hosted CI and candidate feedback remain maintainer gates.
