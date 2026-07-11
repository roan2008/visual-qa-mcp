---
name: knowledge-accuracy-and-synthetic-data-roadmap
description: Honest accuracy assessment plus roadmap ideas for selective-prediction accuracy and synthetic data coverage without external datasets
metadata:
  type: knowledge
  status: current
  last_updated: 2026-07-11
---

## Renderer crutch-stripping experiment (session 2026-07-11, post-circuit-v1)

Ran the "cheapest honest experiment" an advisor review recommended in place of building a
new style-pack/renderer-adapter abstraction from scratch: the existing
`chart-v2-realworld-pilot` Matplotlib cases already prove rasterizer-independence
(Pillow vs. Matplotlib), but every one of them is still tuned to the extractor — matched
`ChartLayout` pixel geometry, the validated Arial font family, and tick values drawn
from the template reader's fixed multiples-of-5 catalog. `experiments/renderer_strip_test.py`
(throwaway, not a dataset or test-suite addition) stripped each crutch independently
against an otherwise-identical golden 3-bar chart:

1. **Baseline** (matched layout, Arial, catalog ticks `[0,25,50,75,100]`): `pass`, as expected —
   reproduces the existing pilot claim.
2. **Off-catalog tick values** (`[0,22,47,83,100]`, not multiples of 5): tick reader returns
   `None` for every tick, axis mapping fails to resolve, verdict `needs_review`. This is the
   template-catalog wall from the "Honest accuracy assessment" section above, now demonstrated
   directly rather than only asserted — and confirmed **safe**: zero unsupported passes, zero
   wrong values, clean abstention.
3. **Unmatched layout** (Matplotlib's own `tight_layout()` placement, not `ChartLayout`-matched):
   **raised `ValueError: Coordinate 'lower' is less than 'upper'`** instead of degrading to
   `needs_review`. Root cause: `chart_extractor.py`'s bar-label crop box
   (`ChartLayout.label_box()`) is computed from a fixed offset with no bounds check against the
   actual image; when the real layout diverges enough, the box's top coordinate exceeds
   `image.height` while `_apply_postprocess`'s clamp only bounds it from below, producing an
   inverted crop rectangle. This is a genuine robustness gap, not a test-harness artifact — a
   Matplotlib chart using default `tight_layout()` (an extremely common real-world default) would
   crash the extractor rather than safely abstain. **Fixed** in the same session: the crop box is
   now clamped to image bounds on all four sides before cropping, and a degenerate
   (post-clamp-empty) box is treated as "no label match" rather than raising. Regression test:
   `test_bar_label_crop_out_of_bounds_degrades_instead_of_raising` in
   `test_extractor_hardening.py`. Verified: 158/158 tests pass (157 prior + 1 new); no change to
   any existing controlled/noisy/pilot dataset metric (fix only activates on crop boxes that were
   previously unreachable without crashing).
4. **Non-Arial font** (DejaVu Serif instead of Arial, matched layout, catalog ticks): tick reading
   still succeeded (the numeric glyph templates are somewhat font-tolerant), but x-axis category
   label matching failed (`missing_bar_label`), correctly degrading to `needs_review` rather than
   a wrong or silent value.

**Net result**: the safety property held under every stripped condition once the crash bug was
fixed — three of four conditions degrade to `needs_review` exactly as designed, and the fourth
(matched baseline) still passes. But the experiment also reclassifies the bottleneck: it is no
longer just "no validated OCR" in the abstract — it is now a quantified, reproducible wall (any
non-catalog tick value on any renderer fails closed) plus a fixed robustness bug that would have
caused real crashes on ordinary Matplotlib-default output. This is exactly the kind of "coverage
per stratum" measurement the roadmap called for, at negligible cost (no new dataset infra, one
throwaway script, one afternoon).

**Not yet done**: the font/layout findings above were not turned into permanent dataset cases or
CI-enforced coverage; the OCR backend is still unvalidated; and no independently authored (not
tool-rendered) images have been tried. The renderer-adapter abstraction (build-order item 1) is
now lower priority than initially planned, since the Matplotlib path already exists and this
experiment got most of its diagnostic value without building it.

