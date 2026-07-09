# Chart V2 Workflow

## Purpose

This document operationalizes the second chart milestone for Visual QA MCP.

Scope:

- Domain: bar charts only
- Input: `visual_spec.json` plus a generated image
- Output: `EvidenceGraph`, `VisualQaReport`, annotated overlay, validation summary

## V2 Loop

```text
visual spec -> chart image -> plot/tick extraction -> axis mapping -> bar value derivation -> rule checks -> findings report -> overlay -> validation summary
```

## Contracts

### `VisualSpec`

Uses `specs/visual-spec.schema.json` and now expects chart source data plus axis expectations in `source_reference.axis`.

### `EvidenceGraph`

Defined in `specs/evidence-graph.schema.json`.

Key chart-v2 fields:

- tick label detections with parsed numeric values
- axis geometry: line x, top y, baseline y, optional zero-line y
- derived axis mapping: min/max, pixels per unit, scale mode
- extracted bars with raw geometry and axis-derived values
- extraction provenance through `backend`
- extraction gaps used to drive `checks_skipped`

### `VisualQaReport`

Uses `specs/findings.schema.json` with these MVP-relevant fields:

- `verdict`
- `findings`
- `checks_run`
- `checks_skipped`
- `overlay_path`
- `evidence_graph_path`
- `overlay_annotations`

## Advisor Gates

### Gate 1: Scale-contract review

Review:

- whether the evidence contract is sufficient to reconstruct numeric value mapping
- whether zero-baseline, non-zero minimum, and signed axes are separated clearly enough
- whether any hidden fallback could reintroduce unsupported passes

Artifact:

- `outputs/advisor/gate-1-evidence.json`

### Gate 2: Implementation review

Review:

- whether the template/OCR dual path is cleanly separated
- whether ambiguity cases correctly escalate to `needs_review`
- whether the dataset is broad enough for the chart-v2 claim

Artifact:

- `outputs/advisor/gate-2-evidence.json`

### Gate 3: Readiness review

Review:

- validation summary
- subset metrics by axis mode
- configured backend versus optional backend boundaries
- known unknowns and recommendation boundaries

Artifacts:

- `outputs/advisor/gate-3-evidence.json`
- `outputs/advisor/gate-3-review.md`

## Validation Dataset

Dataset root:

- `datasets/charts/chart-v2/`

Composition:

- 8 golden cases
- 16 mutated cases

Coverage includes:

- zero-baseline positive charts
- non-zero minimum charts
- signed charts with positive and negative bars
- layout, font, and color variation
- missing, unreadable, and contradictory tick evidence
- shifted scale labels
- wrong bar heights
- extra and missing bars
- optional OCR-stretch case

## Success Targets

- 24 out of 24 cases produce schema-valid reports
- typed scale-related critical defect recall >= 0.85
- ambiguity guard rate = 1.00
- false unsupported passes = 0
- golden fail count = 0
- signed-axis metrics are reported separately from zero-baseline metrics
