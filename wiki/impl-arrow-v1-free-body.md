---
name: impl-arrow-v1-free-body
description: arrow-v1 free-body diagram verifier design, bounds, and validation
metadata:
  type: implementation
  status: current
  last_updated: 2026-07-10
---

# Arrow v1: Free-Body Diagram Verifier

## Purpose

First non-chart vertical. Proves the Spec -> ClaimGraph -> EvidenceGraph -> Rules architecture
generalizes beyond charts. [source: mcp-server/src/visual_qa_mcp/arrow_rules.py:1]

## Scope Bounds (Controlled Only)

- Synthetic free-body diagrams: one gray box object on white background plus colored force
  arrows rendered by `arrow_generator.py`. [source: mcp-server/src/visual_qa_mcp/arrow_generator.py:60]
- Arrow identity is declared by color in `source_reference.arrows` (id, rgb,
  direction_degrees, target). This is a controlled-v1 simplification; no text/label reading.
  [source: mcp-server/src/visual_qa_mcp/claim_graph.py (build_arrow_claim_graph)]
- No OCR, no real-world images, no physics-theory checks (no force balance or magnitude).

## Angle Convention

Degrees counterclockwise, `0 = +x (right)`, `90 = up`, `270 = down`. Image y grows downward, so
`angle = atan2(-(head_y - tail_y), head_x - tail_x) % 360`.
[source: mcp-server/src/visual_qa_mcp/arrow_extractor.py (_analyze_component)]

## Extractor Algorithm (spec-blind)

1. Saturation mask: `max(channel) - min(channel) >= 50` isolates colored arrow pixels;
   gray/white excluded. [source: mcp-server/src/visual_qa_mcp/arrow_extractor.py:_saturation_mask]
2. Gray object mask: channel spread <= 12 and mean value in [90, 205] -> object region bbox;
   fewer than 400 gray pixels -> `object_region_unresolved` gap.
3. 8-connected components over the saturation mask; components with < 60 pixels or principal
   length < 24 px or no head/tail spread contrast -> `degenerate_arrow_geometry` gap covering
   all four checks.
4. Per component: principal axis from 2x2 covariance (`theta = 0.5*atan2(2*sxy, sxx-syy)`),
   end windows = 20% of projection span (min 4 px), head = end with larger perpendicular
   spread (ratio threshold 1.3).
5. Two arrows with mean-color distance < 40 -> `ambiguous_arrow_colors` gap (identity checks
   skipped -> needs_review).

## Checks and Findings

| check_id | rule_id | finding types | severity |
|---|---|---|---|
| arrow-count-matches | arrow-v1.arrow-count-matches | arrow_count_mismatch | high |
| required-arrows-present | arrow-v1.required-arrows-present | arrow_missing, unexpected_arrow | critical |
| arrow-directions-correct | arrow-v1.arrow-directions-correct | arrow_direction_wrong | critical |
| arrow-anchors-object | arrow-v1.arrow-anchors-object | arrow_anchor_detached | high |

Tolerances: angle 15 deg, color match distance 60 (Euclidean RGB), anchor 14 px.
Unknown spec checks fall into ClaimGraph gaps -> `checks_skipped` -> needs_review, same
guardrail as chart-v2. [source: mcp-server/src/visual_qa_mcp/claim_graph.py]

## Reused Infrastructure

- `VerificationResult` / `ArtifactPaths` / `write_verification_artifacts` (service layer)
- verdict/confidence helpers from `chart_rules.py` (`_overall_verdict`,
  `_estimate_rule_confidence`)
- overlay writer, findings/claim-graph schemas, validation summary pattern
- new schema: `specs/arrow-evidence-graph.schema.json`

## Dataset

`datasets/physics/arrow-v1/`: 12 cases = 4 golden + 8 mutated (6 typed + 2 ambiguous).
Typed defects: wrong_direction_reversed, wrong_direction_diagonal, missing_arrow, extra_arrow,
detached_anchor, swapped_arrow_colors. Ambiguous: ambiguous_arrow_colors, degenerate_arrow.
[source: mcp-server/src/visual_qa_mcp/arrow_dataset.py:dataset_cases]

## Validation Result (2026-07-10)