> **Update 2026-07-11**: an external deep-research pass validated, refined, and in places
> corrected the ideas below against published literature. See
> [knowledge-synthetic-coverage-deep-research](knowledge-synthetic-coverage-deep-research.md)
> for the ingested findings — notably: layered sampling (stratified + covering arrays + LHS)
> replaces plain Latin-hypercube sampling as the recommended design; the project direction is
> confirmed as **synthetic-only** (declared-universe coverage with held-out splits, not
> independently authored images); and the recommended top-3 investments are input model +
> covering arrays, failure-mining loop, and a ground-truth-preserving degradation harness.

# Accuracy Assessment and Synthetic-Data Roadmap

Captured from a design discussion (session 2026-07-11, post-session-21e). Not yet
implemented — this is strategy/direction, not a delivered feature. Treat action items
here as candidate entries for `wiki/next-steps.md` "Suggested Next Work" once picked up.

## Honest accuracy assessment (as of session 21e)

- All five verticals report ~100% typed-defect recall and 0 unsupported passes, but
  this is measured almost entirely on datasets rendered by the *same* Pillow generator
  code that ships next to each extractor (e.g. `chart_generator.py` beside
  `chart_extractor.py`). This proves the Spec -> ClaimGraph -> EvidenceGraph -> Rules
  architecture works end-to-end; it does not measure accuracy on images the system
  did not draw itself.
- The one external-ish signal is `chart-v2-realworld-pilot`
  ([impl-chart-v2-noisy-realworld-pilot](impl-chart-v2-noisy-realworld-pilot.md)):
  typed hits `6/7` (0.86), tick readability 0.94, label readability 0.95 — still
  locally rendered Matplotlib plus one frozen World Bank snapshot, not scraped
  publisher images, and only exists for one of five verticals.
- What genuinely holds up: the safety property. Zero false unsupported passes across
  every controlled/noisy track; ambiguity consistently degrades to `needs_review`
  rather than guessing. The failure mode today is "asks a human unnecessarily," not
  "silently approves a wrong diagram" — the correct asymmetry for a QA tool.
- Bottleneck is shared across all five verticals, not per-vertical: (1) no validated
  OCR — every text-reading path uses small fixed template catalogs (numeric ticks, 8
  arrow labels, 6 flowchart labels, 6 dimension labels); (2) no independently authored
  images; (3) most verticals identify elements via spec-declared colors, which
  real-world images won't provide.

## Reframing "accuracy": selective prediction

A verifier is not a classifier — it can emit `needs_review` instead of answering. The
actual target is: **on every case where the tool emits `pass` or `fail`, it should be
~100% right; residual uncertainty routes to `needs_review`.** Since the rules layer is
deterministic, verdict correctness reduces entirely to whether the extracted evidence
is trustworthy. All ideas below are ways to estimate extraction trustworthiness
without new external data. Add a **coverage** metric (fraction decided vs. abstained)
alongside accuracy-on-decided to every future validation summary — "100% accurate at
80% coverage on family X" is the kind of bounded claim this project's Claim Discipline
section expects.

## Techniques to raise accuracy-on-decided toward ~100% (no external data needed)

1. **Round-trip re-rendering (analysis-by-synthesis)** — highest priority. Re-render
   an image from extracted evidence using the vertical's own generator, then compare
   structurally (bar extents, tick positions, arrow endpoints) against the input. A
   misread rarely survives reprojection. All five generators already exist; this is
   mostly plumbing plus a structural comparator. Prototype on chart-v2 first (most
   mature generator/extractor pair).
