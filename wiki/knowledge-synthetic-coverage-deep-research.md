---
name: knowledge-synthetic-coverage-deep-research
description: Ingested deep-research findings on synthetic-only coverage strategy, sampling design, oracles, degradation, and honest reporting
metadata:
  type: knowledge
  status: current
  last_updated: 2026-07-11
---

# Deep-Research Findings: Synthetic-Only Coverage Strategy

Ingested from `research/deep-research-report-1.md` (external deep-research report, Thai,
2026-07-11), which answered the eight research questions posed for the synthetic-data
strategy. This page condenses the actionable conclusions; the source file holds the full
argument. It extends [knowledge-accuracy-and-synthetic-data-roadmap](knowledge-accuracy-and-synthetic-data-roadmap.md).

**Source-integrity caveat**: the report's own literature citations are opaque
tool-generated tokens (`citeturn...`), so individual paper claims below are cited to the
report file, not to verified primary sources. Treat named-paper claims as
[UNVERIFIED - human review needed] until spot-checked against the actual papers if any
becomes load-bearing for a readiness claim.

## 1. Synthetic-only validity: partially supported, not proven

- Literature (Donut/SynthDoG, DePlot, GenPlot, SBSFigures, DocCreator) supports synthetic
  data working well when the generator covers layout/font/style/degradation grammar
  broadly, but no work proves "synthetic-only = real-world coverage"
  [source: research/deep-research-report-1.md:5-11].
- Recommended reframing: not "synthetic replaces the real world" but "synthetic covers the
  declared family of real generators we intend to support." Validate with
  **renderer-held-out / style-held-out / content-held-out / degradation-held-out** splits
  instead of pooling everything [source: research/deep-research-report-1.md:9].
- Residual gaps that never closed in the literature: adjacent text, leader lines/arrows,
  tiny text, camera distortions, figure types with no latent tabular representation —
  the last one is *higher* risk for our free-body/mechanical/flowchart/circuit verticals
  than for bar charts [source: research/deep-research-report-1.md:11].

## 2. Sampling design: three layers, not one method

- NIST combinatorial testing: most software failures involve interactions of few
  parameters; 3-way coverage detects ~90%+ of bugs in many systems; practical t range is
  2–6 [source: research/deep-research-report-1.md:15]. Direct evidence that this holds
  for deterministic *visual extractors* is thin — honest position: 2-way baseline, 3-way
  starting sweet spot, mixed-strength 4-way only on suspected high-coupling factor groups
  (e.g. `renderer x font x number-format x export-DPI`)
  [source: research/deep-research-report-1.md:17].
- Layered sampler [source: research/deep-research-report-1.md:19]:
  1. **Stratified** over renderer family x vertical (guarantees every stratum present).
  2. **t-way covering arrays** (NIST ACTS line) over discrete axes: renderer, chart type,
     legend mode, tick format, locale, export backend, degradation family.
  3. **Latin hypercube** only for continuous nuisance variables: blur radius, JPEG
     quality, downscale factor, line thickness, label-length percentile.
- Warning: LHS as the *primary* sampler over discrete axes misses dangerous discrete
  tuples while looking numerically "covered" [source: research/deep-research-report-1.md:21].

## 3. Coverage measurement: coverage ledger, not one number

- Report coverage in three tiers [source: research/deep-research-report-1.md:27]:
  (a) declared generation-space coverage (per-stratum n, interaction coverage level),
  (b) behavioral/input-partition adequacy (boundary bins, equivalence classes, rare
  formats, ambiguous layouts), (c) implementation branch coverage as a proxy only, never
  the headline metric.
- Code coverage has only low-to-moderate correlation with fault detection; neuron-style
  coverage metrics are a documented negative example
  [source: research/deep-research-report-1.md:25].
- Better fault-correlated supplement for our rule layer: **rule mutations** (flip an
  inequality, disable a tolerance check, remove a fallback) and measure how many the
  test suite catches [source: research/deep-research-report-1.md:29].
- Per-vertical "coverage ledger": stratum coverage, t-way interaction coverage, boundary
  coverage, branch/rule-mutation coverage, discovered-failure coverage; use NIST
  coverage-difference to describe what a release adds
  [source: research/deep-research-report-1.md:31].

## 4. Failure mining: boundary-first search with exact oracles

- With cheap exact oracles (renderer ground truth, round-trip, invariances, ensemble
  disagreement) we are better positioned than most fuzzing work; do NOT import
  DeepHunter-style code-coverage-guided infrastructure — search over semantic generation
  parameters instead [source: research/deep-research-report-1.md:39,45].
- Five-step loop [source: research/deep-research-report-1.md:43]:
  `covering-array seeds -> boundary sweeps -> local search around low-margin cases ->
  delta-debug minimization -> root-cause clustering into new regression strata`.
- Metamorphic relations (rescale, brightness, export/import idempotence, re-render
  equivalence) are failure-surface *mining tools*, not correctness judges
  [source: research/deep-research-report-1.md:41].
