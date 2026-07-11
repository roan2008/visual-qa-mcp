---
name: project-log
description: Chronological record of completed sessions
metadata:
  type: reference
  status: current
  last_updated: 2026-07-11
---

# Project Log

## 2026-07-11 session 22 - Chart-v2 round-trip re-rendering accuracy check

- Prior discussion this session produced `wiki/knowledge-accuracy-and-synthetic-data-roadmap.md`,
  an honest assessment that all five verticals' near-100% recall claims are measured almost
  entirely on self-rendered datasets. Round-trip re-rendering (analysis-by-synthesis) was the
  roadmap's highest-priority idea for closing that gap without external data. Chosen over
  circuit-v1 (new vertical, larger surface) and real-world image/OCR sourcing (blocked on
  external inputs) via an advisor-gated plan-mode session, then implemented against the
  approved plan.
- Key design decision: a naive round-trip (re-render from extracted values using the
  extractor's own inferred axis mapping, then re-extract and compare values) is circular and
  would trivially match itself. The implemented version instead compares (a) the bar pixel
  geometry the extractor directly measured on the original image (already stored unmodified
  in `EvidenceGraph.bars[i].bbox`) against (b) freshly measured bar pixel geometry on a freshly
  rendered image built from the extracted values + inferred axis config — isolating
  self-consistency bugs in axis-mapping/generator math without being tautological. Does not
  catch OCR tick misreads (accepted, documented bound).
- Delivered: `chart_round_trip.py` (new module: `measure_bar_geometry`,
  `build_round_trip_inputs`, `render_round_trip_image`, `compare_bar_geometry`,
  `run_round_trip_check` — never raises), `RoundTripComparison`/`BarGeometryDelta` dataclasses
  and an optional `round_trip` field on `VerificationResult` (contracts.py, additive
  omit-if-None pattern matching `primitive_graph`), an `include_round_trip` flag on
  `run_chart_verification` (round-trip runs strictly after `report` is finalized, so it cannot
  influence `verdict`), opt-in artifact persistence (`persist_round_trip`, default off, so no
  existing dataset directory gains new files by default), `summarize_chart_round_trip_results`
  in `validation.py`, and the `run-chart-round-trip-validation` CLI subcommand.
- Verified: 150 tests pass (141 prior + 9 new in `test_chart_round_trip.py`), including a
  regression test proving `report.to_dict()` is byte-identical whether `include_round_trip` is
  `True` or `False`. Ran the new CLI read-only against all three existing chart-v2 datasets
  with zero exceptions and zero dataset file mutations (`git status --porcelain` clean
  throughout, including the checksum-frozen `chart-v2-realworld-pilot`).
- Measured (not yet acted on): median round-trip pixel delta is 0-1px across all three
  datasets; 25-33% of cases per dataset are skipped (`skipped_no_axis_mapping`, expected where
  the extractor never committed to a mapping); a handful of outlier cases per dataset have
  larger deltas (max 22-33px), not yet individually triaged. No tolerance or verdict-gating was
  set — that is explicitly deferred follow-up work, per this project's no-guessed-tolerance
  discipline. Full numbers and the per-dataset table are in
  `wiki/impl-chart-v2-round-trip-check.md`.

## 2026-07-11 session 21e - Restore derived dataset artifacts after regeneration

- An advisor review of session 21c/21d's work flagged that regenerating
  `datasets/coordinate/coordinate-graph-v1` and `datasets/flowchart/flowchart-v1`
  via `generate-coordinate-dataset`/`generate-flowchart-dataset` only rewrites
  `visual_spec.json`/`metadata.json`/`expected_report.json`/`image.png` per case
  (the generator does `shutil.rmtree` then rewrites only those files), which
  deleted the previously tracked derived artifacts (`claim_graph.json`,
  `evidence_graph.json`, `overlay.png`, `report.json`,
  `primitive_evidence_graph.json`) for every regenerated case, and the new
  cases added this session never had them at all.
- These artifacts are recomputed outputs, not inputs, so this was never a
  correctness bug — validation already recomputes evidence from the image on
  every run. But it left the committed dataset directories inconsistent with
  their own history and would have swamped a real diff with spurious deletions.
- Fixed by running `verify-coordinate`/`verify-flowchart` with `--output-dir`
  set to each case's own directory for every case in both datasets (this is
  the same `write_verification_artifacts` path other verify-* commands use).
  All previously-deleted artifacts are restored and the new cases
  (coordinate golden-05/golden-06/mutated-08/mutated-09; flowchart
  golden-03/mutated-09) now have the full artifact set. Re-ran the full test
  suite afterward: 141/141 still pass, confirming no regression.
