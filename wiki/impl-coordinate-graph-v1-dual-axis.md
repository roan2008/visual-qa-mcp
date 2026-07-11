---
name: impl-coordinate-graph-v1-dual-axis
description: coordinate-graph-v1 dual-axis scatter/polyline verifier design, bounds, and validation
metadata:
  type: implementation
  status: current
  last_updated: 2026-07-11
---

# Coordinate Graph v1: Dual-Axis Scatter/Polyline Verifier

## Purpose

Fourth executable vertical. Proves the Spec -> ClaimGraph -> EvidenceGraph -> Rules architecture
extends to a coordinate plane with two **independent numeric axes**, the one genuinely new
capability beyond chart-v2 (which only reads a single Y-axis; X is categorical bar bins).
[source: mcp-server/src/visual_qa_mcp/coordinate_extractor.py:1]

## Scope Bounds (Controlled Only)

- Synthetic coordinate planes rendered by `coordinate_generator.py`: independent numeric X and Y
  axes with ticks, color-identified scatter points, and one connected polyline linking a
  declared ordered subset of points.
- Point identity is declared by color in `source_reference.points` (id, rgb, x, y), reusing the
  arrow-v1 color-match + collision-guard pattern. No label-based identity in v1.
- Tick values are restricted to multiples of 5 in [-150, 150] to reuse `tick_reader`'s existing
  numeric template catalog (`tick_reader.rank_numeric_text_templates`) without building a second
  one. [source: mcp-server/src/visual_qa_mcp/tick_reader.py:_candidate_templates]
- No multi-series, no curve fitting, no general topology checks, no noisy track, no
  independently authored/real-world images.

## Dual-Axis Extractor Algorithm (spec-blind)

1. Dark mask (`intensity < 110`) finds the Y-axis vertical line (longest contiguous dark run in
   the left ~55% of columns) and the X-axis horizontal line (longest contiguous dark run in the
   bottom ~65% of rows). Either axis missing a run >= 40% of its span -> unreadable.
2. Tick marks are short dashes protruding from the axis frame: Y-ticks sampled at column
   `axis_line_x - 4`, X-ticks at row `axis_line_y + 4`, clustered via `chart_extractor._cluster_indices`.
   Each search is bounded to the correct side of the opposite axis line (`>= axis_line_x` for
   X-ticks, `<= axis_line_y` for Y-ticks) — the first implementation lacked this bound and the
   axis-min tick's label text (which sits at the exact pixel row/column where the two axes meet)
   bled into the other axis's tick-mark search, injecting spurious "ticks" that corrupted the
   linear fit (see Known Bugs Fixed below).
3. Each tick's numeric label is decoded with `tick_reader.rank_numeric_text_templates`, then a
   local sequence-fit search (`_fit_axis_sequence`, mirroring but not modifying
   `tick_reader._decode_tick_sequence_result`) finds the best assignment of candidates to
   positions requiring: >=3 readable ticks, monotonicity in the correct direction (Y values
   decrease as pixel y increases; X values increase as pixel x increases), and residual <2% of
   the axis's value span. No fit -> `{orientation}_axis_unreadable` gap.
4. A fitted axis stores `fit_slope`/`fit_intercept` directly (`value = slope*pixel + intercept`)
   rather than reusing chart-v2's baseline-pixel formula, avoiding sign bookkeeping differences
   between the two axis orientations.
5. Points: saturation mask (`arrow_extractor._saturation_mask`, reused unchanged) + connected
   components; centroid -> pixel position; converted to data space via both axes' linear fits.
   Colliding colors (<40 RGB distance) -> `ambiguous_point_colors` gap.
6. Polyline: a low-saturation gray line mask (`spread<=20`, `70<=value<=180`) distinguishes the
   polyline (mid-gray) from the axis frame (near-black) and points (saturated). For every pair of
   detected points, 24 samples along the straight pixel segment are checked against the line mask
   (2px radius); >=85% coverage -> a detected edge. This is a per-pair "is there a rendered edge"
   test, not general topology/curve tracing.

## Checks and Findings

| check_id | rule_id | finding types | severity |
|---|---|---|---|
| point-count-matches | coordinate-graph-v1.point-count-matches | point_count_mismatch | high |
| required-points-present | coordinate-graph-v1.required-points-present | missing_point, extra_point | critical |
| point-positions-correct | coordinate-graph-v1.point-positions-correct | point_position_wrong | critical |
| polyline-connections-correct (opt-in) | coordinate-graph-v1.polyline-connections-correct | polyline_connection_wrong | high |
| axis-scale-correct | coordinate-graph-v1.axis-scale-correct | axis_scale_misread | critical |