- Warning: never add raw failure seeds directly to the regression suite — minimize,
  cluster, and abstract into a named stratum first, or the suite overfits to found bugs
  [source: research/deep-research-report-1.md:45].

## 5. Degradation: four delivery paths, ground truth transformed alongside

- Four pipelines, not one noise bucket [source: research/deep-research-report-1.md:51]:
  digital export (AA, compositing, downscale, JPEG/WebP); office reproduction
  (print-scan, photocopy, toner, bleed-through — Augraphy/DocCreator territory); camera
  capture (perspective, curl, blur, shading, glare); screen-photo/chat (moire,
  resize/recompress chains).
- Some degradations change ground-truth geometry (rotation, perspective, warps). Keep the
  transformation stack a first-class object: affine/homography transforms coordinates
  directly; non-linear warps carry a dense displacement field applied to every
  point/line/bbox [source: research/deep-research-report-1.md:53-55].
- Warning: app-specific compression signatures (LINE/WhatsApp) have no validated public
  simulators — if built, label as *engineering proxy*
  [source: research/deep-research-report-1.md:57].
- Our current blur/downscale/JPEG tracks do NOT represent the real degradation space for
  thin lines, small text, arrowheads [source: research/deep-research-report-1.md:57].

## 6. LLM content generation: contract, not prompt

- LLM stays at the semantic content layer only (tables, labels, units, locales, topics);
  everything after passes schema validation and the deterministic renderer
  [source: research/deep-research-report-1.md:63].
- Build a "content realism contract" with enforced fields: numeric distribution class,
  round/non-round ratio, sign patterns, decimals, locale separators, label-length
  percentiles, collision stress, near-tie frequency, special tokens (minus, scientific
  notation, percent, SI prefixes) — validated deterministically before rendering
  [source: research/deep-research-report-1.md:65].
- No published ablation isolates which realism factor adds difficulty — defining that
  taxonomy would be an original contribution, not settled literature
  [source: research/deep-research-report-1.md:67].

## 7. Honest reporting for selective prediction

- Always report three lines per stratum: **coverage** (fraction decided, Wilson interval),
  **selective risk** (error rate on decided cases only, exact binomial/Wilson), and
  **abstention profile** (needs_review share with dominant rule-level reasons)
  [source: research/deep-research-report-1.md:73-75].
- With zero observed failures, report the failure-rate upper bound: rule-of-three `3/n`
  or exact Clopper-Pearson — e.g. "0/87 failures on decided cases; 95% upper bound = X"
  [source: research/deep-research-report-1.md:73-75].
- Risk-coverage curve + AURC as summary; never as a replacement for the per-stratum
  table. Never write bare "100% accuracy" with small n and heavy abstention
  [source: research/deep-research-report-1.md:77].

## 8. Structural generation: grammar first, layout second

- Generate from a typed graph/constraint system, then deterministic layout/render; the
  grammar's production history *is* the exact structural ground truth
  [source: research/deep-research-report-1.md:83].
- Per vertical: attributed graph grammar for flowcharts (start/end, decision, fork/join,
  loop-back + reachability constraints); netlist grammar + motif library for circuits
  (series/parallel, bridge, ladder); parametric sketch grammar for mechanical plates
  (hole arrays, slots, dimension chains) [source: research/deep-research-report-1.md:83].
- No off-the-shelf framework exists for this + topological coverage metrics; define our
  own coverage taxonomy openly: grammar-rule, motif, degree-pattern, path-length bins,
  symmetry bins, crossing/planarity bins, constraint-boundary coverage
  [source: research/deep-research-report-1.md:85-87].

## Recommended top-3 investments (coverage-per-effort, solo developer)

[source: research/deep-research-report-1.md:89-90]

1. **Formal input model + stratified registry + mixed-strength covering arrays** — turns
   the test suite from "sampled informally" into "declared coverage."
2. **Failure-mining loop** (boundary sweeps, adaptive local search, delta debugging,
   root-cause clustering) — highest payoff given cheap exact oracles.
3. **Ground-truth-preserving degradation harness** across the four delivery paths.

## Techniques to explicitly skip

[source: research/deep-research-report-1.md:92]

- Neuron/DNN-style coverage metrics as design axis.
- LHS as the primary sampler for the whole space.
- VLM/LLM as primary correctness judge (already project law).
- Training-centric synthetic-data recipes (only the coverage/diversity methodology
  transfers, not the data-scaling recipe).
- Unvalidated app-specific degradation simulation presented as validated.

## Bottom line

The literature strongly supports: (1) synthetic generation works if the generator family
and held-out styles are controlled systematically, (2) combinatorial coverage is the most
transferable coverage backbone, (3) cheap exact oracles give our failure mining more
leverage than most AI-testing work has. It does NOT license "synthetic-only = real-world
coverage" as an automatic claim; the honest strategy is to declare the supported universe
(renderer families, styles, degradation paths, topology classes) and measure
coverage/risk statistically against that declared universe
[source: research/deep-research-report-1.md:94].