- typed hits 6/6 (`critical_error_recall = 1.0`)
- ambiguous guard 2/2, false unsupported passes 0
- golden failures 0, golden non-passes 0, verdict mismatches 0
- arrow-count evidence accuracy 11/11
- full test suite: 54 passing (43 prior + 11 arrow tests)
- chart-v2 controlled metrics re-verified unchanged (9/9, guard 1.0, 0/0)
[source: run-arrow-validation and run-validation CLI output, 2026-07-10]

## Known Limits

- Single rectangular object; no inclined planes, multiple bodies, or torque geometry.
- No real-world arrow images; controlled + noisy synthetic renders only.
- No theory-aware physics rules (completeness relative to declared spec only).

## Label-Based Identity and Noisy Track (2026-07-10, session 12)

Added a second identity signal so arrow-v1 no longer depends on color alone.

### Label decoding

- `arrow_labels.py`: fixed catalog `("W","N","F","f","T","P","Fx","Fy")`, template-matched the
  same way as chart-v2's tick reader (render candidate glyphs, pixel-difference score, ambiguity
  margin guard). [source: mcp-server/src/visual_qa_mcp/arrow_labels.py]
- Label region is computed from the tail/head **midpoint**, offset perpendicular to the shaft —
  not from the tail alone. The tail sits exactly on the object's edge, so a tail-anchored box
  reliably overlapped the object rectangle; the midpoint is always clear of it.
- The foreground mask for glyph matching is achromatic-only (`channel spread <= 30`, `value <
  150`): a plain grayscale threshold also caught saturated arrow colors (e.g. blue has luminance
  ~106), corrupting the crop.
- `_analyze_component`'s tail/head point changed from a windowed average to the true geometric
  extremity (`argmin`/`argmax` of the projection) — the average was biased ~9px inward by the
  window, enough to misalign the label crop even though direction/anchor checks tolerated it.

### Identity resolution (`arrow_rules._match_arrows_by_color`)

Label match (exact decoded-text equality) runs first and consumes matched arrows; remaining
expected ids fall back to greedy nearest-color matching, unchanged from session 11. A label
match that hits more than one expected id/detected arrow is treated as unresolved, not guessed.

The extractor's `ambiguous_arrow_colors` gap is now suppressed when two color-colliding arrows
have distinct, confidently decoded labels — identity is resolvable even though color is not.
Demonstrated by dataset case `mutated-09`: same color on friction/applied, resolved via label,
producing a real `arrow_direction_wrong` finding instead of `needs_review`.

### Noisy track

`datasets/physics/arrow-v1-noisy/`: 6 cases (2 golden, 4 typed mutated) with blur/downscale/JPEG
postprocessing reused from `chart_generator._apply_postprocess`. All noisy cases render labels.

First-pass noisy validation surfaced two real robustness gaps, both fixed in this session:

1. **Color drift under JPEG/downscale**: compression shifted detected arrow color by up to ~74
   in RGB distance, exceeding the 60-unit `color_match_distance` tolerance. Raising the
   tolerance was rejected as unsafe — the closest canonical color pair (weight/friction) is only
   81 apart, so a looser threshold risks silent cross-matching. Fixed by relying on labels
   (noise-robust) as the primary identity signal for noisy cases instead of loosening color
   tolerance.
2. **Object bbox inflation under blur**: `extract_arrow_evidence` computed the object region's
   bbox from the global min/max of every gray-masked pixel. Blur/JPEG scattered small
   gray-ish noise blobs far from the object, inflating the bbox from the true `[240,210,360,300]`
   to `[193,161,409,393]` — large enough that a deliberately detached arrow (`tail_offset=[90,40]`)
   read as anchored, a false unsupported pass. Fixed by using the bbox of the **largest connected
   component** of the gray mask only, mirroring the connected-component approach already used
   for arrows. [source: mcp-server/src/visual_qa_mcp/arrow_extractor.py:extract_arrow_evidence]

### Validation Result (2026-07-10, session 12)

- arrow-v1 controlled (regenerated, now 14 cases: 5 golden + 9 mutated): typed hits `7/7`,
  ambiguous guard `2/2`, false unsupported passes `0`, golden failures `0`.
- arrow-v1-noisy (6 cases: 2 golden + 4 typed mutated): typed hits `4/4`, false unsupported
  passes `0`, golden failures `0`, verdict mismatches `0`.
