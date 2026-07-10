---
name: next-steps
description: Current priority and queued follow-up work
metadata:
  type: reference
  status: current
  last_updated: 2026-07-10
---

# Next Steps

## Current Priority

### 2026-07-10 session 14 - COMPLETE

Completed `geometry-v1`, the third executable vertical, from the partially implemented state left
by the interrupted Claude session.

Delivered:

- controlled mechanical plate extractor and rules for hole count, relative diameter ratios,
  declared linear alignment/spacing, and fixed-catalog dimension text
- `geometry-evidence-graph.schema.json`, service entrypoints, CLI generate/verify/validate commands,
  and six geometry/arrow MCP tools alongside the original chart tools
- `datasets/mechanical/geometry-v1` with 5 golden and 9 mutated cases
- installable package discovery and the `visual-qa` console command
- focused geometry, schema, MCP, and packaging tests

Verified:

- geometry controlled: typed hits `7/7`, ambiguity guards `2/2`, hole-count evidence `13/13`,
  false unsupported passes `0`, golden non-passes `0`, verdict mismatches `0`
- all 70 tests pass when run in bounded groups; the unchanged end-to-end chart file passes all
  16 tests but takes about 4m19s because it repeatedly rebuilds/revalidates full datasets

Bounds: controlled Pillow renders only; single rectangular plate; circular holes; fixed dimension
catalog; ordered hole pairing; no noisy/real-world track, general OCR, unit calibration, general
callout arrows, or CAD-native geometry.

### 2026-07-10 session 13 - COMPLETE

Implemented the translational force-balance rule for arrow-v1 — the first theory-aware
(Level 3) check — closing suggested-next-work item 1 after running its deferred advisor gate.

Design decisions (advisor gate): magnitude = extractor pixel vectors summed directly (no
spec-declared magnitudes, no px-to-newton calibration in v1); equilibrium is opt-in via
`source_reference.scenario_type = "equilibrium"` + a `force-balance-correct` check, with
either half alone becoming a ClaimGraph gap; scope is translational balance only, finding
type `force_balance_violation`.

Delivered:

- `force-balance-correct` claim branch in `build_arrow_claim_graph` with two-way
  scenario/check gating gaps
- fifth rule block in `arrow_rules.run_arrow_claims`: resultant-ratio criterion
  (`|resultant| / max(length_px)` vs. tolerance 0.15), partial-force-set refusal, per-arrow
  vector evidence, overlay annotation
- extractor gap coverage so `ambiguous_arrow_colors` also gates the balance check
- `datasets/physics/arrow-v1` grown to 17 cases: `golden-06` (balanced equilibrium),
  `mutated-10` (shortened weight arrow — first defect class invisible to all four prior
  rules), `mutated-11` (ambiguity guard under declared equilibrium)
- `force_balance_metrics` in the arrow validation summary

Verified:

- 61 tests pass (56 prior + 5 new)
- arrow-v1 controlled (17 cases): typed hits `8/8`, ambiguous guard `3/3`, force-balance
  `1/1`, false unsupported passes `0`, golden failures `0`
- arrow-v1-noisy unchanged (`4/4`, `0` unsupported passes); chart-v2 controlled unchanged
  (`9/9`, guard `1.0`, `0`/`0`)

Bounds: translational balance only (no torque/moments), opt-in per spec, controlled renders
only; deferred px-to-newton calibration and non-zero expected resultants.

### 2026-07-10 session 12 - COMPLETE

Added label-based arrow identity as a second, noise-robust identity signal for arrow-v1 and
built the first arrow-v1 noisy track, closing suggested-next-work item 1 from session 11.

Delivered:

- `arrow_labels.py`: fixed-catalog template-matched label decoder (`W,N,F,f,T,P,Fx,Fy`),
  mirroring the chart-v2 tick-reader pattern
- label-first identity resolution in `arrow_rules._match_arrows_by_color`, with color as
  fallback; `ambiguous_arrow_colors` gap suppressed when labels resolve identity
- tail/head extremity fix in `arrow_extractor._end_statistics` (true geometric extremity
  instead of a windowed average) so label crop regions align correctly
- `datasets/physics/arrow-v1` grown to 14 cases (5 golden, 9 mutated) with label rendering
- new `datasets/physics/arrow-v1-noisy` (6 cases: 2 golden, 4 typed mutated) with
  blur/downscale/JPEG postprocessing, CLI command `generate-noisy-arrow-dataset`
