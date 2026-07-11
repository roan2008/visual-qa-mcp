---
name: impl-chart-v2-covering-array-input-model
description: chart-v2 formal input model with Matrix A / Set B oracle and a frozen 18-case covering-array dataset
metadata:
  type: implementation
  status: current
  last_updated: 2026-07-11
---

# chart-v2 Formal Input Model (Covering-Array Dataset v1)

Implements roadmap item 1 from `wiki/next-steps.md` ("Formal input model + stratified
registry + mixed-strength covering arrays"), following
[knowledge-synthetic-coverage-deep-research](knowledge-synthetic-coverage-deep-research.md).
An advisor review before implementation flagged the one design risk that had to be
resolved first: **the expected-verdict oracle must be non-circular**, and masking means
expected verdict is not simply a function of the defect axis — evidence-degrading
presentation must flip the expected verdict to `needs_review` regardless of what defect
was injected.

## Design: universe partition, not one factor list

Every axis level is classified **in-universe** (evidence-preserving) or **out-of-universe**
(evidence-degrading), based on the renderer-crutch-stripping experiment already recorded
in `knowledge-accuracy-and-synthetic-data-roadmap.md`:

- `tick_catalog`: `catalog` (multiples of 5, in-universe) vs. `off_catalog` (out-of-universe
  — tick reader returns `None` for every tick).
- `font_family` (matplotlib renderer only): `arial` (in-universe) vs. `dejavu_serif`
  (out-of-universe — x-axis category label matching fails).
- `color_style`: `default` vs. `custom` bar/grid fill — both in-universe (already proven
  safe by existing golden-03/golden-08 controlled cases).
- `defect`: `none`, `wrong_bar_height`, `wrong_axis_unit` — the injected-defect axis,
  independent of universe membership.

**Scoped out of this dataset**: a genuine layout mismatch (renderer geometry diverging from
`ChartLayout`'s assumptions) was the fourth out-of-universe axis found by the
crutch-stripping experiment, but the shipped generator can't reproduce it — the extractor
reads `metadata.render_options.layout_overrides` and derives its own layout expectation
from the same overrides (`chart_extractor.py:483`), so any override supplied to the
renderer is transparently matched by the extractor. Reproducing "unmatched layout" needs a
new renderer capability (e.g. a `tight_layout()`-style path) that this MVP does not build.
Documented as a gap, not silently dropped.

Two disjoint case sets, each with its own non-circular expected-verdict rule (the oracle
comes from the generation parameters, never from running the verifier and recording its
output as golden):

- **Matrix A** = in-universe presentation (`tick_catalog=catalog`, `font_family=arial` where
  applicable) x `color_style` x `defect`. Expected verdict is a pure function of `defect`:
  `pass` if none, `fail` with the specific finding type if injected. Claim: zero
  abstentions, zero wrong verdicts.
- **Set B** = any case with one out-of-universe axis flipped, crossed with `defect in
  {none, wrong_bar_height}` to test masking. Expected verdict is always `needs_review`
  regardless of `defect` — this is the concrete test that an injected defect gets masked by
  degraded evidence rather than silently passing or being reported as a specific typed
  failure.

## Why exhaustive enumeration, not a t-way algorithm

Matrix A is `color_style(2) x defect(3)` per renderer = 6 cases/renderer, 12 total. Set B is
6 more (2 renderers x `off_catalog_ticks` x 2 defects, plus matplotlib x `non_arial_font` x
2 defects). At this size, full cross-product enumeration *is* a complete (exhaustive, i.e.
maximal-strength) covering array — building a t-way reduction algorithm would add
complexity with no coverage benefit. This also empirically confirms the advisor's
prediction: **Matrix A is thin** (a single in-universe point per renderer, crossed with only
color and defect) — most of today's declared variation lives in Set B, i.e. in documenting
the abstention boundary, not in decided-verdict coverage. A real t-way generator becomes
worth building once axis count/levels grow (e.g. adding a degradation axis); deferred as
future work rather than built speculatively now.

## Implementation

- `covering_array_cases()` and `build_covering_array_dataset()` in `generate_dataset.py`
  build the 18 cases and a checksum-frozen `manifest.json` (same pattern as
  `build_realworld_pilot_dataset`), including required `provenance` fields
  (`source_type`, `license`, `retrieved_at`) so `verify_dataset_manifest` accepts it.
  `validation.py`'s manifest checker gained one line enforcing
  `chart-v2-covering-v1` case count `== 18`.
- New CLI command `generate-chart-covering-dataset` (default output
  `datasets/charts/chart-v2-covering-v1`). Validation reuses the existing generic
  `run-validation --dataset <path>` command unchanged — no new validation code was needed
  because `kind="golden"/"mutated"` and `expected_finding_types=[]` already express exactly
  Matrix A / Set B's oracle semantics in `summarize_validation_results_for_cases`.
- Regression test `test_covering_array_matrix_a_and_set_b_oracle_holds` in
  `test_end_to_end.py` asserts the full oracle: 18 cases, 4 golden, 8 typed-mutated (8/8
  hits), 6 ambiguous (6/6 guarded to `needs_review`), 0 unsupported passes, 0 verdict
  mismatches, and explicitly checks every `covering-b-*` case actually resolves to
  `needs_review` (the masking claim, checked per-case, not just via the aggregate guard
  rate).

## Measured result (frozen dataset, session 2026-07-11)

Running `run-validation` against the generated dataset: `total_cases=18`,
`golden_cases=4`, `typed_mutated_cases=8`, `typed_mutated_hits=8` (1.0 recall),
`ambiguous_cases=6`, `ambiguous_guard_rate=1.0`, `false_unsupported_passes=0`,
`verdict_mismatches=0`. Every Set B case (including the two where `wrong_bar_height` was
injected under `off_catalog_ticks` or `non_arial_font`) resolved to `needs_review`, not a
wrong `pass` or an unmasked `fail` — confirming the masking behavior the advisor flagged as
the design's central risk. Unified suite: 159/159 (158 prior + 1 new).

## Honest scope

- This is a chart-v2-only, small, hand-enumerated array — not a cross-vertical framework
  and not a general t-way covering-array generator. Per CLAUDE.md's narrow-scope rule, no
  such generator or abstraction was built since the current axis count doesn't need one.
- Layout-mismatch is a known, explicitly undocumented-until-now gap in this dataset's
  coverage (see "Scoped out" above), not silently missing.
- No continuous-nuisance axis (blur/downscale/JPEG/label-length) is included yet — that is
  Latin Hypercube Sampling territory per the layered-sampling design and is separate future
  work, likely folded into the degradation-harness roadmap item instead of this dataset.