`polyline-connections-correct` is opt-in via `source_reference.polyline.ordered_point_ids` +
the check id in `checks[]`, mirroring arrow-v1's `scenario_type`/`force-balance-correct` and
geometry-v1's `layout`/`hole-alignment-correct` gating pattern. Either half without the other
becomes a `ClaimGraph` gap.

An unresolved point endpoint in a polyline edge is skipped per-edge (`continue`), not treated as
a whole-check skip — mirroring arrow-v1's per-arrow `continue` in the direction/anchor checks.
This matters: a plain `missing_point` case must still verdict `fail` (a real finding), not
`needs_review`; only ambiguous evidence (color collision, unreadable axis) should force
`needs_review` via the whole-check skip path.

Unknown spec checks fall into `ClaimGraph` gaps -> `checks_skipped` -> needs_review, the same
guardrail as chart-v2/arrow-v1/geometry-v1.

## Reused Infrastructure

- `VerificationResult` / `ArtifactPaths` / `write_verification_artifacts` (service layer)
- verdict/confidence helpers from `chart_rules.py` (`_overall_verdict`, `_estimate_rule_confidence`)
- `arrow_extractor._saturation_mask` (point color-component isolation)
- `chart_extractor._cluster_indices`, `chart_extractor._maximum_true_run` (tick-mark clustering)
- `tick_reader.rank_numeric_text_templates` (numeric glyph matching, catalog unmodified)
- `arrow_rules`-style color-match + collision-guard pattern (`_match_points_by_color`)
- overlay writer, findings/claim-graph schemas, validation summary pattern
- `PrimitiveEvidenceGraph` adapter: points -> `point` primitives, axes -> `line` primitives,
  detected polyline edges -> `connected_to` relationships (not `polyline` primitives, since each
  edge is independently evidenced, not a single traced path)
- new schema: `specs/coordinate-evidence-graph.schema.json`

## Dataset

`datasets/coordinate/coordinate-graph-v1/`: 11 cases = 4 golden + 7 mutated (5 typed + 2
ambiguous). Golden cases cover zero-baseline, non-zero-minimum, and signed axis configurations,
including one case (`golden-03`) with deliberately mismatched X/Y pixel-per-unit scale (X: 2.8
px/unit, Y: 4.2 px/unit) — a case where a naive single-axis or identity-pixel-mapped extractor
would silently place every point at a detectably wrong position.

Typed defects: `missing_point`, `extra_point`, `point_position_wrong`, `axis_scale_misread`
(Y-axis tick labels rendered with a uniform +10 offset while points keep their true pixel
positions), `polyline_connection_wrong` (rendered polyline skips a declared point). Ambiguous:
`ambiguous_point_colors`, `unreadable_axis` (Y-axis ticks reduced to a single tick mark).
[source: mcp-server/src/visual_qa_mcp/coordinate_dataset.py:dataset_cases]

## Tolerance Measurement (2026-07-11)

Per the project's no-guessed-tolerance discipline (mirrors arrow-v1's force-balance-ratio
measurement), pixel->data round-trip error was measured *before* setting any position tolerance,
across three axis configurations with X-scale != Y-scale:

| configuration | X range | Y range | max abs error X | max abs error Y |
|---|---|---|---|---|
| zero-baseline | 0..100 | 0..50 | 0.000 | 0.000 (before corner-tick fix: 0.000/0.095) |
| non-zero-min | 20..120 | 30..90 | 0.000 | 0.000 |
| signed, X-scale != Y-scale | -100..100 | -50..50 | 0.000 | 0.000 |

The first measurement pass (before the corner-tick-bleed fix below) showed up to 0.095 data
units of error (~0.2% of axis range) on some configurations; after the fix, measured error on
all three configurations is effectively zero (Pillow's deterministic circle rasterization plus
exact template-matched tick decoding leaves no residual bias on these controlled renders).
Position tolerance was set to **3% of each axis's declared range** — comfortably above the
measured margin even before the fix, and not tuned per case.

## Bug Found and Fixed During Implementation

The Y-axis's minimum-value tick sits at the same pixel row as the X-axis line (both axes meet at
the plot's bottom-left corner), so its label-text crop box vertically overlapped the row used to
scan for X-axis tick marks — and symmetrically for the X-axis's minimum-value tick's crop box
against the Y-tick-mark scan column. This corrupted the affected axis's tick-position list with
extra "phantom" ticks whose decoded text combined with the real ticks into a materially wrong
linear fit (observed as a false `axis_scale_misread` finding on an otherwise-golden signed-axis
case). Fixed by bounding each tick-mark search to the correct side of the opposite axis line.
[source: mcp-server/src/visual_qa_mcp/coordinate_extractor.py:_tick_positions]