- Lesson for future dataset regeneration: after any `generate-*-dataset` run
  that touches an already-committed dataset directory, follow up with a
  `verify-*` pass per case (`--output-dir` = case dir) before considering the
  regeneration complete, rather than assuming missing derived artifacts are
  pre-existing/acceptable drift.

## 2026-07-11 session 21d - Flowchart-v1 branching/diagonal topology

- Closed the "single vertical chain topology only" item from
  `impl-flowchart-v1-vertical-chain.md`'s Known Limits — the fourth and last of the four
  extensions the user asked for this session ("all").
- Advisor gate before implementation: rendered a throwaway probe (one diamond, two diagonal
  out-edges to two rectangles) and ran the existing `extract_flowchart_evidence` against it
  before writing any dataset/rule code. Both connectors detected correctly with no gaps — the
  extractor (`_principal_axis_ends`, PCA-based) and the claim graph/rules (arbitrary
  `{from_id, to_id}` edge list) were already fully general. No extractor or rule changes needed.
- Only change required: `flowchart_generator.py`'s connector anchor calculation was hardcoded to
  bottom-center/top-center (vertical-only). Replaced with `_anchor_toward`, a general
  ray/boundary intersection against either shape, verified to reduce to the identical
  bottom-center/top-center calc for a purely vertical edge (regenerating the pre-existing 10-case
  dataset reproduced identical metrics — no rendering regression).
- `datasets/flowchart/flowchart-v1` grew to 12 cases: `golden-03` (decision node with two diagonal
  out-edges, all correct) and `mutated-09` (one branch connector missing). Needed a widened
  620px-wide canvas since the default width put the rightmost branch node's label region
  off-canvas at the new horizontal spread.
- Validation: controlled 12 cases, typed hits 7/7, ambiguous guard 2/2, 0 unsupported passes, 0
  golden failures. Full suite: 141 passing (139 -> +2 new tests).
- This closes all four extensions requested this session (arrow-v1 net-force, coordinate-graph
  label identity, coordinate-graph multi-series, flowchart branching topology). GitHub remote +
  cron-scheduled cloud routine setup remains blocked on the user's input (no `gh` CLI, no git
  remote configured).

## 2026-07-11 session 21c - Coordinate-graph-v1 multi-series polylines

- Closed the "single connected polyline only; no multi-series" item from
  `impl-coordinate-graph-v1-dual-axis.md`'s Known Limits.
- Advisor gate before implementation: confirmed no extractor rework was needed (point-pair edge
  detection is already color-independent), so the feature is purely a claim-graph/rule/dataset
  generalization. Also used the advisor call to empirically confirm (via `git stash`) that the
  pre-existing `mutated-04` extra finding is unrelated to session 21/21b changes.
- `source_reference.polylines: [{"series_id", "ordered_point_ids"}, ...]` accepted alongside the
  legacy singular `polyline`; both normalize to an internal `series_list` in
  `claim_graph.build_coordinate_claim_graph`.
- `coordinate_rules.run_coordinate_claims`'s polyline block now loops per series, tagging each
  `polyline_connection_wrong` finding with `evidence["series_id"]`.
- `coordinate_generator.render_coordinate_diagram` gained `polylines: list[list[str]] | None` to
  draw multiple independent line chains.
- `datasets/coordinate/coordinate-graph-v1` grew to 15 cases: `golden-06` (two independent
  2-point series, both correct) and `mutated-09` (`series_polyline_connection_wrong`, series-2's
  connection missing while series-1 stays correct).
- Validation: controlled 15 cases, typed hits 7/7, ambiguous guard 2/2, 0 unsupported passes, 0
  golden failures. Full suite: 139 passing (137 -> +2 new tests).

## 2026-07-11 session 21b - Coordinate-graph-v1 label-based point identity

- Closed the "no label-based point identity" item from `impl-coordinate-graph-v1-dual-axis.md`'s
  Known Limits, mirroring arrow-v1's label decoder/identity pattern almost exactly.
