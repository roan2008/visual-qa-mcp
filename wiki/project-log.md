---
name: project-log
description: Chronological record of completed sessions
metadata:
  type: reference
  status: current
  last_updated: 2026-07-09
---

# Project Log

## 2026-07-09 session 5 - Chart v2 axis-scale extraction

- Upgraded the chart verifier from metadata-derived bar values to axis-scale-derived values.
- Extended `EvidenceGraph` with tick detections, axis mapping, baseline geometry, zero-line support, and backend provenance.
- Added a dual tick-reader design:
  - template backend as the validated local default
  - optional OCR backend scaffold that degrades to `needs_review` when unavailable
- Reworked chart extraction into explicit stages for plot detection, tick extraction, axis mapping, and bar value derivation.
- Added chart-v2 dataset generation with 24 cases: 8 golden and 16 mutated.
- Added support for zero-baseline, non-zero minimum, and signed-axis charts in the controlled-to-semi-realistic dataset family.
- Expanded tests to cover tick reading, new rules, schema validation, end-to-end cases, and optional OCR degradation behavior.
- Refreshed advisor gate evidence packs for chart-v2 and prepared a new readiness review pass.
- Updated `AGENTS.md`, `CLAUDE.md`, `skills/educational-visual-qa/SKILL.md`, and wiki memory so future sessions inherit the chart-v2 baseline and bounded claim policy.

Verification:

- Ran `pytest mcp-server/tests -q` successfully with 18 passing tests.
- Regenerated `datasets/charts/chart-v2/` and validated all 24 cases.
- Current local validation summary reports:
  - `critical_error_recall = 1.0`
  - `ambiguous_guard_rate = 1.0`
  - `false_unsupported_passes = 0`
  - `golden_failures = 0`
  - subset metrics reported for `zero_baseline`, `non_zero_min`, and `signed`.

## 2026-07-09 session 4 - Chart MVP implementation

- Implemented the first executable chart-only MVP in `mcp-server/src/visual_qa_mcp/`.
- Added a chart `EvidenceGraph` contract and schema in `specs/evidence-graph.schema.json`.
- Implemented a synthetic bar-chart dataset generator with 12 cases: 4 golden and 8 mutated.
- Implemented chart evidence extraction, deterministic rules, overlay generation, CLI entrypoints, and validation summary logic.
- Extended `findings.schema.json` to include overlay annotations and evidence graph artifact paths.
- Added verification tests for schemas, rule behavior, and end-to-end dataset execution.
- Generated advisor gate evidence artifacts and recorded a reconciled Gate 3 review.
- Refined validation metrics after advisor feedback so typed defect recall and ambiguity guard behavior are reported separately.

Verification:

- Ran `pytest mcp-server/tests -q` successfully with 14 passing tests.
- Ran the chart validation summary over the 12-case dataset.
- Confirmed `false_unsupported_passes = 0`, `golden_failures = 0`, `critical_error_recall = 1.0` over typed mutated cases, and `ambiguous_guard_rate = 1.0`.

## 2026-07-09 session 3 - Research direction and architecture concepts

- Clarified that the project will not fine-tune foundation models; it will compose existing extractors, deterministic rules, domain validators, and audit reports.
- Discussed product positioning as a fact-checker or verification runtime for AI-generated technical visuals.
- Surveyed external ideas including claim decomposition, chart fact-checking, diagram understanding, domain validators, and high-risk audit discipline.
- Clarified the role of `run_rules` and validators as the decision layer over extracted evidence, including position, direction, distance, angle, alignment, containment, and target checks.
- Discussed a future 3D roadmap that starts with rendered 3D images and later supports native 3D/CAD files.
- Added wiki pages for product direction, rules/validators, and no-tuning/3D strategy.
- Updated `AGENTS.md` and `CLAUDE.md` so future agents preserve the no-fine-tuning strategy, EvidenceGraph/ClaimGraph architecture, and 3D roadmap.

Verification:

- Documentation-only change; no code or schema validation was required.

## 2026-07-09 session 2 - High-assurance direction

- Reframed the project direction toward high-confidence, theory-aligned verification for scientific, medical-education, engineering, chemistry, biology, anatomy, and CAD-derived visuals.
- Added `docs/high-assurance-roadmap.md` to define medical/anatomy, complex chemistry/biology, and full CAD reconstruction as long-term target tracks.
- Updated README, product brief, MVP scope, problem map, `AGENTS.md`, and `CLAUDE.md` so high-risk domains are treated as later high-assurance tracks rather than permanent exclusions.

Verification:

- Documentation-only change; no code or schema validation was required.

## 2026-07-09 session 1 - Initial scaffold

- Created the `visual-qa-mcp` workspace for verified educational visual QA.
- Defined the initial project hypothesis: educational images should be checked with specs, evidence, rules, overlays, and review tiers.
- Added documentation for problem taxonomy, product brief, MVP scope, and validation strategy.
- Added JSON schemas for visual specs and findings reports.
- Added example visual specs for a physics lever diagram, bar chart, and mechanical callout.
- Added a draft `educational-visual-qa` skill.
- Added `CLAUDE.md`, `AGENTS.md`, and initial `wiki/` project memory files.

Verification:

- Parsed every JSON file successfully with PowerShell `ConvertFrom-Json`.
- Listed the project file tree after creation.
