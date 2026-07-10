---
name: project-log
description: Chronological record of completed sessions
metadata:
  type: reference
  status: current
  last_updated: 2026-07-11
---

# Project Log

## 2026-07-11 session 16 - Coordinate-graph-v1 dual-axis verifier (fourth vertical)

- Implemented `coordinate-graph-v1`, following the fourth-vertical plan: scatter points
  (color-identified) plus one connected polyline on a coordinate plane with independent numeric
  X and Y axes. The advisor-flagged new capability (dual-axis mapping, versus chart-v2's single
  Y-axis) was the implementation's central risk.
- Added `coordinate_generator.py` (deterministic Pillow renderer: independent X/Y tick axes,
  colored scatter points, one polyline), `coordinate_extractor.py` (spec-blind dual-axis tick
  reader, point color-component extraction, per-pair polyline edge coverage), `coordinate_rules.py`
  (`run_coordinate_claims`: count/presence/position/polyline/axis-scale checks with color-match +
  collision-guard, mirroring `arrow_rules._match_arrows_by_color`), and `build_coordinate_claim_graph`
  in `claim_graph.py` with the same unsupported-check gap guardrail as the other three verticals.
- The dual-axis tick reader reuses `tick_reader.rank_numeric_text_templates` (the numeric glyph
  matcher) but implements its own local sequence-fit search (`_fit_axis_sequence`) rather than
  calling `tick_reader.read_tick_texts`/`_decode_tick_sequence_result` directly, because that
  function is hard-coded to a decreasing Y-axis (position increases -> value decreases) and the
  X-axis needs the opposite monotonicity. This kept the validated chart-v2 tick reader completely
  unmodified.
- Added `specs/coordinate-evidence-graph.schema.json`, coordinate service entrypoints
  (`run_coordinate_verification`), CLI commands `generate-coordinate-dataset`,
  `verify-coordinate`, `run-coordinate-validation`, three new MCP tools
  (`build_coordinate_claim_graph`, `parse_coordinate`, `verify_coordinate`), and
  `primitive_graph_from_coordinates` (points -> `point` primitives, axes -> `line` primitives,
  detected polyline edges -> `connected_to` relationships) registered as the `coordinate-graph-v1`
  profile in `SUPPORTED_PRIMITIVE_PROFILES`.
- Added `datasets/coordinate/coordinate-graph-v1/` with 11 cases (4 golden, 7 mutated: 5 typed +
  2 ambiguous), including `golden-03`, a signed-axis case with deliberately mismatched X/Y pixel
  scale (X: 2.8 px/unit, Y: 4.2 px/unit) designed so a naive single-axis or identity-mapped
  extractor would silently produce a wrong-but-plausible point position.