- `coordinate_extractor.py`: fixed 6-entry catalog `("A".."F")`, reusing `arrow_labels`'s generic
  `read_label_text`/`rank_label_templates` unchanged. New `point_label_box` helper (fixed offset
  from centroid) shared with `coordinate_generator.py` for rendering.
- Found and fixed a real extraction bug during validation: the polyline runs through the fixed
  up-right label-box direction for any generally-ascending point sequence, so every point except
  the last on the line failed to decode (line stroke read as glyph foreground). Fixed by
  precomputing `_line_mask` before the point loop and blanking line-mask pixels inside each
  point's label crop before decoding.
- `coordinate_rules._match_points_by_color` extended with label-first matching (mirrors
  `arrow_rules._match_arrows_by_color` exactly); `ambiguous_point_colors` gap now suppressed when
  two color-colliding points have distinct decoded labels.
- `datasets/coordinate/coordinate-graph-v1` grew to 13 cases: `golden-05` (labeled, all correct)
  and `mutated-08` (`label_resolved_color_collision`, color collision resolved via label,
  surfacing a real `point_position_wrong` instead of `needs_review`).

Verification:

- coordinate-graph-v1 controlled (13 cases): typed hits `6/6`, ambiguous guard `2/2`, false
  unsupported passes `0`, golden failures `0`, verdict mismatches `0`.
- coordinate-graph-v1-noisy (6 cases): unchanged, `4/4` typed hits (regression check only).
- Full test suite: 137 passing (135 prior + 2 new).

Bounds: label catalog is a small fixed 6-entry alphabet; label box position is a fixed offset,
not adaptive to point density.

## 2026-07-11 session 21 - Arrow-v1 non-zero declared expected resultant (net-force)

- Closed the last remaining tractable deferred item from `impl-arrow-v1-free-body.md`: extended
  `force-balance-correct` with a second `scenario_type` value, `"net-force"`, requiring a declared
  `source_reference.expected_resultant = {"magnitude_px", "direction_degrees"}`. Missing
  `expected_resultant` under `net-force` becomes a new ClaimGraph gap
  (`expected_resultant_not_declared`), mirroring the existing equilibrium gating pattern.
- `arrow_rules.run_arrow_claims` now branches on `scenario_type`: `equilibrium` keeps the existing
  zero-sum-ratio criterion unchanged; `net-force` compares the computed resultant against the
  declared vector (magnitude relative error vs. `resultant_ratio_tolerance`, direction difference
  vs. a new `resultant_angle_tolerance_degrees`, default 15deg). New finding type
  `net_force_resultant_mismatch`, kept distinct from `force_balance_violation`.
- `validation.py`'s `force_balance_metrics` counter extended to also count
  `net_force_resultant_mismatch` cases.
- `datasets/physics/arrow-v1` grew to 19 cases: `golden-07` (declared net-force, actual resultant
  matches) and `mutated-12` (`net_force_magnitude_mismatch`, actual resultant diverges from the
  declared vector). Both passed on the first empirical measurement (measure-before-claim
  discipline), no threshold tuning needed.

Verification:

- arrow-v1 controlled (19 cases): typed hits `9/9`, ambiguous guard `3/3`, force-balance typed
  hits `2/2` (equilibrium + net-force), false unsupported passes `0`, golden failures `0`,
  verdict mismatches `0`.
- Full test suite: 135 passing (132 prior + 3 new).

Bounds: still translational only (no torque/moment balance); no px-to-newton magnitude
calibration. This closes the force-balance deferred list down to those two long-term items only.

## 2026-07-11 session 20 - Arrow-v1 noisy-track equilibrium case

- Closed one deferred item from `impl-arrow-v1-free-body.md`: added a noisy-track equilibrium
  case pair. `arrow-v1-noisy` grew from 6 to 8 cases: `noisy-golden-03` (declared equilibrium,
  balanced, mild blur+downscale) and `noisy-mutated-05` (declared equilibrium, weight arrow
  shortened to 50px, mild downscale+JPEG), reusing existing postprocess settings and the existing
  `force-balance-correct` check unchanged.
