# Reproducible detector evaluation

The benchmark uses actual detector implementations and actual circuit decisions. It makes
no provider calls, uploads or simulated similarity-score substitutions. Results are
**provisional because human label review is pending**.

## Reproduce

From the repository root, install development dependencies and run:

```bash
uv sync --extra dev
uv run --no-sync python benchmarks/run.py --output benchmarks/results/current-hash.json
```

The runner explicitly selects hash embeddings for semantic oscillation and Jaccard for
dead-end drift. An installed optional backend does not silently change this evaluation.
For sentence-transformers, supply a local model snapshot and its pinned revision:

```bash
uv run --no-sync python benchmarks/run.py --backend sentence-transformers   --model-path /path/to/local/snapshot --model-revision COMMIT_SHA   --output /tmp/longguard-semantic-results.json
```

No sentence-transformers model run is claimed in the preview evidence. Hash/Jaccard results
cannot establish transformer-backend quality.

## Corpus and assessment

`benchmarks/corpus.json` contains 40 original synthetic traces under the repository MIT
license: two calibration and eight held-out evaluation traces per detector. Each evaluation
group has four loop labels and four healthy labels. The corpus and labels were written
before evaluation; related named families cannot cross splits. Traces remain small and
correlated, so these counts are not production incident rates or independent statistical
samples. The implementation author also authored the labels; a second human must review
intent, timing and split separation using `benchmarks/LABEL_REVIEW.md`.

The assessment unit is one trace for its assigned detector. A positive is timely if first
detection is on or before its `timely_by` step. Calibration is excluded, not silently used
to tune defaults. The runner records TP/FP/TN/FN, precision, recall, false-positive rate,
denominators, errors, skips, first detection and every circuit outcome. Undefined ratios
are JSON `null`. Circuit evaluation runs all detectors independently of each trace's target
label; raw detector accuracy and recovery success are different measurements.

## Observed hash/Jaccard results

These counts match the unchanged release-baseline detectors and preview detectors.

| Detector | TP | FP | TN | FN | Precision | Recall | False-positive rate |
|---|---:|---:|---:|---:|---:|---:|---:|
| Tool repeat | 4 | 1 | 3 | 0 | 0.80 | 1.00 | 0.25 |
| Semantic oscillation | 4 | 2 | 2 | 0 | 0.67 | 1.00 | 0.50 |
| Dead-end drift | 3 | 1 | 3 | 1 | 0.75 | 0.75 | 0.25 |
| Token velocity | 4 | 1 | 3 | 0 | 0.80 | 1.00 | 0.25 |

Legitimate polling can trigger repetition/dead-end rules, similar useful text can trigger
semantic oscillation, and justified large output can trigger token velocity. Switching
unproductive actions can hide a dead end. These are exposed limitations, not reasons to
silently remove negative traces or tune defaults on the evaluation split.

`benchmarks/results/baseline-hash.json` evaluates source exported from release commit
`7b02104b47277cb5948c84e9ca4830e5f27df8c4`; `current-hash.json` evaluates the edited preview.
Each stores source and corpus hashes, command, environment, thresholds, backend, errors and
per-trace outcomes. Working-tree flags describe the execution checkout; source paths and
hashes identify the actually imported package. Package installation metadata can differ
from exported baseline source; `source_version` records the imported version.

Latency records separate backend initialization, breaker construction, standalone embedding
and complete warmed `guard.check` calls. They exclude model/network/tool execution. An
extra embedding probe warms the same texts before guard checks; this is explicitly a warm
workload, not first-call end-to-end latency. Timings depend on the local machine. They do
not establish application latency, saved tokens, saved dollars or production adoption.

## Release decision

Maintainers must approve labels, review weak classes and decide whether quality is acceptable
before release. The roadmap supplies no fixed accuracy threshold. Keep the original results,
record the reviewer and any dataset revision, then evaluate again without relabeling to match
scores. Candidate feedback must include useful polling/retries/progress and real failure cases.

Static corpus replay records 21 circuit stops and no clean recovery-after-advice outcomes in
the measured hash run. It does not respond to injected prompts. Delivered advice and successful
recovery are demonstrated separately by real-framework local tests and examples.
