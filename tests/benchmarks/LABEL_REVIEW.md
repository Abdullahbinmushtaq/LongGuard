# Benchmark label review record

Status: **Pending human review**. Dataset: `synthetic-v1`, `corpus.json`.
Author: implementation agent. Independent reviewer: not yet assigned.

Before accepting detector-quality evidence, a human reviewer must read every trace's intent,
positive/negative label, target detector, timing boundary and split. Check related cases and
near duplicates across calibration/evaluation, legitimate retries/polling/new progress, and
synthetic-data limitations. Do not change labels to improve the observed score.

| Review item | Decision / evidence |
|---|---|
| Dataset provenance and MIT licensing | Original local synthetic text; confirm on review |
| Labels and `timely_by` boundaries | Pending |
| Family/split leakage and near-duplicate review | Pending |
| Healthy traces represent useful work | Pending |
| Weak classes and results accepted by release owner | Pending |
| Reviewer, date, dataset SHA256 | Pending |

Record corrections as a new dataset revision with rationale; retain old results. After human
approval, update the corpus review metadata and rerun both baseline and preview evaluations.
Production/adoption claims require separate evidence and are not approved by this record.