- Also added the first pytest coverage for the arrow-v1 noisy dataset (`test_arrow_noisy_dataset_structure`,
  `test_arrow_noisy_dataset_validation_summary` in `test_arrow_v1.py`); previously the noisy
  dataset was only exercised via CLI, not the automated test suite.
- Per the measure-before-claim discipline, ran the new cases once before writing any test
  assertions: both passed on the first measurement, no extractor/rule changes needed.

Verification:

- arrow-v1-noisy (8 cases): typed hits `5/5`, force-balance typed hits `1/1`, false unsupported
  passes `0`, golden failures `0`, golden non-passes `0`, verdict mismatches `0`.
- Full test suite: 132 passing (130 prior + 2 new).

Bounds: still only two mild transform families (blur; downscale+JPEG); non-zero declared expected
resultants and torque/moment balance remain deferred.

## 2026-07-11 session 19 - Flowchart-v1 PrimitiveEvidenceGraph adapter

- Closed the flowchart-v1 known gap noted in session 17: added `primitive_graph_from_flowchart`
  in `primitive_evidence.py`, registering `flowchart-v1` as the fifth supported primitive profile
  in both `SUPPORTED_PRIMITIVE_PROFILES` and `specs/primitive-evidence-graph.schema.json`'s
  `profile` enum.
- Mapping: rectangle nodes -> `rectangle` primitives; diamond nodes -> `symbol` primitives (the
  fixed primitive-type enum has no dedicated diamond/polygon type, and `symbol` already supports
  bounds-only geometry via the existing rectangle/text_region/color_region schema branch); node
  labels -> `text_region` primitives with a `connected_to` relationship to their node (mirroring
  geometry-v1's dimension-label pattern); connectors -> `arrow` primitives with `touches`
  relationships to whichever endpoint node(s) resolved during extraction.
- Wired `run_flowchart_verification` / `extract_flowchart_evidence_from_inputs` to populate
  `primitive_graph` (previously deliberately `None`), extended `validate_domain_primitive_links`
  with a `FlowchartEvidenceGraph` branch, and added `flowchart-v1` to the CLI/MCP `--profile`
  choices.

Verification:

- 130 tests pass (128 prior + 2 new: adapter primitive-type/count assertions, profile-dispatch
  test). Controlled flowchart-v1 metrics re-verified unchanged after wiring (`6/6` typed hits,
  `2/2` ambiguity guards, `0` unsupported passes, node-count evidence `9/10` as before).

Bounds: audit-only layer as with the other four profiles; domain rules still consume the existing
`FlowchartEvidenceGraph` directly, not the primitive graph.

## 2026-07-11 session 18 - Coordinate-graph-v1 noisy blur/downscale/JPEG track

- Added the first noisy robustness track for coordinate-graph-v1, following the "Suggested Next
  Work" backlog item and the advisor's earlier note that extension items are lower-risk/faster to
  land than a new vertical when working without further scope confirmation available (autonomous
  session, no user response to a scope question).
- `coordinate_dataset.noisy_dataset_cases()`: 6 cases (2 golden, 4 typed mutated: missing_point,
  extra_point, point_position_wrong, axis_scale_misread), reusing
  `chart_generator._apply_postprocess` via `render_options["postprocess"]` (mild `blur_radius=0.6`
  on one golden/two mutated cases; `downscale_factor=0.88` + `jpeg_quality=82` on the other
  golden/two mutated cases) — no new postprocessing machinery.
- `build_noisy_coordinate_dataset`, CLI command `generate-noisy-coordinate-dataset`. No new
  validation summarizer was needed: `summarize_coordinate_validation_results` already takes a
  dataset-root argument and works unchanged against the noisy track.
- Per the no-guessed-tolerance/measure-before-claim discipline, ran the full 6-case set once
  before writing any test assertions or wiki claims: all 6 cases passed on the first
  measurement (no extractor bugs found here, unlike arrow-v1-noisy's first pass which surfaced
  two real bugs before it went clean).

Verification:

- coordinate-graph-v1-noisy (6 cases): typed hits `4/4`, false unsupported passes `0`, golden
  failures `0`, golden non-passes `0`, verdict mismatches `0`, point-count evidence `6/6`.
- Full test suite: 128 passing (126 prior + 2 new noisy-track tests in
  `test_coordinate_graph_v1.py`). Controlled coordinate-graph-v1 and all other verticals'
  controlled metrics unaffected (only additive dataset/CLI code; no extractor/rule files touched).

Bounds: only two mild configured transforms (light blur; light downscale+JPEG) — not evidence for
heavier distortion or independently authored/real-world images.

## 2026-07-11 session 17 - Flowchart-v1 vertical-chain verifier (fifth vertical)

- Implemented `flowchart-v1`, the fifth executable vertical, following an autonomous multi-hour
  work session per the user's request (build features to completion, one at a time, no fixed
  1-hour cap, pausing between features). Ran the advisor scope-freeze gate before writing any
  code, mirroring the discipline used for arrow-v1/geometry-v1/coordinate-graph-v1.