2. **Ensemble-of-extractions with mandatory agreement** — metamorphic copies (1x /
   1.5x upscale / brightness shift; true content is invariant, bugs usually aren't),
   parameter jitter (2-3 threshold settings; disagreement = near a cliff), redundant
   readers (template catalog vs. validated OCR must agree). Disagreement anywhere ->
   `needs_review`.
3. **Exploit internal redundancy already in the image** — axis tick linear-fit
   residual bounds, gridline-vs-tick cross-checks, bar-baseline-vs-zero-line
   consistency, arrow-anchor-on-object-boundary consistency. Never trust a single
   measurement when the image encodes the same fact twice.
4. **VLM as a one-directional tripwire, never a judge** — consistent with the
   project's existing rule against VLM-as-sole-judge. A VLM check may only downgrade
   a deterministic `pass` to `needs_review` on disagreement; it can never cause a pass
   or fail. Strictly reduces false passes, can't inject hallucinated verdicts.

## Synthesized data ideas for broad coverage without external datasets

Strategic framing: the real-world target distribution (AI-generated + tool-generated
educational visuals) is itself much narrower than "all images in the world" — it's
dominated by a handful of renderer house styles (Matplotlib, Excel/Sheets, ggplot2,
plotly, Chart.js/D3, seaborn, PowerPoint, TikZ, Mermaid/Graphviz) plus AI image
generators. Spanning that space synthetically covers most of the actual target without
scraping.

1. **Factor generation into orthogonal axes** and sample the cross product
   (stratified/Latin hypercube, not enumeration): content (value ranges, number
   formats, label lengths, topology), style (fonts, palettes incl. colorblind-safe and
   dark mode, line widths, legends, aspect ratio), renderer (Pillow, Matplotlib,
   SVG->raster, headless-browser Chart.js), degradation (JPEG, rescale,
   screenshot-of-screenshot, PDF print-then-rasterize, simulated photo-of-screen with
   perspective warp/glare/sensor noise). Every degradation must also transform the
   ground truth, or labels rot.
2. **Grammar-based structural generation** per vertical (node/branch/loop patterns for
   flowcharts, force configurations for free-body diagrams) to get structural novelty
   that parameter jitter alone can't produce.
3. **Coverage-guided and adversarial generation** — highest-leverage idea. Instrument
   extractors to track which evidence branches/outcomes are exercised; bias new
   generation toward untested combinations. Boundary/magnitude sweeps (e.g. point
   displaced 2.9%/3.0%/3.1% of axis range) replace N/N hand-picked-mutation claims
   with measured per-defect-class sensitivity curves. Adversarial search uses the
   consensus/round-trip machinery above as a fitness function: perturb generation
   params, keep cases where the ensemble disagrees or round-trip barely passes, turn
   each into a regression case — self-play that converges on the actual failure
   surface instead of a guessed one.
4. **Defect taxonomy x magnitude sweep** — turn `docs/problem-map.md` into a matrix
   (defect class x vertical x magnitude x style) instead of ~7 hand-picked mutations
   per dataset, to prove detection of a *class* down to a measured threshold.
5. **LLM-generated realistic content, deterministically rendered** — use an LLM only
   to write plausible spec content (real subject matter, messy realistic values, long
   colliding labels); rendering stays deterministic so ground truth stays exact. Fixes
   the current toy-text distribution (labels A-F, multiples of 5) cheaply and safely.
6. **Report coverage per stratum**, not one global number (recall/abstention rate per
   renderer x style x degradation x defect class) — a global "99.4%" can hide "62% on
   dark-mode JPEG."

## Honest asymptote

This approach cannot cover hand-drawn sketches, scanned legacy figures, or genuinely
novel bespoke scientific graphics — the correct behavior there is the existing
`needs_review` abstention, not a stretch claim. Realistic end-state: near-total
coverage of tool-generated and AI-generated visuals (the actual product domain), with
zero silent errors on the long tail.

## Suggested build order (not yet started)

1. Style-pack + renderer-adapter abstraction over existing generators (one spec, N
   renderers x M styles) — foundation for everything else.
2. Degradation pipeline with ground-truth-transforming postprocessing.
3. Boundary/magnitude sweeps on existing defect classes (cheap; produces sensitivity
   curves immediately, no new infra).
4. Round-trip re-rendering check, starting with chart-v2.
5. Coverage-guided / adversarial generation, once round-trip/consensus checks exist to
   serve as the oracle.