- Full test suite: 56 passing (54 prior + 2 new label tests; dataset case count grew inside the
  existing dataset-summary tests).
- chart-v2 controlled and arrow-v1 controlled metrics re-verified unchanged after the
  object-mask fix.

### Updated Known Limits

- Label catalog is a small fixed alphabet (8 entries); does not generalize to arbitrary text.
- Noisy track covers only mild blur/downscale/JPEG; no adversarial or heavy-distortion cases yet.
- Object detection is still a single connected gray blob; multiple objects or partially
  occluded objects are unsupported.

## Translational Force Balance (2026-07-10, session 13)

First theory-aware (Level 3) rule: `force-balance-correct`, verifying that a declared
equilibrium scenario's drawn force vectors sum to approximately zero.

### Design decision (advisor gate, session 13)

- **Magnitude source**: sum the extractor's existing pixel vectors (`length_px`,
  `angle_degrees`) directly. Spec-declared magnitudes were rejected (would verify the spec's
  own arithmetic, not the image, violating the evidence-grounding rule); px-to-newton
  calibration was deferred (new error source, spec bloat, not needed for a zero-sum check).
  [source: mcp-server/src/visual_qa_mcp/arrow_rules.py (force-balance block)]
- **Equilibrium gating**: opt-in only, via `source_reference.scenario_type = "equilibrium"`
  plus a `force-balance-correct` entry in `checks[]`. Either half without the other becomes a
  `ClaimGraph` gap (`scenario_type_not_declared` / `scenario_without_balance_check`) ->
  `checks_skipped` -> needs_review. [source: mcp-server/src/visual_qa_mcp/claim_graph.py:build_arrow_claim_graph]
- **Scope**: translational force balance only (vector sum). NOT torque/moment balance and not
  full static equilibrium — finding type is deliberately named `force_balance_violation`.

### Rule mechanics

- Reuses `_match_arrows_by_color` (label-first identity). If any expected arrow is unmatched
  or identity is ambiguous (extractor `ambiguous_arrow_colors` gap now covers this check id
  too), the check is skipped with an explicit reason — a partial force set is never summed.
- Resultant = sum of `length_px * (cos(angle), sin(angle))` over all matched arrows.
- Defect criterion: `|resultant| / max(length_px)` > `resultant_ratio_tolerance`
  (default 0.15). Evidence includes per-arrow px vectors, the resultant vector/magnitude,
  and the tolerance. Severity: critical.
- Measured noise floor on golden renders: extraction angle error ~1.3 deg/arrow leaves the
  golden resultant ratio well below 0.15, while a 50-px-vs-90-px shortened weight arrow
  produces a ratio of ~0.44 — a clear margin, no per-case threshold tuning.
  [source: run-arrow-validation output, 2026-07-10]

### Dataset growth

`datasets/physics/arrow-v1/` regenerated to 17 cases (6 golden + 11 mutated):
- `golden-06`: declared equilibrium, balanced labeled forces -> pass.
- `mutated-10` (`force_balance_magnitude`): weight arrow shortened to 50 px — same direction,
  same anchor, correct count/presence — so only the new check catches it. This is the first
  defect class invisible to all four session-11 rules.
- `mutated-11` (`ambiguous_arrow_colors_equilibrium`): unlabeled color collision with a
  declared equilibrium -> balance check skipped -> needs_review (guard path proven).

### Validation Result (2026-07-10, session 13)

- arrow-v1 controlled (17 cases): typed hits `8/8`, ambiguous guard `3/3`, force-balance
  typed hits `1/1`, false unsupported passes `0`, golden failures `0`, verdict mismatches `0`.
- arrow-v1-noisy (6 cases): unchanged `4/4` typed hits, `0` false unsupported passes; noisy
  specs do not declare `scenario_type`, so the balance check does not run there (scope, not
  a gap).
- chart-v2 controlled re-verified unchanged (`9/9`, guard `1.0`, `0`/`0`).
- Full test suite: 61 passing (56 prior + 5 new force-balance tests).

### Deferred (explicitly out of this increment)

- Absolute magnitude calibration (px-to-newton scale references).
- Torque/moment balance (needs points of application).
- Non-zero declared expected resultant (unbalanced-scenario verification).
