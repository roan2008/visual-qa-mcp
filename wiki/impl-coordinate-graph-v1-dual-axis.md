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

- Single connected polyline only; no multi-series, no curve/function fitting.
- No general connectivity/topology extraction — polyline evidence is a per-declared-edge
  pixel-coverage check, not a traced path.
- Tick value catalog restricted to multiples of 5 in [-150, 150] (reuses `tick_reader`'s existing
  numeric templates rather than building a second catalog).
- No noisy-image robustness track and no independently authored/real-world images yet.
- No label-based point identity; color collisions always route to `needs_review`.