## Validation Result (2026-07-11)

- coordinate-graph-v1 controlled (11 cases): typed hits `5/5`, ambiguous guard `2/2`, point-count
  evidence `11/11`, false unsupported passes `0`, golden failures `0`, golden non-passes `0`,
  verdict mismatches `0`.
- Full test suite: 106 passing (85 prior + 21 new: 20 coordinate-focused tests plus one new MCP
  `verify_coordinate` schema-validity test).
- chart-v2, arrow-v1, and geometry-v1 controlled metrics re-verified unchanged: chart `9/9`
  (guard `1.0`), arrow `8/8` (guard `1.0`), geometry `7/7` (guard `1.0`), all with `0`
  unsupported passes and `0` golden failures.

## Known Limits

- No curve/function fitting.
- No general connectivity/topology extraction — polyline evidence is a per-declared-edge
  pixel-coverage check, not a traced path.
- Tick value catalog restricted to multiples of 5 in [-150, 150] (reuses `tick_reader`'s existing
  numeric templates rather than building a second catalog).
- No independently authored/real-world images yet.
- (Multi-series and label-based point identity were closed in session 21b/21c — see below.)

## Label-Based Point Identity (2026-07-11, session 21)

Added a second identity signal, mirroring arrow-v1's label decoder, closing that item from
Known Limits.

### Label decoding

- Fixed catalog `("A","B","C","D","E","F")`, reusing `arrow_labels.read_label_text` /
  `rank_label_templates` unchanged (those functions are generic, not arrow-specific, and already
  accept a `catalog` override). [source: mcp-server/src/visual_qa_mcp/coordinate_extractor.py]
- Label box is a fixed offset from the point centroid (`POINT_LABEL_OFFSET_PX = (12, -26)`,
  size `(56, 20)`, clipped to image bounds) — simpler than arrow-v1's tail/head-midpoint
  geometry since a point has no shaft to be perpendicular to.
- **Bug found and fixed during implementation**: the label box sits in a fixed direction
  (up-right) from every point, but the polyline connects consecutive points and, for a
  generally ascending point sequence, runs directly through that same up-right region —
  contaminating the label crop with the line's gray stroke (which also passes the achromatic
  foreground threshold used for glyph matching). Every point except the last on the line failed
  to decode. Fixed by computing `_line_mask` once before the point loop and blanking
  (`= 255`, i.e. background) any line-mask pixels inside each point's label crop before running
  `read_label_text` — the polyline evidence itself doesn't need those pixels either, so nothing
  is lost. [source: mcp-server/src/visual_qa_mcp/coordinate_extractor.py:extract_coordinate_evidence]

### Identity resolution (`coordinate_rules._match_points_by_color`)

Label match (exact decoded-text equality) runs first and consumes matched points; remaining
expected ids fall back to greedy nearest-color matching — identical structure to
`arrow_rules._match_arrows_by_color`. The extractor's `ambiguous_point_colors` gap is
suppressed when two color-colliding points have distinct, confidently decoded labels.
Demonstrated by dataset case `mutated-08`: p2 and p3 share a color, resolved via label,
producing a real `point_position_wrong` finding instead of `needs_review`.

### Dataset growth

`datasets/coordinate/coordinate-graph-v1/` grew to 13 cases (5 golden + 8 mutated):
- `golden-05`: four labeled points, all correct -> pass.
- `mutated-08` (`label_resolved_color_collision`): p3 rendered with p2's color and shifted
  off its declared position, but keeps its own distinct label -> `point_position_wrong`,
  not `needs_review`.

### Validation Result (2026-07-11, session 21)

- coordinate-graph-v1 controlled (13 cases): typed hits `6/6`, ambiguous guard `2/2`, false
  unsupported passes `0`, golden failures `0`, verdict mismatches `0`.
- coordinate-graph-v1-noisy (6 cases): unchanged, typed hits `4/4`, `0` unsupported passes —
  noisy specs do not declare point labels, so this is a regression check, not new coverage.
- Full test suite: 137 passing (135 prior + 2 new: labeled-points-pass and
  label-resolves-collision tests; dataset case counts grew inside existing dataset-summary
  tests).

### Updated Known Limits

- Label catalog is a small fixed alphabet (6 entries); does not generalize to arbitrary text.
- Label box position is a fixed offset, not adaptive to local point density — two points placed
  very close together could still have overlapping label crops (not exercised in the current
  dataset).

## Noisy Blur/Downscale/JPEG Track (2026-07-11)

