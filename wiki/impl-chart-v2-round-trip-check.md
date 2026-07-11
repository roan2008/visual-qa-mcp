---
name: impl-chart-v2-round-trip-check
description: Additive chart-v2 round-trip re-rendering accuracy check and measured pixel-delta distribution
metadata:
  type: implementation
  status: current
  last_updated: 2026-07-11
---

# Chart-v2 Round-Trip Re-Rendering Check

## Scope and origin

First concrete step out of [knowledge-accuracy-and-synthetic-data-roadmap](knowledge-accuracy-and-synthetic-data-roadmap.md),
chosen over circuit-v1 (new vertical, larger surface) and real-world image/OCR sourcing
(blocked on external inputs) because it needs no external data and is on the critical path
for later coverage-guided/adversarial generation work. [source: session 2026-07-11 advisor-gated plan]

This is a purely **additive, non-blocking** evidence layer on `chart-v2` only. It does not
change `VisualQaReport.verdict`/`findings` for any existing dataset case, does not set any
tolerance/threshold, and is not wired into `chart_rules.py`. Tolerance-setting and
verdict-gating are explicitly deferred follow-up work once real distributions have been
observed (see Measured Distribution below).

## Design: why the naive version doesn't work

A naive round-trip — re-render from extracted bar values using the extractor's own inferred
axis mapping, then re-extract and compare values — is circular: it encodes and decodes
through the same (possibly wrong) mapping and would trivially match itself.

The implemented version instead compares two **independently derived** pixel measurements:
(a) the bar pixel geometry the extractor directly measured on the **original** image,
already stored unmodified in `EvidenceGraph.bars[i].bbox` (chart_extractor.py's
`_find_bar_regions` output flows straight into `ExtractedBar.bbox` with no transform), against
(b) freshly measured bar pixel geometry (via the same `_find_bar_regions`/`detect_plot_area`
primitives) on a **freshly rendered** image built from the extracted values + inferred axis
config via `chart_generator.render_chart_image`. This isolates self-consistency bugs between
the extractor's inverse axis-mapping and the generator's forward axis-mapping (rounding,
baseline miscalculation, bar-order scrambling) without being tautological. It does **not**
catch OCR tick misreads — an accepted, documented bound, not a gap to be closed by this check.

## Implementation

- `chart_round_trip.py` (new module): `measure_bar_geometry`, `build_round_trip_inputs`
  (EvidenceGraph -> generator inputs; returns `None` rather than guessing if
  `y_axis.mapping is None` or any bar `value is None`), `render_round_trip_image`,
  `compare_bar_geometry` (matches bars by index/order, not category text, to avoid
  compounding OCR-match noise into a check meant to be OCR-independent), `run_round_trip_check`
  (never raises — wraps everything in try/except, returns `status="error"` on failure since
  this is diagnostic-only and must not break the main verification path).
- `contracts.py`: new `BarGeometryDelta`/`RoundTripComparison` dataclasses; optional
  `round_trip: RoundTripComparison | None` field on `VerificationResult`, following the
  existing `primitive_graph` additive-field pattern exactly (omit-if-None in `to_dict()`).
- `service.py::run_chart_verification`: round-trip runs as a fifth step, strictly **after**
  `report = run_chart_claims(...)` is already finalized — there is no code path by which
  round-trip output can influence `report.verdict`. New `include_round_trip: bool = True`
  parameter allows opting out (e.g. for latency-sensitive callers).
- `write_verification_artifacts`: round-trip image/JSON persistence is opt-in via
  `persist_round_trip: bool = False` (default off), so no existing dataset directory gains
  new files unless explicitly requested — this is what keeps `chart-v2-realworld-pilot`
  checksums untouched.
- `validation.py::summarize_chart_round_trip_results` + CLI
  `run-chart-round-trip-validation --dataset <path> [--backend ...]`: read-only, pure
  measurement summary (min/max/mean/median/p90 pixel deltas, broken down by axis_mode and
  golden/mutated, plus `skipped_by_status` counts). No pass/fail field anywhere in the output.

## Tests

`test_chart_round_trip.py` (9 tests): adapter unit tests, `measure_bar_geometry` on a
known-rendered fixture, end-to-end golden-case check, `skipped_no_axis_mapping` path,
never-raises-on-render-failure path, bar-count-mismatch path, and the most important test —
`report.to_dict()` is byte-identical whether `include_round_trip` is `True` or `False`,
proving the additive/non-blocking guarantee the whole design rests on.

## Measured distribution (2026-07-11, read-only run, no dataset mutation)

Ran `run-chart-round-trip-validation` against all three existing chart-v2 datasets:

| dataset | total | evaluable | skipped (no axis mapping) | top_y p90 / max (px) | height p90 / max (px) |
|---|---|---|---|---|---|
| chart-v2 (controlled, 24 cases) | 24 | 17 | 7 | 6.0 / 22.0 | 6.0 / 21.0 |
| chart-v2-noisy (6 cases) | 6 | 4 | 2 | 6.0 / 13.0 | 11.0 / 16.0 |
| chart-v2-realworld-pilot (24 cases, checksum-frozen) | 24 | 18 | 6 | 1.0 / 29.0 | 1.0 / 33.0 |