- Measured pixel->data round-trip extraction error *before* setting any position tolerance (per
  the project's no-guessed-tolerance discipline), across zero-baseline, non-zero-minimum, and
  signed axis configurations with X-scale != Y-scale. Set position tolerance to 3% of each axis's
  declared range, well above the measured margin.
- Found and fixed a real extraction bug during that measurement pass: the Y-axis's minimum-value
  tick sits at the same pixel row as the X-axis line (the two axes meet at the plot's bottom-left
  corner), so its label-text crop box vertically overlapped the row scanned for X-axis tick
  marks — and symmetrically for the X-axis's minimum-value tick against the Y-tick-mark scan
  column. This injected phantom tick candidates that corrupted the linear fit on one golden case
  (a false `axis_scale_misread`). Fixed by bounding each tick-mark search to the correct side of
  the opposite axis line in `coordinate_extractor._tick_positions`.
- Also fixed a verdict-interaction bug found while writing tests: the polyline check originally
  skipped the *entire* check (forcing `needs_review` via `checks_skipped`) if any declared point
  was unresolved, which would have wrongly overridden a plain `missing_point` case's correct
  `fail` verdict. Changed to a per-edge `continue`, mirroring arrow-v1's per-arrow skip pattern in
  the direction/anchor checks.

Verification:

- coordinate-graph-v1 controlled (11 cases): typed hits `5/5`, ambiguous guard `2/2`, point-count
  evidence `11/11`, false unsupported passes `0`, golden failures `0`, golden non-passes `0`,
  verdict mismatches `0`.
- Full test suite: 106 passing (85 prior + 21 new: 20 in `test_coordinate_graph_v1.py` plus one
  new MCP `verify_coordinate` schema-validity test).
- chart-v2, arrow-v1, and geometry-v1 controlled metrics re-verified unchanged: chart `9/9`
  (guard `1.0`), arrow `8/8` (guard `1.0`), geometry `7/7` (guard `1.0`), all `0` unsupported
  passes and `0` golden failures.
- Environment note (not a code change): the local matplotlib install was binary-incompatible
  with the installed numpy 2.x (pre-existing, unrelated to this session's code), which blocked
  the chart-v2 realworld-pilot test fixture. Reinstalling matplotlib fixed it; pillow was then
  re-pinned to the project's declared `<12` constraint since the matplotlib reinstall had pulled
  in a newer, non-conforming pillow.

Bounds: controlled Pillow renders only; single connected polyline (no multi-series, no curve
fitting, no general topology/connectivity checks); tick value catalog restricted to multiples of
5 in [-150, 150] (reuses chart-v2's numeric templates); no noisy-image robustness track or
independently authored/real-world images yet; point identity is color-only (no label reading).

## 2026-07-10 session 15 - Basic-to-complex primitive evidence foundation

- Added strict `PrimitiveEvidenceGraph` v1 with type-discriminated point/line/polyline/arrow/circle/
  region geometry, deterministic IDs, relationships, source references, semantic validation, and
  explicit spec-blind profiles for chart, arrow, and geometry.
- Added additive primitive links to domain evidence, `primitive_evidence_graph.json` verification
  artifacts, `extract-primitives` CLI, and `parse_primitives` MCP tool. Domain rules remain unchanged.
- Added the checksum-frozen 20-case `geometry-v1-noisy` track: two golden, one typed defect, and one
  ambiguity case for each of blur, downscale, JPEG, low contrast, and label degradation.
- Replaced per-pixel component flood fill with deterministic run-length union-find and cached font/
  text templates. Validation summaries no longer write into immutable dataset fixtures.
- Advisor gates froze the schema as an additive audit layer and required standalone chart primitives
  to remain spec-blind.

Verification:

- Geometry noisy: golden `10/10`, typed `5/5`, ambiguity `5/5`, false unsupported passes `0`,
  verdict mismatches `0`, manifest valid `20/20`.
- Controlled baselines unchanged: chart `9/9`, arrow `8/8`, geometry `7/7`; chart noisy `2/2`,
  arrow noisy `4/4`; chart pilot remains `6/7` typed hits.
- Unified suite: `85/85` passing in about 63 seconds. Chart end-to-end: `16/16` in about 35 seconds
  versus about 4m19s before the performance refactor.

Cross-graph validation enforces that domain links resolve for chart bars/axis/ticks, arrow regions/
arrows, and geometry plates/holes; a typed geometry finding traces through detected domain evidence
to its primitive support.

Bounds: primitive evidence is audit-only in this milestone; no coordinate-graph, flowchart, circuit,
general OCR, independently authored geometry, native CAD, or teaching-intent readiness claim.

## 2026-07-10 session 14 - Geometry-v1 controlled mechanical plate verifier

- Recovered the five partially authored `geometry_*` modules and completed their runtime seams:
  evidence schema, validation discovery/metrics, CLI commands, MCP tools, package exports, and tests.
- Froze the v1 claim boundary to one controlled rectangular plate with circular holes, relative
  diameter ratios, opt-in linear alignment/spacing, ordered hole pairing, and a six-item dimension
  label catalog. No pixel-to-unit calibration or general OCR was introduced.
- Added `datasets/mechanical/geometry-v1` with 14 cases (5 golden, 9 mutated). Seven mutations have
  typed findings; two prove merged-hole and unreadable-label ambiguity guards.
- Added setuptools src-layout discovery and `visual-qa` console entrypoint; editable installation and
  `visual-qa --help` were verified locally.
- Expanded the MCP wrapper from four chart-only tools to ten tools by adding claim, parse, and verify
  surfaces for arrow-v1 and geometry-v1.

Verification:

- Geometry validation: typed `7/7`, ambiguity `2/2`, hole-count `13/13`, unsupported passes `0`,
  golden non-passes `0`, verdict mismatches `0`.
- Test groups: geometry/MCP/schema `15/15`, chart rules/extractor/tick `21/21`, chart end-to-end
  `16/16`, and arrow `18/18` (70 total). The chart end-to-end group takes about 4m19s; runtime is a
  known test-fixture architecture issue, not a failing assertion.

Readiness remains bounded to controlled generated images. No noisy or independently sourced
geometry evidence exists yet.

## 2026-07-10 session 13 - Arrow-v1 translational force-balance rule (first theory-aware check)

- Ran the deferred advisor gate on the force-balance design questions from sessions 11/12.
  Decisions: magnitude comes from the extractor's existing pixel vectors (`length_px` +
  `angle_degrees`) summed directly — spec-declared magnitudes rejected (would verify the
  spec's own arithmetic, not the image) and px-to-newton calibration deferred (new error
  source with no benefit for a zero-sum check). Equilibrium is opt-in via
  `source_reference.scenario_type = "equilibrium"` plus a `force-balance-correct` check;
  scope is translational balance only (not torque), and the finding type is named
  `force_balance_violation` to avoid overclaiming full static equilibrium.
- Implemented the check across the existing seams with no new extraction machinery:
  - `claim_graph.build_arrow_claim_graph`: new dispatch branch; scenario-without-check and
    check-without-scenario both become `ClaimGraph` gaps -> needs_review.
  - `arrow_rules.run_arrow_claims`: fifth rule block; reuses `_match_arrows_by_color`;
    refuses to sum a partial force set (any unmatched expected arrow -> explicit skip);
    defect criterion is `|resultant| / max(length_px) > resultant_ratio_tolerance` (0.15).
  - `arrow_extractor`: `force-balance-correct` added to `ARROW_CHECK_IDS` and the
    `ambiguous_arrow_colors` gap so extraction ambiguity also gates the new check.
  - `validation.summarize_arrow_validation_results`: new `force_balance_metrics` block.
- Grew `datasets/physics/arrow-v1` to 17 cases: `golden-06` (declared equilibrium,
  balanced), `mutated-10` (weight arrow shortened to 50 px — the first defect class
  invisible to all four prior rules: direction, anchor, count, and presence all still pass),
  and `mutated-11` (unlabeled color collision under a declared equilibrium -> needs_review).
- Measured margins rather than assuming `length_px` reliability: golden resultant ratio sits
  well under the 0.15 tolerance despite ~1.3 deg extraction angle error per arrow, while the
  shortened-arrow case produces ~0.44. No thresholds were tuned per-case.

Verification:

- `pytest mcp-server/tests -q`: 61 passing tests (56 prior + 5 new force-balance tests).
- Arrow-v1 controlled (regenerated, 17 cases): typed hits `8/8`, ambiguous guard `3/3`,
  force-balance typed hits `1/1`, false unsupported passes `0`, golden failures `0`,
  verdict mismatches `0`.
- Arrow-v1-noisy (6 cases): unchanged `4/4` typed hits, `0` false unsupported passes. Noisy
  specs do not declare `scenario_type`, so the balance check does not run there (scope
  boundary, not a gap).
- Chart-v2 controlled re-verified unchanged: `9/9` typed hits, guard `1.0`, `0`/`0`.

Bounds: translational force balance only, opt-in per spec, controlled renders only. Deferred:
px-to-newton magnitude calibration, torque/moment balance, non-zero expected resultants.

## 2026-07-10 session 12 - Arrow-v1 label identity and noisy track

- Added `arrow_labels.py`: a template-matched fixed label catalog (`W,N,F,f,T,P,Fx,Fy`) used as
  a second, noise-robust identity signal alongside color, following the same template-matching
  pattern as chart-v2's tick reader.
- Fixed two label-placement bugs found via empirical debugging: label crop box must be computed
  from the tail/head midpoint (not the tail, which sits on the object edge and caused overlap),
  and the glyph foreground mask must be achromatic-only (plain grayscale threshold also caught
  saturated arrow colors).
- Fixed a tail/head extremity bias in `arrow_extractor._analyze_component`: the endpoint was a
  windowed average biased ~9px inward, invisible to direction/anchor checks but large enough to
  misalign the new label crop; changed to the true geometric extremity.
- Wired label matching into `arrow_rules._match_arrows_by_color` as a first pass before color
  distance, and suppressed the extractor's `ambiguous_arrow_colors` gap when colliding-color
  arrows have distinct decoded labels. Added dataset case `mutated-09` proving this: a real
  direction defect on a color-colliding arrow now resolves to `arrow_direction_wrong` instead of
  `needs_review`.
- Added `datasets/physics/arrow-v1-noisy/` (6 cases) with blur/downscale/JPEG postprocessing.
  First-pass validation exposed two real robustness gaps, both root-caused and fixed:
  1. JPEG/downscale color drift (~74 RGB units) exceeded the color-match tolerance; rejected
     raising the tolerance as unsafe (closest canonical color pair is only 81 apart) and instead
     relied on the noise-robust label signal.
  2. Blur scattered small gray noise blobs that inflated the object region's bbox via a naive
     global min/max over all matching pixels, causing a false unsupported pass on a deliberately
     detached arrow. Fixed by using the largest connected component of the gray mask only.
- Advisor scope-freeze gate (before starting): flagged that a planned force-balance/theory check
  needs a magnitude source decision (spec-declared vs. length-calibrated) and an equilibrium
  gate field before any code is written; deferred that work and resequenced label+noisy work
  first as the lower-risk item.

Verification:

- `pytest mcp-server/tests -q`: 56 passing tests (54 prior + 2 new label-specific tests).
- Arrow-v1 controlled (regenerated, 14 cases): typed hits `7/7`, ambiguous guard `2/2`, false
  unsupported passes `0`, golden failures `0`.
- Arrow-v1-noisy (6 cases): typed hits `4/4`, false unsupported passes `0`, golden failures `0`,
  verdict mismatches `0`.
- Chart-v2 controlled and arrow-v1 controlled metrics re-verified unchanged after the
  extractor fix.

Readiness remains bounded: label catalog is a small fixed alphabet, noisy track covers only
mild blur/downscale/JPEG, and object detection still assumes one connected gray blob.

## 2026-07-10 session 11 - Arrow-v1 free-body prototype (second vertical)

- Reviewed the roadmap against the all-around learning-verification target and confirmed the
  next step per `docs/high-assurance-roadmap.md` strategy step 1: prove the loop beyond charts.
- Implemented `arrow-v1`, the first physics vertical: controlled free-body diagrams with
  color-identified force arrows.
- Added `arrow_generator.py` (deterministic Pillow renderer: gray object box + shaft/head
  arrows), `arrow_extractor.py` (spec-blind color-component extractor with principal-axis
  head/tail analysis), `build_arrow_claim_graph` in `claim_graph.py`, and `arrow_rules.py`
  (count, presence, direction, anchor rules with rule_id + coordinate evidence).
- Added `ArrowEvidenceGraph` contracts, `specs/arrow-evidence-graph.schema.json`, arrow service
  entrypoints (`run_arrow_verification`), and CLI commands `generate-arrow-dataset`,
  `verify-arrow`, `run-arrow-validation`.
- Added `datasets/physics/arrow-v1/` with 12 cases (4 golden, 6 typed mutated, 2 ambiguous)
  and arrow validation summaries mirroring the chart metric discipline.
- Reused the shared service layer, artifact writer, overlay, verdict/confidence helpers, and
  claim-gap guardrails unchanged — evidence that the architecture generalizes across domains.

Verification:

- `pytest mcp-server/tests -q`: 54 passing tests (43 prior + 11 new arrow tests).
- Arrow validation: typed hits `6/6`, ambiguous guard `2/2`, false unsupported passes `0`,
  golden non-passes `0`, verdict mismatches `0`, arrow-count evidence `11/11`.
- Chart-v2 controlled validation re-run and unchanged: `9/9` typed hits, guard `1.0`,
  `0` false unsupported passes, `0` golden failures.

Readiness remains bounded: arrow-v1 covers only synthetic single-box free-body diagrams with
color-declared arrow identity. No label reading, noisy track, real-world images, or
theory-aware physics rules yet.

## 2026-07-10 session 10 - Noisy hardening and real-world pilot

- Fixed `uint8` overflow in blue-bar channel comparisons and hardened bar segmentation with
  vertical-run, width, and row-coverage evidence.
- Hardened plot/tick-row detection by selecting peak rows and rejecting insufficient line coverage.
- Recalibrated template tick confidence and added a visual-only sequence decoder that handles
  missing ticks and jitter without using expected spec values to rewrite visual evidence.
- Added explicit axis-range checking so clearly read shifted scales are reported rather than relying
  on extractor mistakes to surface a defect.
- Added multi-font and vertically tolerant category/axis label matching while preserving unresolved
  evidence as `needs_review`.
- Generalized chart source records to support `category` / `value` while retaining legacy fixture
  compatibility.
- Added `chart-v2-realworld-pilot` with 24 cases, frozen checksums, Pillow/Matplotlib rendering,
  and World Bank CC BY 4.0 reference-backed population snapshots.
- Added pilot evidence metrics, manifest verification, `generate-realworld-pilot`, and
  `run-chart-suite-validation` CLI commands.
- Closed advisor blockers by preventing ambiguous sequence fallback, carrying missing-gridline
  support through linear axis mapping, and validating manifest completeness/uniqueness/provenance.

Verification:

- `pytest mcp-server/tests -q`: 43 passing tests.
- Controlled: typed hits `9/9`, golden non-passes `0`, false unsupported passes `0`.
- Noisy: typed hits `2/2`, golden non-passes `0`, verdict mismatches `0`, ambiguous guard `2/2`.
- Pilot: typed hits `6/7` (`0.86`), ambiguous guard `7/7`, false unsupported passes `0`, golden non-passes `0`.
- Pilot extraction: bar count `24/24` (`1.00`), readable tick sequences `16/17` (`0.94`),
  readable labels `19/20` (`0.95`).
- Pilot manifest: 24 cases, all frozen checksums valid.

Readiness remains bounded: the pilot uses locally rendered assets and one frozen public-data source;
it is not evidence of general publisher/style coverage or OCR readiness. The unmatched typed pilot
case safely returns `needs_review` because its shifted-scale sequence remains ambiguous.

## 2026-07-10 session 9 - Phase 2 operationalization and evidence expansion

- Added `pyproject.toml` with explicit Python and dependency metadata, including a stable MCP SDK pin (`mcp>=1.27,<2`) for the repo rather than relying on the global environment.
- Implemented a thin MCP stdio server wrapper in `mcp-server/src/visual_qa_mcp/server.py` that exposes `build_claim_graph`, `parse_chart`, `run_rules`, and `verify_chart` over the existing callable chart-v2 service layer.
- Added audit-oriented contract upgrades:
  - stable `rule_id` values in `ClaimGraph` claims and `VisualQaReport` findings
  - explicit `provenance` in `EvidenceGraph`
  - separate `extraction_confidence` and `rule_confidence` in reports
- Extended the CLI with `serve-mcp`, `run-rules`, `generate-noisy-dataset`, `run-phase2-validation`, and `run-ocr-validation`.
- Added a separate noisy chart-v2 dataset generator and Phase 2 validation summaries for controlled versus noisy tracks.
- Added OCR environment capture and separate OCR validation summaries without expanding OCR readiness claims.
- Added MCP server tests plus validation tests for noisy and OCR gate summaries.

Verification:

- Ran `pytest mcp-server/tests -q` successfully with 33 passing tests.
- Ran `python -m visual_qa_mcp.cli run-validation --dataset datasets/charts/chart-v2` and confirmed the controlled template-backed metrics remained unchanged:
  - `critical_error_recall = 1.0`
  - `typed_mutated_cases = 9`
  - `typed_mutated_hits = 9`
  - `ambiguous_guard_rate = 1.0`
  - `false_unsupported_passes = 0`
  - `golden_failures = 0`
- Generated `datasets/charts/chart-v2-noisy/` and ran `run-phase2-validation`.
- Confirmed the noisy track currently exposes unresolved robustness limits:
  - `golden_non_passes = 2`
  - `verdict_mismatches = 4`
  - `typed_mutated_cases = 2`
  - `typed_mutated_hits = 0`
- Ran `run-ocr-validation` and confirmed OCR is still unavailable in this environment and correctly degrades to `needs_review`.

## 2026-07-10 session 8 - Chart v2 callable tool surface

- Split chart-v2 verification into a reusable service layer with `build_claim_graph_from_spec`, `extract_chart_evidence_from_inputs`, `run_chart_verification`, and `write_verification_artifacts`.
- Added `ArtifactPaths` and `VerificationResult` contracts so claim, evidence, report, and persisted artifacts can move through one shared callable path.
- Refactored validation so `run_case()` now delegates to the service layer and artifact writer instead of recomputing and writing outputs inline.
- Made chart evidence extraction accept optional metadata input, using only safe local defaults when metadata is absent.
- Extended the CLI with `build-claim-graph`, `extract-chart-evidence`, and `verify-chart` so the local callable surface can be exercised directly outside dataset validation.
- Updated README, MCP notes, and chart workflow docs to describe the current state as a callable chart-v2 surface that is ready for a future MCP wrapper, not yet a full MCP server process.
- Added tests for pure service verification, artifact writing, validation delegation, CLI JSON output, metadata-optional execution, and optional OCR degradation.

Verification:

- Ran `pytest mcp-server/tests -q` successfully with 29 passing tests.
- Ran `python -m visual_qa_mcp.cli run-validation --dataset datasets/charts/chart-v2`.
- Confirmed the bounded chart-v2 validation summary remained unchanged:
  - `critical_error_recall = 1.0`
  - `typed_mutated_cases = 9`
  - `typed_mutated_hits = 9`
  - `ambiguous_guard_rate = 1.0`
  - `false_unsupported_passes = 0`
  - `golden_failures = 0`

## 2026-07-09 session 7 - Chart v2 ClaimGraph hardening

- Added structured `ClaimGraph` gaps so every chart-v2 spec check is either mapped to a claim or recorded as unsupported with a machine-readable reason.
- Updated chart rule execution to merge claim-generation gaps into `checks_skipped`, forcing unsupported or mistyped checks to end in `needs_review` rather than disappearing silently.
- Promoted `claim_graph.json` to a formal audit artifact by validating it in the runtime path and adding `claim_graph_path` to `VisualQaReport`.
- Extended schemas and contracts so report outputs now reference claim artifacts alongside evidence artifacts.
- Added tests for unknown checks, mistyped known checks, end-to-end `claim_graph_path` emission, and invalid runtime claim-graph rejection.
- Updated workflow and implementation docs to reflect the unsupported-check guardrail policy.

Verification:

- Ran `pytest mcp-server/tests -q` successfully with 23 passing tests.
- Ran `python -m visual_qa_mcp.cli run-validation --dataset datasets/charts/chart-v2`.
- Confirmed the bounded chart-v2 validation summary remained unchanged:
  - `critical_error_recall = 1.0`
  - `typed_mutated_cases = 9`
  - `typed_mutated_hits = 9`
  - `ambiguous_guard_rate = 1.0`
  - `false_unsupported_passes = 0`
  - `golden_failures = 0`

## 2026-07-09 session 6 - Chart v2 ClaimGraph integration

- Added `specs/claim-graph.schema.json` as the first explicit claim contract for chart-v2.
- Added `mcp-server/src/visual_qa_mcp/claim_graph.py` to translate `VisualSpec` into per-check claims with expected values, tolerances, and evidence requirements.
- Refactored chart rule execution so validators consume `ClaimGraph` instead of re-parsing chart spec details inline.
- Updated validation runs to emit `claim_graph.json` artifacts beside `evidence_graph.json`, `report.json`, and `overlay.png`.
- Added schema and rule tests for the claim-generation path and updated end-to-end coverage.
- Updated README, chart workflow docs, MCP server notes, and wiki implementation memory to reflect the spec -> claim -> evidence -> rules flow.

Verification:

- Ran `pytest mcp-server/tests -q` successfully with 20 passing tests.
- Ran `python -m visual_qa_mcp.cli run-validation --dataset datasets/charts/chart-v2`.
- Confirmed the bounded chart-v2 validation summary remained unchanged:
  - `critical_error_recall = 1.0`
  - `typed_mutated_cases = 9`
  - `typed_mutated_hits = 9`
  - `ambiguous_guard_rate = 1.0`
  - `false_unsupported_passes = 0`
  - `golden_failures = 0`

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