Added `datasets/coordinate/coordinate-graph-v1-noisy/`: 6 cases (2 golden, 4 typed mutated),
reusing `chart_generator._apply_postprocess` (`blur_radius`, `downscale_factor` + `jpeg_quality`)
via `render_options["postprocess"]`, mirroring arrow-v1/geometry-v1's noisy-track pattern. Mild
settings only (`blur_radius=0.6`; `downscale_factor=0.88` + `jpeg_quality=82`), matching the
severity already validated for arrow-v1-noisy.

## Multi-Series Polylines (2026-07-11, session 21c)

Closed the "Single connected polyline only; no multi-series" item from Known Limits. Scope was
frozen deliberately narrow before implementation (advisor gate): an arbitrary number of named
series, each an independent ordered polyline over a subset of the declared points, checked by
the existing single opt-in `polyline-connections-correct` check generalized to iterate a list
rather than one chain. No cross-series relations, no legend OCR, no curve fitting.

### Design: color still identifies points, not series

The advisor's suggested model (color identifies the *series*, order/labels identify points
*within* it) was considered but not needed: the extractor's point-pair edge detection already
operates independently per pair of points regardless of color, and feature 2's label-based
identity (session 21) already resolves same-color collisions when points carry distinct labels.
So multi-series required **no extractor changes at all** — `_edge_coverage`/`polyline_edges`
already checks straight-line pixel coverage between any two specific points, which is exactly
what a second, separately-routed polyline needs. The entire feature is a claim-graph/rule/dataset
generalization:

- `source_reference.polylines: [{"series_id": str, "ordered_point_ids": [...]}, ...]` is now
  accepted alongside the legacy singular `source_reference.polyline.ordered_point_ids`.
  [source: mcp-server/src/visual_qa_mcp/claim_graph.py:build_coordinate_claim_graph] Both forms
  normalize to an internal `series_list`; the legacy form becomes a single implicit
  `"series-1"`.
- The `polyline-connections-correct` claim's `expected` now carries `"series": [...]` instead of
  a single `"ordered_point_ids"`; `coordinate_rules.run_coordinate_claims` loops over each series'
  consecutive-pair check independently, tagging each `polyline_connection_wrong` finding with
  `evidence["series_id"]` so the report attributes the break to the right series.
  [source: mcp-server/src/visual_qa_mcp/coordinate_rules.py]
- `coordinate_generator.render_coordinate_diagram` gained a `polylines: list[list[str]] | None`
  parameter (a list of ordered id lists) alongside the legacy `polyline_point_ids`, drawing each
  series as its own line segment chain in the same shared `POLYLINE_COLOR` — no rendering change
  was needed to disambiguate series pixel-wise, since edge detection is point-pair scoped, not
  color scoped.

### Dataset growth

`datasets/coordinate/coordinate-graph-v1/` grew to 15 cases (6 golden + 9 mutated):
- `golden-06`: the existing 4-point linear diagram split into two independent 2-point series
  (`p1-p2`, `p3-p4`), both polylines correct -> pass.
- `mutated-09` (`series_polyline_connection_wrong`): same two-series declaration, but the
  `series-2` polyline is rendered with only `p3` (no line to `p4`) -> `polyline_connection_wrong`
  with `evidence["series_id"] == "series-2"`, `series-1` unaffected.

### Validation Result (2026-07-11, session 21c)

- coordinate-graph-v1 controlled (15 cases): typed hits `7/7`, ambiguous guard `2/2`, false
  unsupported passes `0`, golden failures `0`, verdict mismatches `0`.
- Full test suite: 139 passing (137 prior + 2 new: multi-series-pass and
  multi-series-series-scoped-failure tests; dataset case counts grew inside existing
  dataset-summary tests).

### Updated Known Limits

- Series are declared explicitly by the spec (`source_reference.polylines`), not inferred from
  color grouping — there is no rule yet for "group same-colored points into an implied series."
- No cross-series checks (e.g., series must not visually cross, series point counts must match).
- Rendering always uses one shared polyline color for every series; a real-world multi-series
  chart with per-series line colors and a legend is out of scope until legend OCR exists.

Unlike arrow-v1-noisy's first pass (which surfaced two real robustness bugs before it validated
cleanly), this track's first empirical measurement passed all 6 cases without any extractor
changes: typed hits `4/4`, golden failures `0`, false unsupported passes `0`, verdict mismatches
`0`. `generate-noisy-coordinate-dataset` and the existing `run-coordinate-validation` command work
against it unchanged (that command already takes a dataset-root argument, so no new validation
summarizer was needed). This result is bounded to the two mild configured transforms tested; it is
not evidence for heavier distortion or independently authored images.
[source: mcp-server/src/visual_qa_mcp/coordinate_dataset.py:noisy_dataset_cases]