Observations:

- Roughly 25-33% of cases across all three datasets are skipped with
  `skipped_no_axis_mapping` — these are cases where `y_axis.mapping` is `None` (backend
  degraded to `needs_review` before a mapping was derivable, e.g. `optional_ocr` backend
  cases or deliberately ambiguous mutated cases). This is expected: the round-trip check can
  only run where the extractor already committed to a mapping.
- Median delta is 0-1px in every dataset; most cases round-trip near-exactly. A handful of
  outliers (max 22-33px) exist in each dataset and are worth inspecting before any tolerance
  is set — they were not individually triaged in this landing (out of scope per the
  additive-only definition of done).
- This is a first empirical measurement, not a validated accuracy claim. No threshold or
  verdict-gating has been set from these numbers.

## Bounds

- `chart-v2` only; not extended to arrow/geometry/coordinate/flowchart in this landing.
- Does not catch OCR tick-label misreads (round-trip renders using the same tick values the
  extractor already read).
- No investigation yet into why ~25-33% of cases lack a mapping, or what the outlier cases
  specifically got wrong — flagged as follow-up, not resolved here.
- No tolerance/threshold/verdict-gating — this is a measurement-only landing.

## Outlier triage and layout-carrying fix (2026-07-11, session 23)

Triaged the four largest outliers by inspecting each case's `metadata.json` and re-running
`run_round_trip_check` directly with full bar-delta detail:

- `golden-02` (22px), `noisy-golden-01` (16px), `rw-public-golden-06` (33px) all had non-default
  `render_options.layout_overrides` (custom `width`/`height`/`margin_left`/`axis_label_box`)
  in their original render. `build_round_trip_inputs` was rendering the round-trip image with
  generator **defaults** regardless, so the round-trip plot area had different margins/height
  than the original — a pure layout artifact, not an extraction bug. Confirmed by inspecting
  `bar_deltas`: `bottom_y_delta_px` was consistently near zero (baseline agreed) while
  `top_y_delta_px` scaled with how far the case's layout diverged from the generator default.
- `mutated-07` (19px, `defect_type: "shifted_scale"`) is different: `render_options` is `{}`
  (default layout both times), but the case is deliberately rendered with a true `bar_axis` of
  `0-80` while its tick labels are relabeled to display `0/25/50/75/100` (see
  `generate_dataset.py:383-394`). The extractor correctly reads the (fake) labels and infers a
  `0-75` mapping; the round-trip then re-renders using that `0-75` mapping, which necessarily
  produces different bar heights than the original `0-80`-positioned bars. This is the round-trip
  check correctly detecting the same scale inconsistency the deterministic
  `chart_value_mismatch` rule already catches independently — a corroborating signal, not a bug.

**Fix applied**: `chart_round_trip.py` gained `geometry_render_metadata()`, a whitelist filter
(`layout_overrides`, `tick_font_size`, `x_label_font_size` — geometry-affecting keys only, not
`postprocess`/noise knobs) over the original case's `render_options`. `build_round_trip_inputs`,
`render_round_trip_image`, and `run_round_trip_check` now accept an optional `render_metadata`
carrying these keys through to `render_chart_image`, so the round-trip render reproduces the
original's plot-area geometry instead of silently diffing against generator defaults.
`service.py::run_chart_verification` reads `render_options` from `metadata_path` and passes the
filtered dict through; `write_verification_artifacts`'s persisted `round_trip.png` does the same.

**Re-measured distribution after the fix** (same three datasets, re-run read-only, zero dataset
mutations):

| dataset | top_y p90 / max (px) | height p90 / max (px) |
|---|---|---|
| chart-v2 (24 cases, 17 evaluable) | 1.0 / 19.0 | 1.0 / 19.0 |
| chart-v2-noisy (6 cases, 4 evaluable) | 1.0 / 2.0 | 1.0 / 2.0 |
| chart-v2-realworld-pilot (24 cases, 18 evaluable) | 1.0 / 1.0 | 1.0 / 1.0 |

p90 dropped from 6.0px to 1.0px in every dataset; max dropped from 22-33px to 1-2px everywhere
except `mutated-07`'s expected 19px (the one case designed to disagree). All 150 tests
(including the verdict-unaffected regression test) still pass; no dataset files were modified.

**Tolerance decision**: not setting a verdict-gating tolerance yet. The remaining outlier is a
known, intentional defect case rather than unexplained noise, and the deterministic
`chart_value_mismatch` rule already catches it independently — round-trip gating would be
redundant here, not additive signal. Revisit if/when round-trip is used as a standalone
diagnostic (e.g. a future dashboard) rather than feeding `verdict`.

## Follow-up (deferred, not started)

- Extend the same technique (including the layout-carrying fix) to
  arrow-v1/geometry-v1/coordinate-graph-v1/flowchart-v1 if useful.
- If a future case wants round-trip to *catch* a scale-shift defect like `mutated-07` on its
  own (not just corroborate an existing rule), that would require deliberately deciding a
  tolerance and wiring `round_trip` into `chart_rules.py` — out of scope for this additive
  landing.
