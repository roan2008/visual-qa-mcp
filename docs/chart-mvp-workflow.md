# Chart V2 Workflow

## Purpose

This document operationalizes the second chart milestone for Visual QA MCP.

Scope:

- Domain: bar charts only
- Input: `visual_spec.json` plus a generated image
- Output: `ClaimGraph`, `EvidenceGraph`, `VisualQaReport`, annotated overlay, validation summary

## V2 Loop

```text
visual spec -> claim graph -> chart image -> plot/tick extraction -> axis mapping -> bar value derivation -> rule checks -> findings report -> overlay -> validation summary
```

## Callable Surface

The current implementation is no longer only a dataset-validation loop. It now exposes a local callable chart-v2 surface that can be wrapped by a future MCP server:

- `build_claim_graph_from_spec(spec_path)`
- `extract_chart_evidence_from_inputs(image_path, spec_path, metadata_path?, backend?)`
- `run_chart_verification(image_path, spec_path, metadata_path?, backend?)`
- `write_verification_artifacts(result, output_dir)`

This improves operability and integration readiness, but it does not expand the current bounded readiness claim and it does not make the optional OCR path ready.

Phase 2 now also includes a thin MCP stdio wrapper over the callable surface plus audit schema upgrades for provenance and rule identifiers.

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

### `ClaimGraph`

Defined in `specs/claim-graph.schema.json`.

Key chart-v2 fields:

- claim-per-check records for bar values, bar count, axis label, axis unit, and scale readability/consistency
- claim-generation gaps for unsupported or unmapped spec checks
- expected values grouped by category instead of being re-derived inside the rule runner
- evidence requirements and tolerances carried with each claim
- metadata linking claims back to the source spec and learning objective

### `VisualQaReport`

Uses `specs/findings.schema.json` with these MVP-relevant fields:

- `verdict`
- `findings`
- `checks_run`
- `checks_skipped`
- `overlay_path`
- `evidence_graph_path`
- `claim_graph_path`
- `overlay_annotations`

## Advisor Gates

### Gate 1: Scale-contract review

Review:

- whether the evidence contract is sufficient to reconstruct numeric value mapping
- whether the claim contract preserves all checkable expectations needed by the rule runner
- whether zero-baseline, non-zero minimum, and signed axes are separated clearly enough
- whether any hidden fallback could reintroduce unsupported passes

Artifact:

- `outputs/advisor/gate-1-evidence.json`

### Gate 2: Implementation review

Review:

- whether claim generation and rule execution stay aligned with the bounded chart-v2 scope
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

## Current CLI Entry Points

```powershell
$env:PYTHONPATH='D:\visual-qa-mcp\mcp-server\src'
python -m visual_qa_mcp.cli build-claim-graph specs\examples\chart-bar.visual-spec.json
python -m visual_qa_mcp.cli extract-chart-evidence datasets\charts\chart-v2\golden\golden-01\image.png datasets\charts\chart-v2\golden\golden-01\visual_spec.json --metadata datasets\charts\chart-v2\golden\golden-01\metadata.json
python -m visual_qa_mcp.cli verify-chart datasets\charts\chart-v2\golden\golden-01\image.png datasets\charts\chart-v2\golden\golden-01\visual_spec.json --metadata datasets\charts\chart-v2\golden\golden-01\metadata.json --output-dir tmp\chart-callable
python -m visual_qa_mcp.cli serve-mcp
python -m visual_qa_mcp.cli generate-noisy-dataset --output datasets\charts\chart-v2-noisy
python -m visual_qa_mcp.cli generate-realworld-pilot --output datasets\charts\chart-v2-realworld-pilot
python -m visual_qa_mcp.cli run-phase2-validation --controlled-dataset datasets\charts\chart-v2 --noisy-dataset datasets\charts\chart-v2-noisy
python -m visual_qa_mcp.cli run-chart-suite-validation --controlled-dataset datasets\charts\chart-v2 --noisy-dataset datasets\charts\chart-v2-noisy --pilot-dataset datasets\charts\chart-v2-realworld-pilot
python -m visual_qa_mcp.cli run-ocr-validation --controlled-dataset datasets\charts\chart-v2 --noisy-dataset datasets\charts\chart-v2-noisy
python -m visual_qa_mcp.cli run-validation --dataset datasets\charts\chart-v2
```

## Phase 2 Validation Boundary

The controlled chart-v2 dataset remains the bounded readiness baseline.

The noisy dataset is a bounded robustness gate for the configured transforms. The real-world pilot is
a separate evidence-expansion track with renderer/reference provenance and frozen checksums. Neither
track justifies a general real-world or OCR readiness claim; all metrics must retain their own
denominators and dataset-family labels.
