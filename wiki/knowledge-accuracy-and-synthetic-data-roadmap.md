---
name: knowledge-accuracy-and-synthetic-data-roadmap
description: Honest accuracy assessment plus roadmap ideas for selective-prediction accuracy and synthetic data coverage without external datasets
metadata:
  type: knowledge
  status: current
  last_updated: 2026-07-11
---

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