- fixed two robustness bugs found while validating the noisy track: JPEG/downscale color
  drift (relied on labels instead of loosening color tolerance) and object-region bbox
  inflation from scattered noise blobs (fixed by using only the largest connected gray
  component)

Verified:

- 56 tests pass (54 prior + 2 new label tests)
- arrow-v1 controlled (14 cases): typed hits `7/7`, ambiguous guard `2/2`, false unsupported
  passes `0`, golden failures `0`
- arrow-v1-noisy (6 cases): typed hits `4/4`, false unsupported passes `0`, golden failures
  `0`, verdict mismatches `0`
- chart-v2 controlled metrics re-verified unchanged

Bounds: label catalog is a small fixed alphabet (8 entries), noisy track covers only mild
blur/downscale/JPEG, object detection still assumes a single connected gray blob. No
theory-aware physics rules, no real-world arrow images, no geometry vertical yet.

### 2026-07-10 session 11 - COMPLETE

Implemented arrow-v1, the second executable vertical (physics free-body diagrams), proving the
Spec -> ClaimGraph -> EvidenceGraph -> Rules architecture generalizes beyond charts.

Delivered:

- deterministic free-body renderer, spec-blind color-component arrow extractor
- arrow ClaimGraph generation with the same unsupported-check gap guardrails
- count/presence/direction/anchor rules with rule_id and coordinate evidence
- `datasets/physics/arrow-v1` (4 golden, 6 typed mutated, 2 ambiguous)
- `specs/arrow-evidence-graph.schema.json`, arrow service entrypoints, CLI commands
  `generate-arrow-dataset`, `verify-arrow`, `run-arrow-validation`

Verified:

- 54 tests pass (43 prior + 11 arrow)
- arrow typed hits `6/6`, ambiguous guard `2/2`, false unsupported passes `0`, golden
  non-passes `0`
- chart-v2 controlled metrics re-verified unchanged (`9/9`, guard `1.0`, `0`/`0`)

Bounds: synthetic single-box free-body diagrams with color-declared arrow identity only; no
label reading, noisy track, real-world arrow images, or theory-aware physics rules yet.

### 2026-07-10 session 10 - COMPLETE

Completed the configured noisy-hardening gate and added a separate hybrid real-world pilot without
widening the general readiness claim.

Delivered:

- signed-safe color arithmetic, component-based bar segmentation, peak/coverage plot detection
- calibrated tick-template candidates plus a visual-only sequence decoder
- tolerant multi-font/category label matching and explicit axis-range validation
- 24-case `chart-v2-realworld-pilot` with provenance and frozen checksums
- pilot extraction metrics and combined chart-suite validation CLI

Verified:

- 43 tests pass, including adversarial ambiguity, missing-gridline, irregular-spacing, and manifest-completeness coverage
- controlled typed hits `9/9`; noisy typed hits `2/2`; all controlled/noisy golden cases pass
- pilot typed hits `6/7` (`0.86`), ambiguous guard `7/7`, false unsupported passes `0`
- pilot bar/tick/label accuracy `1.00/0.94/0.95`; manifest valid `24/24`

The result is evidence for the configured renderer/transform/reference-backed families only.

### 2026-07-10 session 9 - COMPLETE

Operationalized chart-v2 for Phase 2 by adding an MCP wrapper, audit schema upgrades, noisy validation, and a separate OCR gate.

Delivered:

- `pyproject.toml` with explicit runtime/dependency metadata and stable MCP SDK pinning
- thin MCP stdio wrapper for `build_claim_graph`, `parse_chart`, `run_rules`, and `verify_chart`
- `rule_id`, provenance, and separated extraction/rule confidence fields in runtime artifacts
- CLI support for `serve-mcp`, `run-rules`, `generate-noisy-dataset`, `run-phase2-validation`, and `run-ocr-validation`
- `datasets/charts/chart-v2-noisy/` as a separate noisy robustness gate
- OCR environment capture and separate OCR validation summary path
- new tests for MCP tools and Phase 2 validation flows

Verified:

- `pytest mcp-server/tests -q` passes with 33 tests
- `python -m visual_qa_mcp.cli run-validation --dataset datasets/charts/chart-v2` preserves the controlled chart-v2 bounded metrics
- `python -m visual_qa_mcp.cli run-phase2-validation --controlled-dataset datasets/charts/chart-v2 --noisy-dataset datasets/charts/chart-v2-noisy` surfaces noisy-track weaknesses separately from the readiness baseline
- `python -m visual_qa_mcp.cli run-ocr-validation --controlled-dataset datasets/charts/chart-v2 --noisy-dataset datasets/charts/chart-v2-noisy` confirms OCR remains unavailable and safely degrades to `needs_review`

### 2026-07-10 session 8 - COMPLETE

Prepared chart-v2 as a callable local tool surface so the current bounded verifier can be wrapped by an MCP server later without changing readiness claims.

Delivered:

- reusable service-layer chart-v2 entrypoints for claim generation, evidence extraction, full verification, and artifact writing
- `ArtifactPaths` / `VerificationResult` contracts for shared callable execution
- validation refactor so dataset `run_case()` delegates to the service layer
- optional metadata handling for callable use with safe local defaults only
- CLI support for `build-claim-graph`, `extract-chart-evidence`, and `verify-chart`
- docs updates that describe the current state as MCP-ready callable tooling, not yet a full MCP server process
- new tests for pure verification, artifact writing, delegation, CLI output, metadata-optional execution, and OCR degradation

Verified:

- `pytest mcp-server/tests -q` passes with 29 tests
- `python -m visual_qa_mcp.cli run-validation --dataset datasets/charts/chart-v2` preserves current chart-v2 metrics and bounded readiness claims

### 2026-07-09 session 7 - COMPLETE

Hardened chart-v2 `ClaimGraph` handling so unsupported spec checks are surfaced explicitly and cannot silently turn into unsupported passes.

Delivered:

- `ClaimGraph` gaps for unsupported or unmapped chart-v2 spec checks
- rule-runner integration that merges claim-generation gaps into `checks_skipped`
- runtime validation of `claim_graph.json` before writing or referencing it
- `claim_graph_path` in `VisualQaReport` / findings schema so the claim artifact is part of the formal audit trail
- new tests for unknown checks, mistyped known checks, and invalid runtime claim graphs

Verified:

- `pytest mcp-server/tests -q` passes with 23 tests
- `python -m visual_qa_mcp.cli run-validation --dataset datasets/charts/chart-v2` preserves current chart-v2 metrics and bounded readiness claims

### 2026-07-09 session 6 - COMPLETE

Implemented chart-v2 `ClaimGraph` contracts so rule execution is now spec-driven through explicit claim generation.

Delivered:

- `specs/claim-graph.schema.json` for chart-v2 claim artifacts
- `mcp-server/src/visual_qa_mcp/claim_graph.py` to generate chart-v2 claims from `VisualSpec`
- chart rule integration so validators consume `ClaimGraph` rather than ad hoc spec parsing
- `claim_graph.json` artifacts emitted alongside evidence, overlay, and report outputs
- tests and workflow docs updated for the new claim contract

Verified:

- `pytest mcp-server/tests -q` passes with 20 tests
- `python -m visual_qa_mcp.cli run-validation --dataset datasets/charts/chart-v2` preserves current chart-v2 metrics and bounded readiness claims

### 2026-07-09 session 5 - COMPLETE

Implemented chart-v2 axis-scale extraction and upgraded the chart verifier from metadata-derived values to image-derived scale mapping.

Delivered:

- chart-v2 extractor pipeline with tick detection, monotonic scale inference, non-zero minimum support, and signed-axis support
- template backend plus optional OCR backend scaffold
- `specs/evidence-graph.schema.json` update for chart-v2 contracts
- `datasets/charts/chart-v2/` with 8 golden and 16 mutated cases
- expanded tests with 18 passing checks
- refreshed advisor evidence packs for chart-v2 readiness review
- updated agent memory and workflow docs so future sessions start from the chart-v2 bounded-claim baseline

Verified:

- `pytest mcp-server/tests -q` passes with 18 tests
- chart-v2 validation summary meets current controlled-to-semi-realistic targets on the configured template backend
- unsupported `pass` outcomes are zero in the current 24-case set

### 2026-07-09 session 4 - COMPLETE

Implemented the first executable chart-only MVP loop and validation set.

Delivered:

- `mcp-server/src/visual_qa_mcp/` - chart extractor, rule runner, overlay, CLI, validation, and advisor artifacts helpers.
- `specs/evidence-graph.schema.json` - chart evidence contract.
- `docs/chart-mvp-workflow.md` - operational workflow with advisor gates.
- `datasets/charts/chart-v1/` - 4 golden and 8 mutated chart cases.
- `outputs/advisor/` - gate evidence, validation summary, and reconciled Gate 3 review.
- `mcp-server/tests/` - schema, rule, and end-to-end tests.

Verified:

- `pytest mcp-server/tests -q` passes with 14 tests.
- Validation summary meets the controlled-MVP targets for the synthetic chart set.

### 2026-07-09 session 3 - COMPLETE

Captured research direction, no-fine-tuning strategy, validator architecture, and 3D roadmap in the wiki.

Delivered:

- `wiki/knowledge-product-direction.md` - product framing and research ideas.
- `wiki/knowledge-rules-validators.md` - rule and validator architecture concept.
- `wiki/knowledge-no-tuning-and-3d.md` - no-fine-tuning strategy and 3D roadmap.
- `AGENTS.md` and `CLAUDE.md` updates for future agent session context.

### 2026-07-09 session 2 - COMPLETE

Reframed the project direction toward high-assurance, theory-aligned visual verification.

Delivered:

- `docs/high-assurance-roadmap.md` - roadmap for medical/anatomy, chemistry/biology, and CAD target tracks.
- README/product/MVP/problem-map updates to clarify that high-risk domains are long-term goals.
- Agent guidance updates so future sessions preserve the stronger reliability framing.

### 2026-07-09 session 1 - COMPLETE

Created the initial Visual QA MCP project scaffold and agent guidance files.

Delivered:

- `README.md` - project overview and design principle.
- `docs/problem-map.md` - taxonomy of educational visual errors.
- `docs/mvp-scope.md` - first MVP scope for charts, arrows, and geometry.
- `docs/validation-plan.md` - validation dataset and metrics plan.
- `specs/visual-spec.schema.json` - schema for expected visual structure.
- `specs/findings.schema.json` - schema for QA reports.
- `skills/educational-visual-qa/SKILL.md` - draft agent skill workflow.
- `CLAUDE.md` and `AGENTS.md` - guidance for future agents.
- `wiki/` - project memory scaffold.

Verified:

- All JSON files parse successfully with PowerShell `ConvertFrom-Json`.
- Project files were listed after creation.

## Suggested Next Work

1. Add a separate noisy geometry track, including blur/downscale/JPEG, low contrast, and label
   degradation; do not widen the controlled readiness claim before that gate passes.
2. Reduce end-to-end test runtime by sharing immutable generated fixtures and separating generator
   tests from verifier regression tests.
3. Add independently authored or publisher-sourced open-license chart images; the current pilot images
   are still locally rendered and should not be treated as general real-world coverage.
   Install and validate the optional OCR backend in a configured environment so OCR gets its own
   evidence-backed readiness gate.
4. Extend force-balance beyond v1 when justified: a noisy-track equilibrium case, non-zero
   declared expected resultants, and (much later) torque/moment balance with points of
   application.

## Recent Completed Milestones

- 2026-07-09: Project scaffold and agent memory files created.
- 2026-07-09: High-assurance domain roadmap added.
- 2026-07-09: Research direction, validator architecture, no-tuning strategy, and 3D roadmap captured.
- 2026-07-09: First executable chart-only MVP implemented with advisor review and validation artifacts.
- 2026-07-09: Chart-v2 axis-scale extraction implemented with dual backend scaffolding and 24-case validation set.
- 2026-07-09: Chart-v2 ClaimGraph contract added so rule execution is spec-driven end to end.
- 2026-07-09: Chart-v2 ClaimGraph hardening added unsupported-check guardrails and formal claim audit artifacts.
- 2026-07-10: Chart-v2 callable tool surface added for MCP-ready local verification without expanding current readiness claims.
- 2026-07-10: Phase 2 MCP wrapper, audit schema upgrades, noisy dataset gate, and OCR validation gate added.
- 2026-07-10: Arrow-v1 free-body verifier added as the second executable vertical with a 12-case controlled dataset.
- 2026-07-10: Arrow-v1 label-based identity and noisy track added (14-case controlled, 6-case noisy, 7/7 and 4/4 typed hits).
- 2026-07-10: Arrow-v1 translational force-balance rule added (first theory-aware check; 17-case controlled set, 8/8 typed hits, force-balance 1/1).
