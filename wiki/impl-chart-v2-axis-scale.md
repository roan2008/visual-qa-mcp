---
name: impl-chart-v2-axis-scale
description: Chart-v2 baseline, workflow, and bounded readiness claim
metadata:
  type: implementation
  status: current
  last_updated: 2026-07-09
---

# Chart V2 Axis-Scale Baseline

## Scope

The current executable verifier baseline is `chart-v2`, a bar-chart verifier that derives numeric bar values from image-read Y-axis scale evidence instead of metadata-derived scale shortcuts. [source: README.md:53] [source: docs/chart-mvp-workflow.md:1]

The validated local scope is bounded to bar charts in the current generated and semi-realistic dataset family. It supports `zero_baseline`, `non_zero_min`, and `signed` axis modes. [source: docs/chart-mvp-workflow.md:72] [source: wiki/project-log.md:15]

## Evidence Contract

`chart-v2` treats scale evidence as first-class extracted evidence in `EvidenceGraph`. The chart contract includes tick label detections, parsed numeric values, bounding boxes, axis geometry, derived mapping, extraction provenance, and extraction gaps. [source: docs/chart-mvp-workflow.md:18] [source: outputs/advisor/gate-3-review.md:7]

This allows rule execution to depend on explicit scale support rather than hidden metadata assumptions. [source: outputs/advisor/gate-3-review.md:7]

## Workflow

The current chart workflow is:

```text
visual spec -> chart image -> plot/tick extraction -> axis mapping -> bar value derivation -> rule checks -> findings report -> overlay -> validation summary
```

[source: docs/chart-mvp-workflow.md:11]

Operationally, unreadable, contradictory, or insufficient scale evidence must produce `checks_skipped` and escalate the verdict to `needs_review` rather than silently passing or falling back. [source: outputs/advisor/gate-3-review.md:8]

## Backends

The validated default backend is the template tick-reader path. [source: outputs/advisor/gate-3-review.md:27]

An optional OCR backend exists as scaffolded infrastructure, but it is not part of the current readiness claim because OCR accuracy is not yet validated in this environment. [source: outputs/advisor/gate-3-review.md:31] [source: wiki/project-log.md:15]

## Validation Boundary

The current local validation basis is:

- 24 total cases
- 8 golden cases
- 16 mutated cases
- `critical_error_recall = 1.0`
- `typed_mutated_cases = 9`
- `typed_mutated_hits = 9`
- `ambiguous_guard_rate = 1.0`
- `false_unsupported_passes = 0`
- `golden_failures = 0`

[source: outputs/advisor/gate-3-review.md:15] [source: outputs/advisor/validation-summary.json:1]

Signed-axis metrics are tracked separately from zero-baseline and non-zero-minimum subsets. [source: docs/chart-mvp-workflow.md:85] [source: outputs/advisor/validation-summary.json:13]

## Readiness Claim

Advisor review reconciled the current milestone as a bounded, template-backed controlled-to-semi-realistic bar-chart verifier. [source: outputs/advisor/gate-3-review.md:3]

This means the current implementation can be described as ready for the configured template backend and local dataset family, but not as a general real-world chart verifier and not as an OCR-validated verifier. [source: outputs/advisor/gate-3-review.md:38]

## Working Rules For Future Sessions

- Preserve the evidence-first path; do not reintroduce metadata-derived value fallback in `chart-v2`.
- Keep readiness claims bounded to the validated backend and dataset family.
- Report typed recall and ambiguity handling with explicit denominators.
- Require advisor gates for scope freeze, implementation freeze, and readiness review on verifier milestones.
- Prefer `needs_review` over unsupported `pass` whenever required scale evidence is ambiguous or missing.