- Advisor-gated design decisions: node identity = color fill (not text), text label is a separate
  opt-in `node-label-correct` check so flaky decoding never blocks the core capability; connector
  topology is per-declared-edge presence/direction only (not general graph reconstruction); scope
  is a single vertical chain (no diagonal/branching/orthogonal routing) with exactly two shape
  types (rectangle, diamond).
- Added `flowchart_generator.py` (deterministic Pillow renderer: rectangle/diamond nodes stacked
  vertically, straight connector arrows), `flowchart_labels.py` (fixed 6-entry catalog
  template-matched node-label decoder, mirroring `arrow_labels.py`), `flowchart_extractor.py`
  (spec-blind shape classification via fill-ratio geometry, achromatic-mask connector detection
  reusing the arrow-v1 principal-axis head/tail technique, nearest-node attach resolution),
  `flowchart_rules.py` (`run_flowchart_claims`: count/presence/shape/label/connector checks with
  color-match + collision-guard, mirroring `arrow_rules._match_arrows_by_color`), and
  `build_flowchart_claim_graph` in `claim_graph.py` with the same unsupported-check gap guardrail
  as the other four verticals.
- Found and fixed a real extraction bug during the first verification smoke test: node label text
  (rendered achromatic, beside each node on white background) has anti-aliased glyph edges that
  blend black text with white background across the full intensity range, landing inside the
  connector mask's achromatic value band regardless of how that band was narrowed. Every golden
  case initially produced dozens of false tiny "connector" components and a spurious
  `degenerate_connector_geometry` gap forcing `needs_review`. Fixed by explicitly blanking each
  detected node's label bbox out of the connector mask before running connected components,
  rather than tuning thresholds around the noise.
- Added `specs/flowchart-evidence-graph.schema.json`, flowchart service entrypoints
  (`run_flowchart_verification` — deliberately does not populate `primitive_graph`, an explicit
  scope bound rather than an oversight), CLI commands `generate-flowchart-dataset`,
  `verify-flowchart`, `run-flowchart-validation`, and three new MCP tools
  (`build_flowchart_claim_graph`, `parse_flowchart`, `verify_flowchart`).
- Added `datasets/flowchart/flowchart-v1/` with 10 cases (2 golden, 8 mutated: 6 typed + 2
  ambiguous: `ambiguous_node_colors`, `degenerate_node_geometry`).

Verification:

- flowchart-v1 controlled (10 cases): typed hits `6/6`, ambiguous guard `2/2`, node-count evidence
  `9/10` (the 10th case's degenerate node is correctly excluded, not a miss), false unsupported
  passes `0`, golden failures `0`, golden non-passes `0`, verdict mismatches `0`. All results
  matched expectations on the first full dataset run after the connector-mask fix.
- Full test suite: 126 passing (106 prior + 20 new in `test_flowchart_v1.py`, including one MCP
  tool-list update for the 3 new tools). No shared extractor/rule files were modified, so
  chart-v2/arrow-v1/geometry-v1/coordinate-graph-v1 controlled metrics are unaffected by
  construction (only new files plus additive registrations in `contracts.py`, `service.py`,
  `cli.py`, `server.py`, `validation.py`).

Bounds: controlled Pillow renders only; single vertical-chain topology (no branching/diagonal/
orthogonal routing); exactly two shape types (rectangle, diamond); node label catalog is a
6-entry fixed alphabet; no noisy track or independently authored/real-world images yet; no
`PrimitiveEvidenceGraph` adapter yet (audit-only layer, not a blocking gap for this vertical's
domain verdicts).

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
