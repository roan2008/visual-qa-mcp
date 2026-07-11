---
name: next-steps
description: Current priority and queued follow-up work
metadata:
  type: reference
  status: current
  last_updated: 2026-07-11
---

# Next Steps

## Current Priority

### 2026-07-11 session 28 (cont.) - chart-v2 covering-array input model implemented; second research report found unread

Implemented next-steps item 1 (see item 1 below and
`wiki/impl-chart-v2-covering-array-input-model.md`). While working, found a second,
untracked deep-research file at `research/synthetic-data-coverage-report.md` (dated
2026-07-12, not yet ingested, not produced by this agent this session) that uses named,
checkable sources (FigureQA, DVQA, ChartQA, DePlot, etc.) rather than the first report's
opaque `citeturn` tokens — likely higher source-integrity value. **Not yet read in full or
ingested.** Next session should read it and decide whether it supersedes or extends
`knowledge-synthetic-coverage-deep-research.md`.

### 2026-07-11 session 28 - COMPLETE: synthetic-only decision confirmed + deep-research ingest

The user confirmed a previously made decision: validation images are **100% synthetic**;
independently authored/publisher images are off-strategy (old Suggested Next Work item 1 is
redirected accordingly). An external deep-research report was commissioned (prompt covering 8
research questions) and delivered at `research/deep-research-report-1.md`; findings are ingested
in `wiki/knowledge-synthetic-coverage-deep-research.md`. Headline conclusions: synthetic-only is
literature-supported as *declared-universe* coverage (held-out renderer/style/content/degradation
splits), not as automatic real-world equivalence; layered sampling (stratified + t-way covering
arrays + LHS for continuous nuisances) replaces plain LHS; top-3 investments are (1) formal input
model + covering arrays, (2) failure-mining loop, (3) ground-truth-preserving degradation harness.

### 2026-07-11 session 27 - COMPLETE: remote setup + renderer crutch-stripping experiment

Closed the operational risk item (uncommitted circuit-v1a/v1b work, no GitHub remote) and ran
the first concrete external-validity experiment from the accuracy roadmap. See
`wiki/project-log.md` session 27 and `wiki/knowledge-accuracy-and-synthetic-data-roadmap.md`
"Renderer crutch-stripping experiment" for full detail.

**Decision going forward: freeze the vertical count at six** (chart-v2, arrow-v1, geometry-v1,
coordinate-graph-v1, flowchart-v1, circuit-v1a/v1b). The architecture-generalizes question is
answered; the priority is now closing external validity, not proving generalization again with
a seventh vertical.

Key result: the Matplotlib renderer path was already less crutch-dependent than assumed
(rasterizer-independence was already proven via the pilot dataset), but stripping the remaining
crutches (matched layout, Arial font, catalog tick values) found and fixed a real crash-safety
bug — an unmatched Matplotlib `tight_layout()` layout previously raised an unhandled
`ValueError` instead of degrading to `needs_review`. Fixed and regression-tested (158/158).
Off-catalog tick values and non-Arial fonts both correctly degrade to `needs_review` (no
unsupported passes) — the template-catalog wall is now a measured, reproducible finding
instead of an assertion.

Repo is now at `https://github.com/roan2008/visual-qa-mcp` (origin, `master` pushed and tracked).

### 2026-07-11 session 26 - COMPLETE: circuit-v1a and circuit-v1b

Both separately gated circuit milestones are complete within their controlled Pillow-rendered scope.
`circuit-v1a` validates orthogonal, non-crossing battery/resistor/lamp series loops across 11 cases
(4/4 typed, 5/5 ambiguity, 2/2 golden, terminal netlists 6/6). `circuit-v1b` adds explicit
junction-dot evidence, arbitrary-degree nets, simple-parallel and one bounded series-parallel family
across 14 cases (7/7 typed, 3/3 ambiguity, 4/4 golden, terminal netlists 11/11, junction counts 11/11).
Both record zero unsupported passes, golden non-passes, and verdict mismatches. CLI/MCP/schema/artifact
coverage is executable; the unified suite passes 157/157.

Next gate: choose hardening rather than silently broadening the claim. Candidate work is a
checksum-frozen noisy circuit track, independently authored holdout diagrams, more complete-evidence
branch mutations, or a `PrimitiveEvidenceGraph` circuit adapter. Crossings, arbitrary schematics,
OCR, rotation, electrical quantities/laws, and engineering certification remain prohibited.

### 2026-07-11 session 25 - COMPLETE: circuit-v1a graph foundation

The scope was advisor-reconciled with the GPT-5.6 Sol medium-effort review and implemented as
`circuit-v1a`, not a broad undifferentiated circuit-v1 claim. It built a
typed component-terminal-to-net evidence graph, canonical netlist comparison, controlled
one-loop-series rules, dataset cases, and callable runtime artifacts. `circuit-v1b` (explicit
junction dots plus simple parallel/mixed branches) is deferred to its own evidence and validation
gate. Crossings, arbitrary schematics, electrical values/laws, OCR, rotation, and functionality
remain out of scope.

Completion evidence: 11 cases, 4/4 typed defects, 5/5 ambiguity guards, 2/2 golden layouts,
exact terminal-netlist accuracy 6/6, zero unsupported passes/non-passing goldens/mismatches,
persisted artifacts, end-to-end CLI/MCP tests, and a passing unified regression suite.

### 2026-07-11 session 24 - GO: corrected circuit-v1 feasibility gate

The repaired probe received a bounded implementation **GO** from GPT-5.6 Sol. It now holds
canonical wire routes fixed under the wrong-symbol mutation, uses a true near miss outside terminal
tolerance, asserts golden completeness, and covers the advisor-required negative cases. This is a
GO to build the controlled verifier, not a readiness claim.

Bounded scope remains: controlled Pillow-rendered, orthogonal, single-loop DC diagrams; structural
component presence/type plus terminal/netlist connectivity only. Deferred: switches, crossings,
junctions, branches, OCR, rotation, values/polarity, and Ohm/Kirchhoff rules. Next work is to build
the normal circuit-specific evidence/claim/rule/dataset/CLI/MCP surface, and promote the probe cases
to exact automated tests before claiming validation.

### 2026-07-11 session 23 - COMPLETE

Triaged the round-trip outliers flagged as follow-up in session 22 (item 0 of Suggested Next
Work). Found and fixed a real gap: the round-trip render used generator-default layout
regardless of the original case's `render_options.layout_overrides`, so 3 of the 4 largest
outliers (22-33px) were pure layout artifacts, not extraction bugs. Added
`geometry_render_metadata()` in `chart_round_trip.py` to carry `layout_overrides`/font-size
keys through to the round-trip render; wired through `service.py`. The 4th outlier
(`mutated-07`, 19px) is a deliberately mutated `shifted_scale` defect case where the round-trip
delta is a correct, corroborating signal (matches the existing `chart_value_mismatch` rule), not
a bug.

Verified: p90 pixel delta dropped from 6.0px to 1.0px across all three chart-v2 datasets after
the fix; max dropped from 22-33px to 1-2px everywhere except the intentional `mutated-07` case.
150/150 tests still pass, including the verdict-unaffected regression test. No dataset files
modified (checked via `git status --porcelain` on all three dataset dirs).

Decision: no tolerance/verdict-gating set. The remaining outlier is an intentional defect
already caught by an existing deterministic rule, so round-trip gating there would be redundant,
not additive. See `wiki/impl-chart-v2-round-trip-check.md` "Outlier triage and layout-carrying
fix" section.

### 2026-07-11 session 22 - COMPLETE

Implemented the round-trip re-rendering accuracy check for chart-v2 (first concrete step from
`wiki/knowledge-accuracy-and-synthetic-data-roadmap.md`, chosen via advisor-gated plan mode
over circuit-v1 and real-world image/OCR sourcing since it needs no external data). Purely
additive/non-blocking: new `chart_round_trip.py` module, `RoundTripComparison`/
`BarGeometryDelta` on `VerificationResult` (optional, omit-if-None), `include_round_trip` flag
on `run_chart_verification`, `summarize_chart_round_trip_results` + CLI
`run-chart-round-trip-validation`. See `wiki/impl-chart-v2-round-trip-check.md` for the design
rationale (why the naive circular version doesn't work) and the measured pixel-delta
distribution across all three chart-v2 datasets.

Verified: 150 tests pass (141 prior + 9 new), including a regression test proving
`report.verdict`/`findings` are byte-identical whether round-trip is included or not. CLI ran
read-only across `chart-v2` (24 cases, 17 evaluable), `chart-v2-noisy` (6 cases, 4 evaluable),
and `chart-v2-realworld-pilot` (24 cases, 18 evaluable, checksum-frozen) with zero exceptions
and zero dataset file mutations (`git status --porcelain` clean on all three dataset dirs).

Explicitly deferred, not started this session: tolerance/threshold decision, verdict-gating,
triaging the outlier cases (max deltas 22-33px across the three datasets), and extending the
technique to arrow-v1/geometry-v1/coordinate-graph-v1/flowchart-v1.

### 2026-07-11 session 21e - COMPLETE

Advisor review after session 21d flagged that regenerating the coordinate and flowchart
datasets had deleted their previously tracked derived artifacts (`claim_graph.json`,
`evidence_graph.json`, `overlay.png`, `report.json`, `primitive_evidence_graph.json`).
Restored them by running `verify-coordinate`/`verify-flowchart` with `--output-dir` per
case across both datasets. 141/141 tests still pass; no correctness regression (these
are recomputed outputs, not inputs). See `wiki/project-log.md` session 21e for the
lesson: follow any `generate-*-dataset` run on an already-committed dataset with a
per-case `verify-*` pass before considering the regeneration done.

This closes out the session. All four requested extensions (arrow-v1 net-force,
coordinate-graph label identity, coordinate-graph multi-series, flowchart branching
topology) are implemented, validated, tested, and documented, and the dataset
directories are clean. Only remaining open item: GitHub remote + cron-scheduled cloud
routine setup, blocked on the user's next input (no `gh` CLI, no git remote configured).

### 2026-07-11 session 21d - COMPLETE

Added branching/diagonal connector topology to flowchart-v1 (fourth and last of the four
extensions requested this session), closing that Known Limits item. Advisor gate confirmed no
extractor/rule rework was needed (a throwaway probe showed diagonal connectors already detected
correctly) — the feature was a single generator anchor-calculation generalization
(`_anchor_toward`, boundary-intersection instead of hardcoded bottom/top-center) plus dataset
cases.

Verified: controlled (12 cases) typed hits `7/7`, ambiguous guard `2/2`, `0` unsupported passes,
`0` golden failures. 141 tests pass (139 prior + 2 new).

This closes all four extensions the user requested this session (arrow-v1 net-force,
coordinate-graph label identity, coordinate-graph multi-series, flowchart branching topology).
GitHub remote + cron-scheduled cloud routine setup remains the only pending item, blocked on the
user's next input (no `gh` CLI, no git remote configured in this environment).

### 2026-07-11 session 21c - COMPLETE

Added multi-series polylines to coordinate-graph-v1 (third of the four extensions requested
this session), closing that Known Limits item. Advisor gate confirmed no extractor rework was
needed — the feature is a claim-graph/rule/dataset generalization of the existing single-polyline
check into an N-series loop (`source_reference.polylines`, per-series `polyline_connection_wrong`
findings tagged with `series_id`).

Verified: controlled (15 cases) typed hits `7/7`, ambiguous guard `2/2`, `0` unsupported passes,
`0` golden failures. 139 tests pass (137 prior + 2 new).

Next in the requested sequence: flowchart branching topology. GitHub remote + cron setup still
pending the user's input.

### 2026-07-11 session 21b - COMPLETE

Added label-based point identity to coordinate-graph-v1 (second of the four extensions
requested this session), closing that Known Limits item.

Verified: controlled (13 cases) typed hits `6/6`, ambiguous guard `2/2`, `0` unsupported
passes, `0` golden failures. 137 tests pass (135 prior + 2 new).

Next in the requested sequence: coordinate-graph multi-series, then flowchart branching
topology. GitHub remote + cron setup still pending the user's input.

### 2026-07-11 session 21 - COMPLETE

Extended arrow-v1's force-balance check with a declared non-zero expected resultant
(`scenario_type: "net-force"` + `source_reference.expected_resultant`), closing the
"non-zero declared expected resultant" deferred item.

Verified: controlled (19 cases) typed hits `9/9`, force-balance typed hits `2/2`, `0` unsupported
passes, `0` golden failures. 135 tests pass (132 prior + 3 new).

Still pending: GitHub remote + cron-scheduled cloud routine setup (blocked on `gh` CLI not being
installed; needs the user's next input). User asked (this session) to extend all four remaining
backlog items in sequence: arrow-v1 net-force (this entry), coordinate-graph label identity,
coordinate-graph multi-series, flowchart branching topology — continuing to those next.

### 2026-07-11 session 20 - COMPLETE

Added a noisy-track equilibrium case pair to arrow-v1 (`arrow-v1-noisy` grew from 6 to 8 cases),
closing one deferred item, plus the first pytest coverage for that dataset.

Verified: typed hits `5/5`, force-balance typed hits `1/1`, `0` unsupported passes, `0` golden
failures. 132 tests pass (130 prior + 2 new).

Still pending: GitHub remote + cron-scheduled cloud routine setup (blocked on `gh` CLI not being
installed; needs the user's next input).

### 2026-07-11 session 19 - COMPLETE

Closed the flowchart-v1 `PrimitiveEvidenceGraph` gap noted in session 17: added
`primitive_graph_from_flowchart`, registered `flowchart-v1` as a fifth primitive profile, and
wired `run_flowchart_verification` to populate it (previously deliberately `None`).

Verified: 130 tests pass (128 prior + 2 new). Flowchart-v1 controlled metrics unchanged
(`6/6` typed hits, `2/2` ambiguity guards, `0` unsupported passes).

Still pending: GitHub remote + cron-scheduled cloud routine setup (blocked on `gh` CLI not being
installed; needs the user's next input — see session 18's note below).

### 2026-07-11 session 18 - COMPLETE

Added the coordinate-graph-v1 noisy blur/downscale/JPEG track (6 cases: 2 golden, 4 typed
mutated), continuing autonomous work after the user went to sleep with no response to a pending
scope question. Per advisor guidance, picked a lower-risk backlog extension item over opening a
new vertical (circuit-v1) without the ability to confirm scope first.

Delivered: `coordinate_dataset.noisy_dataset_cases()` / `build_noisy_coordinate_dataset`, CLI
`generate-noisy-coordinate-dataset`, 2 new tests. No new extractor/rule code was needed — the
existing `run_coordinate_verification` and `summarize_coordinate_validation_results` worked
unchanged against the noisy track.

Verified: typed hits `4/4`, false unsupported passes `0`, golden failures `0`, verdict mismatches
`0` — all passed on the first empirical measurement. 128 tests pass (126 prior + 2 new).

Bounds: only two mild configured transforms tested (light blur; light downscale+JPEG).

**Still pending from the prior session**: setting up a GitHub remote + cron-scheduled cloud
routine for future feature work. Blocked on `gh` CLI not being installed in this environment (no
way to authenticate to GitHub non-interactively). Needs the user to either (a) create a repo and
give its URL, or (b) install/authenticate `gh` themselves (e.g. via `! gh auth login`) next
session.

### 2026-07-11 session 17 - COMPLETE

Implemented `flowchart-v1`, the fifth executable vertical, during an autonomous multi-hour work
session (user request: build features to full completion one at a time, no fixed time-box,
pause between features; later revised to a cron-scheduled 15-30 min/feature cadence for future
sessions — see below).

Delivered:

- `flowchart_generator.py` (vertical-chain Pillow renderer: rectangle/diamond nodes, straight
  connector arrows), `flowchart_labels.py` (fixed 6-entry catalog label decoder),
  `flowchart_extractor.py` (fill-ratio shape classification, achromatic-mask connector detection
  reusing arrow-v1's principal-axis technique, nearest-node attach resolution), `flowchart_rules.py`,
  `build_flowchart_claim_graph`, `flowchart_dataset.py`
- `specs/flowchart-evidence-graph.schema.json`, flowchart service entrypoints, CLI commands
  (`generate-flowchart-dataset`, `verify-flowchart`, `run-flowchart-validation`), 3 new MCP tools
- `datasets/flowchart/flowchart-v1/` with 10 cases (2 golden, 8 mutated: 6 typed + 2 ambiguous)
- Found and fixed a real extraction bug during validation: anti-aliased node-label glyph edges
  polluted the connector mask, forcing a false `needs_review` on every golden case; fixed by
  blanking each node's label region out of the connector mask before component search.

Verified:

- flowchart-v1 controlled (10 cases): typed hits `6/6`, ambiguous guard `2/2`, node-count evidence
  `9/10` (expected: the excluded case is the deliberately degenerate node), false unsupported
  passes `0`, golden failures `0`, verdict mismatches `0`
- 126 tests pass (106 prior + 20 new); chart/arrow/geometry/coordinate controlled metrics
  unaffected by construction (no shared files modified)

Bounds: controlled Pillow renders only; single vertical-chain topology (no branching/diagonal
routing); exactly two shape types (rectangle, diamond); 6-entry fixed label catalog; no noisy
track or independently authored images yet; no `PrimitiveEvidenceGraph` adapter yet.

**Operating change starting next session**: the user asked to shift to a cron-scheduled cloud
routine that works through the backlog one feature per run, at an hourly cadence, with each
feature scoped to at least 15-30 minutes of real implementation+test work (not a trivial change).
See the "Suggested Next Work" list below for the feature order. This requires a GitHub remote
(the repo currently has none — cloud routines clone from a URL and cannot see the local disk);
setting that up plus the routine itself is the first item of the next session.

### 2026-07-11 session 16 - COMPLETE

Implemented `coordinate-graph-v1`, the fourth executable vertical, proving the dual
independent-numeric-axis capability the plan flagged as the one genuinely new technical piece.

Delivered:

- `coordinate_generator.py` (dual numeric-axis Pillow renderer: independent X/Y ticks, colored
  scatter points, one connected polyline), `coordinate_extractor.py` (spec-blind dual-axis tick
  reader adapted from `tick_reader`'s numeric template catalog, point color-component detection,
  per-pair polyline edge coverage), `coordinate_rules.py`, `build_coordinate_claim_graph`,
  `coordinate_dataset.py`
- `specs/coordinate-evidence-graph.schema.json`, coordinate service entrypoints, CLI commands
  `generate-coordinate-dataset`, `verify-coordinate`, `run-coordinate-validation`, and three new
  MCP tools (`build_coordinate_claim_graph`, `parse_coordinate`, `verify_coordinate`)
- `primitive_graph_from_coordinates` primitive-evidence adapter (points -> `point` primitives,
  axes -> `line` primitives, detected polyline edges -> `connected_to` relationships)
- `datasets/coordinate/coordinate-graph-v1` with 11 cases (4 golden including a mismatched
  X/Y-scale signed-axis "trap" case, 7 mutated: 5 typed + 2 ambiguous)
- Found and fixed a real extraction bug during validation: the axis-minimum tick's label text
  sits at the same pixel row/column where the two axes meet, and its text was bleeding into the
  opposite axis's tick-mark search, corrupting the linear fit on one golden case

Verified:

- Measured pixel->data round-trip error first (per the no-guessed-tolerance discipline) across
  zero-baseline/non-zero-min/signed axis configs with X-scale != Y-scale: effectively zero after
  the corner-tick-bleed fix; set position tolerance at 3% of each axis's declared range
- coordinate-graph-v1 controlled (11 cases): typed hits `5/5`, ambiguous guard `2/2`, false
  unsupported passes `0`, golden failures `0`, verdict mismatches `0`
- 106 tests pass (85 prior + 21 new); chart/arrow/geometry controlled metrics re-verified
  unchanged (`9/9`, `8/8`, `7/7`, all guard rates `1.0`, `0`/`0`)

Bounds: controlled Pillow renders only; single connected polyline (no multi-series, no curve
fitting, no general topology); tick catalog restricted to multiples of 5 in [-150, 150]; no noisy
track or independently authored images yet; color-only point identity.

### 2026-07-10 session 15 - COMPLETE

Completed the additive basic-to-complex foundation.

Delivered:

- strict shared primitive/relationship graph with semantic validation and domain traceability
- spec-blind `extract-primitives` CLI and `parse_primitives` MCP surface
- checksum-frozen 20-case geometry noisy gate across five transform families
- immutable validation summaries and shared test fixtures
- run-length connected components plus cached chart text/font templates

Verified:

- geometry noisy: golden `10/10`, typed `5/5`, ambiguity `5/5`, unsupported passes `0`, manifest `20/20`
- all prior controlled/noisy vertical metrics preserved
- unified tests `85/85` in about 63 seconds; chart end-to-end `16/16` in about 35 seconds

Bounds: shared primitives are an additive audit layer. Domain rules still use their existing evidence
graphs; new coordinate, flowchart, and circuit verticals remain follow-up work.

### 2026-07-10 session 14 - COMPLETE

Completed `geometry-v1`, the third executable vertical, from the partially implemented state left
by the interrupted Claude session.

Delivered:

- controlled mechanical plate extractor and rules for hole count, relative diameter ratios,
  declared linear alignment/spacing, and fixed-catalog dimension text
- `geometry-evidence-graph.schema.json`, service entrypoints, CLI generate/verify/validate commands,
  and six geometry/arrow MCP tools alongside the original chart tools
- `datasets/mechanical/geometry-v1` with 5 golden and 9 mutated cases
- installable package discovery and the `visual-qa` console command
- focused geometry, schema, MCP, and packaging tests

Verified:

- geometry controlled: typed hits `7/7`, ambiguity guards `2/2`, hole-count evidence `13/13`,
  false unsupported passes `0`, golden non-passes `0`, verdict mismatches `0`
- all 70 tests pass when run in bounded groups; the unchanged end-to-end chart file passes all
  16 tests but takes about 4m19s because it repeatedly rebuilds/revalidates full datasets

Bounds: controlled Pillow renders only; single rectangular plate; circular holes; fixed dimension
catalog; ordered hole pairing; no noisy/real-world track, general OCR, unit calibration, general
callout arrows, or CAD-native geometry.

### 2026-07-10 session 13 - COMPLETE

Implemented the translational force-balance rule for arrow-v1 — the first theory-aware
(Level 3) check — closing suggested-next-work item 1 after running its deferred advisor gate.

Design decisions (advisor gate): magnitude = extractor pixel vectors summed directly (no
spec-declared magnitudes, no px-to-newton calibration in v1); equilibrium is opt-in via
`source_reference.scenario_type = "equilibrium"` + a `force-balance-correct` check, with
either half alone becoming a ClaimGraph gap; scope is translational balance only, finding
type `force_balance_violation`.

Delivered:

- `force-balance-correct` claim branch in `build_arrow_claim_graph` with two-way
  scenario/check gating gaps
- fifth rule block in `arrow_rules.run_arrow_claims`: resultant-ratio criterion
  (`|resultant| / max(length_px)` vs. tolerance 0.15), partial-force-set refusal, per-arrow
  vector evidence, overlay annotation
- extractor gap coverage so `ambiguous_arrow_colors` also gates the balance check
- `datasets/physics/arrow-v1` grown to 17 cases: `golden-06` (balanced equilibrium),
  `mutated-10` (shortened weight arrow — first defect class invisible to all four prior
  rules), `mutated-11` (ambiguity guard under declared equilibrium)
- `force_balance_metrics` in the arrow validation summary

Verified:

- 61 tests pass (56 prior + 5 new)
- arrow-v1 controlled (17 cases): typed hits `8/8`, ambiguous guard `3/3`, force-balance
  `1/1`, false unsupported passes `0`, golden failures `0`
- arrow-v1-noisy unchanged (`4/4`, `0` unsupported passes); chart-v2 controlled unchanged
  (`9/9`, guard `1.0`, `0`/`0`)

Bounds: translational balance only (no torque/moments), opt-in per spec, controlled renders
only; deferred px-to-newton calibration and non-zero expected resultants.

### 2026-07-10 session 12 - COMPLETE

Added label-based arrow identity as a second, noise-robust identity signal for arrow-v1 and
built the first arrow-v1 noisy track, closing suggested-next-work item 1 from session 11.

Delivered:

- `arrow_labels.py`: fixed-catalog template-matched label decoder (`W,N,F,f,T,P,Fx,Fy`),
  mirroring the chart-v2 tick-reader pattern
- label-first identity resolution in `arrow_rules._match_arrows_by_color`, with color as
  fallback; `ambiguous_arrow_colors` gap suppressed when labels resolve identity
- tail/head extremity fix in `arrow_extractor._end_statistics` (true geometric extremity
  instead of a windowed average) so label crop regions align correctly
- `datasets/physics/arrow-v1` grown to 14 cases (5 golden, 9 mutated) with label rendering
- new `datasets/physics/arrow-v1-noisy` (6 cases: 2 golden, 4 typed mutated) with
  blur/downscale/JPEG postprocessing, CLI command `generate-noisy-arrow-dataset`
- fixed two robustness bugs found while validating the noisy track: JPEG/downscale color
  drift (relied on labels instead of loosening color tolerance) and object-region bbox
  inflation from scattered noise blobs (fixed by using only the largest connected gray
  component)

Verified:

- 56 tests pass (54 prior + 2 new label tests)
- arrow-v1 controlled (14 cases): typed hits `7/7`, ambiguous guard `2/2`, false unsupported
  passes `0`, golden failures `0`
- arrow-v1-noisy (6 cases): typed hits `4/4`, false unsupported passes `0`, golden failures
  `0`, verdict mismatches `0`
- chart-v2 controlled metrics re-verified unchanged

Bounds: label catalog is a small fixed alphabet (8 entries), noisy track covers only mild
blur/downscale/JPEG, object detection still assumes a single connected gray blob. No
theory-aware physics rules, no real-world arrow images, no geometry vertical yet.

### 2026-07-10 session 11 - COMPLETE

Implemented arrow-v1, the second executable vertical (physics free-body diagrams), proving the
Spec -> ClaimGraph -> EvidenceGraph -> Rules architecture generalizes beyond charts.

Delivered:

- deterministic free-body renderer, spec-blind color-component arrow extractor
- arrow ClaimGraph generation with the same unsupported-check gap guardrails
- count/presence/direction/anchor rules with rule_id and coordinate evidence
- `datasets/physics/arrow-v1` (4 golden, 6 typed mutated, 2 ambiguous)
- `specs/arrow-evidence-graph.schema.json`, arrow service entrypoints, CLI commands
  `generate-arrow-dataset`, `verify-arrow`, `run-arrow-validation`

Verified:

- 54 tests pass (43 prior + 11 arrow)
- arrow typed hits `6/6`, ambiguous guard `2/2`, false unsupported passes `0`, golden
  non-passes `0`
- chart-v2 controlled metrics re-verified unchanged (`9/9`, guard `1.0`, `0`/`0`)

Bounds: synthetic single-box free-body diagrams with color-declared arrow identity only; no
label reading, noisy track, real-world arrow images, or theory-aware physics rules yet.

### 2026-07-10 session 10 - COMPLETE

Completed the configured noisy-hardening gate and added a separate hybrid real-world pilot without
widening the general readiness claim.

Delivered:

- signed-safe color arithmetic, component-based bar segmentation, peak/coverage plot detection
- calibrated tick-template candidates plus a visual-only sequence decoder
- tolerant multi-font/category label matching and explicit axis-range validation
- 24-case `chart-v2-realworld-pilot` with provenance and frozen checksums
- pilot extraction metrics and combined chart-suite validation CLI

Verified:

- 43 tests pass, including adversarial ambiguity, missing-gridline, irregular-spacing, and manifest-completeness coverage
- controlled typed hits `9/9`; noisy typed hits `2/2`; all controlled/noisy golden cases pass
- pilot typed hits `6/7` (`0.86`), ambiguous guard `7/7`, false unsupported passes `0`
- pilot bar/tick/label accuracy `1.00/0.94/0.95`; manifest valid `24/24`

The result is evidence for the configured renderer/transform/reference-backed families only.

### 2026-07-10 session 9 - COMPLETE

Operationalized chart-v2 for Phase 2 by adding an MCP wrapper, audit schema upgrades, noisy validation, and a separate OCR gate.

Delivered:

- `pyproject.toml` with explicit runtime/dependency metadata and stable MCP SDK pinning
- thin MCP stdio wrapper for `build_claim_graph`, `parse_chart`, `run_rules`, and `verify_chart`
- `rule_id`, provenance, and separated extraction/rule confidence fields in runtime artifacts
- CLI support for `serve-mcp`, `run-rules`, `generate-noisy-dataset`, `run-phase2-validation`, and `run-ocr-validation`
- `datasets/charts/chart-v2-noisy/` as a separate noisy robustness gate
- OCR environment capture and separate OCR validation summary path
- new tests for MCP tools and Phase 2 validation flows

Verified:

- `pytest mcp-server/tests -q` passes with 33 tests
- `python -m visual_qa_mcp.cli run-validation --dataset datasets/charts/chart-v2` preserves the controlled chart-v2 bounded metrics
- `python -m visual_qa_mcp.cli run-phase2-validation --controlled-dataset datasets/charts/chart-v2 --noisy-dataset datasets/charts/chart-v2-noisy` surfaces noisy-track weaknesses separately from the readiness baseline
- `python -m visual_qa_mcp.cli run-ocr-validation --controlled-dataset datasets/charts/chart-v2 --noisy-dataset datasets/charts/chart-v2-noisy` confirms OCR remains unavailable and safely degrades to `needs_review`

### 2026-07-10 session 8 - COMPLETE

Prepared chart-v2 as a callable local tool surface so the current bounded verifier can be wrapped by an MCP server later without changing readiness claims.

Delivered:

- reusable service-layer chart-v2 entrypoints for claim generation, evidence extraction, full verification, and artifact writing
- `ArtifactPaths` / `VerificationResult` contracts for shared callable execution
- validation refactor so dataset `run_case()` delegates to the service layer
- optional metadata handling for callable use with safe local defaults only
- CLI support for `build-claim-graph`, `extract-chart-evidence`, and `verify-chart`
- docs updates that describe the current state as MCP-ready callable tooling, not yet a full MCP server process
- new tests for pure verification, artifact writing, delegation, CLI output, metadata-optional execution, and OCR degradation

Verified:

- `pytest mcp-server/tests -q` passes with 29 tests
- `python -m visual_qa_mcp.cli run-validation --dataset datasets/charts/chart-v2` preserves current chart-v2 metrics and bounded readiness claims

### 2026-07-09 session 7 - COMPLETE

Hardened chart-v2 `ClaimGraph` handling so unsupported spec checks are surfaced explicitly and cannot silently turn into unsupported passes.

Delivered:

- `ClaimGraph` gaps for unsupported or unmapped chart-v2 spec checks
- rule-runner integration that merges claim-generation gaps into `checks_skipped`
- runtime validation of `claim_graph.json` before writing or referencing it
- `claim_graph_path` in `VisualQaReport` / findings schema so the claim artifact is part of the formal audit trail
- new tests for unknown checks, mistyped known checks, and invalid runtime claim graphs

Verified:

- `pytest mcp-server/tests -q` passes with 23 tests
- `python -m visual_qa_mcp.cli run-validation --dataset datasets/charts/chart-v2` preserves current chart-v2 metrics and bounded readiness claims

### 2026-07-09 session 6 - COMPLETE

Implemented chart-v2 `ClaimGraph` contracts so rule execution is now spec-driven through explicit claim generation.

Delivered:

- `specs/claim-graph.schema.json` for chart-v2 claim artifacts
- `mcp-server/src/visual_qa_mcp/claim_graph.py` to generate chart-v2 claims from `VisualSpec`
- chart rule integration so validators consume `ClaimGraph` rather than ad hoc spec parsing
- `claim_graph.json` artifacts emitted alongside evidence, overlay, and report outputs
- tests and workflow docs updated for the new claim contract

Verified:

- `pytest mcp-server/tests -q` passes with 20 tests
- `python -m visual_qa_mcp.cli run-validation --dataset datasets/charts/chart-v2` preserves current chart-v2 metrics and bounded readiness claims

### 2026-07-09 session 5 - COMPLETE

Implemented chart-v2 axis-scale extraction and upgraded the chart verifier from metadata-derived values to image-derived scale mapping.

Delivered:

- chart-v2 extractor pipeline with tick detection, monotonic scale inference, non-zero minimum support, and signed-axis support
- template backend plus optional OCR backend scaffold
- `specs/evidence-graph.schema.json` update for chart-v2 contracts
- `datasets/charts/chart-v2/` with 8 golden and 16 mutated cases
- expanded tests with 18 passing checks
- refreshed advisor evidence packs for chart-v2 readiness review
- updated agent memory and workflow docs so future sessions start from the chart-v2 bounded-claim baseline

Verified:

- `pytest mcp-server/tests -q` passes with 18 tests
- chart-v2 validation summary meets current controlled-to-semi-realistic targets on the configured template backend
- unsupported `pass` outcomes are zero in the current 24-case set

### 2026-07-09 session 4 - COMPLETE

Implemented the first executable chart-only MVP loop and validation set.

Delivered:

- `mcp-server/src/visual_qa_mcp/` - chart extractor, rule runner, overlay, CLI, validation, and advisor artifacts helpers.
- `specs/evidence-graph.schema.json` - chart evidence contract.
- `docs/chart-mvp-workflow.md` - operational workflow with advisor gates.
- `datasets/charts/chart-v1/` - 4 golden and 8 mutated chart cases.
- `outputs/advisor/` - gate evidence, validation summary, and reconciled Gate 3 review.
- `mcp-server/tests/` - schema, rule, and end-to-end tests.

Verified:

- `pytest mcp-server/tests -q` passes with 14 tests.
- Validation summary meets the controlled-MVP targets for the synthetic chart set.

### 2026-07-09 session 3 - COMPLETE

Captured research direction, no-fine-tuning strategy, validator architecture, and 3D roadmap in the wiki.

Delivered:

- `wiki/knowledge-product-direction.md` - product framing and research ideas.
- `wiki/knowledge-rules-validators.md` - rule and validator architecture concept.
- `wiki/knowledge-no-tuning-and-3d.md` - no-fine-tuning strategy and 3D roadmap.
- `AGENTS.md` and `CLAUDE.md` updates for future agent session context.

### 2026-07-09 session 2 - COMPLETE

Reframed the project direction toward high-assurance, theory-aligned visual verification.

Delivered:

- `docs/high-assurance-roadmap.md` - roadmap for medical/anatomy, chemistry/biology, and CAD target tracks.
- README/product/MVP/problem-map updates to clarify that high-risk domains are long-term goals.
- Agent guidance updates so future sessions preserve the stronger reliability framing.

### 2026-07-09 session 1 - COMPLETE

Created the initial Visual QA MCP project scaffold and agent guidance files.

Delivered:

- `README.md` - project overview and design principle.
- `docs/problem-map.md` - taxonomy of educational visual errors.
- `docs/mvp-scope.md` - first MVP scope for charts, arrows, and geometry.
- `docs/validation-plan.md` - validation dataset and metrics plan.
- `specs/visual-spec.schema.json` - schema for expected visual structure.
- `specs/findings.schema.json` - schema for QA reports.
- `skills/educational-visual-qa/SKILL.md` - draft agent skill workflow.
- `CLAUDE.md` and `AGENTS.md` - guidance for future agents.
- `wiki/` - project memory scaffold.

Verified:

- All JSON files parse successfully with PowerShell `ConvertFrom-Json`.
- Project files were listed after creation.

## Suggested Next Work

**Vertical count is frozen at six as of session 27.** Do not start a seventh vertical
(new domain) without an explicit user decision to unfreeze it — the architecture-generalizes
question is answered; unallocated effort goes to external validity instead. Circuit-v1
hardening (item 4 below) is in-scope background work on an *existing* vertical, not new scope.

**Strategy note (2026-07-11, session 28)**: the project is confirmed **synthetic-only** — no
independently authored or publisher-sourced images. External validity is pursued via
declared-universe synthetic coverage per `wiki/knowledge-synthetic-coverage-deep-research.md`,
validated with renderer/style/content/degradation-held-out splits. The list below is reordered
to match that report's evidence-backed build order.

1. **[DONE 2026-07-11] Formal input model + stratified registry + mixed-strength covering
   arrays** for chart-v2. Delivered as a Matrix A (in-universe presentation x defect,
   exhaustively enumerated since the space is small: 12 cases) / Set B (any out-of-universe
   axis flipped, testing that degraded evidence masks defect detection to `needs_review`: 6
   cases) design, frozen at `datasets/charts/chart-v2-covering-v1` (18 cases, checksum
   manifest), generated via `generate-chart-covering-dataset` and validated via the existing
   generic `run-validation --dataset ...` command. See
   `wiki/impl-chart-v2-covering-array-input-model.md` for the full design and measured
   result (18/18 cases correct, 8/8 typed-defect hits, 6/6 masking-guard cases, 0
   unsupported passes). Known gap: layout-mismatch out-of-universe axis not reproducible
   with the current renderer and is deferred, not silently dropped. Not yet extended to the
   other five verticals or to continuous-nuisance axes (LHS) — those remain open.
2. **Boundary/magnitude sweeps on existing typed-defect classes** across all six verticals —
   the cheap entry point of the failure-mining loop (no new infra; converts N/N
   hand-picked-mutation claims into measured per-defect-class sensitivity curves).
3. **Full failure-mining loop** (deep-research top investment 2): covering-array seeds ->
   boundary sweeps -> adaptive local search around low-margin cases -> delta-debug
   minimization -> root-cause clustering into named regression strata. Never add raw failure
   seeds to the suite directly.
4. **Ground-truth-preserving degradation harness** (deep-research top investment 3) across the
   four delivery paths: digital export, office reproduction (print/scan), camera capture
   (perspective/glare — transforms ground-truth geometry via a first-class transformation
   stack), and screen-photo/chat. Extends the current blur/downscale/JPEG tracks.
5. **Reporting upgrade to selective-prediction statistics**: per-stratum coverage (Wilson
   interval), selective risk on decided cases, abstention profile, and rule-of-three /
   Clopper-Pearson upper bounds when observed failures are zero — replaces bare "N/N" language
   in future validation summaries per Claim Discipline.
6. **Rule-mutation testing** on the rule layer (flip inequalities, disable tolerance checks,
   remove fallbacks; measure suite catch rate) as the fault-correlated coverage supplement.
7. Extend the crutch-stripping technique to other verticals' extractors (arrow-v1 labels,
   geometry-v1 dimension labels, coordinate/flowchart label catalogs) — cheap background work,
   likely to surface crash-safety gaps like session 27's chart-v2 find.
8. Install and validate the optional OCR backend so OCR gets its own evidence-backed readiness
   gate — the direct fix for the template-catalog wall, and a prerequisite for LLM-generated
   realistic label content (deep-research section 6) beyond the fixed catalogs.
9. Circuit-v1 hardening: a checksum-frozen noisy track, or the `PrimitiveEvidenceGraph` circuit
   adapter (the only vertical without one).
10. Longer-term extensions when justified: torque/moment balance, coordinate curve-fitting,
    flowchart shape types, round-trip re-rendering for the non-chart verticals, grammar-based
    structural generation with topological coverage taxonomy (deep-research section 8).
11. **Long-arc direction (not yet queued for implementation)**: migrate rules toward a generic
    declared-vs-recovered structural diff over `PrimitiveEvidenceGraph`, with domain rules
    shrinking to thin adapters for tolerance policy, correspondence/abstention policy, and
    theory-aware checks (force balance etc.) that a geometry-only diff cannot express. See
    `wiki/knowledge-representation-centric-architecture.md` for the full design discussion and
    rationale for sequencing this *after* items 1-6 (statistical/failure-mining baselines must
    exist before refactoring the verdict core, so regressions in the safety property are
    detectable). Suggested pilot order: (a) flowchart-v1 rules -> `PrimitiveEvidenceGraph`
    migration, (b) grammar-based generation for one vertical, (c) generic diff engine only
    after both prove out.

## Recent Completed Milestones

- 2026-07-09: Project scaffold and agent memory files created.
- 2026-07-09: High-assurance domain roadmap added.
- 2026-07-09: Research direction, validator architecture, no-tuning strategy, and 3D roadmap captured.
- 2026-07-09: First executable chart-only MVP implemented with advisor review and validation artifacts.
- 2026-07-09: Chart-v2 axis-scale extraction implemented with dual backend scaffolding and 24-case validation set.
- 2026-07-09: Chart-v2 ClaimGraph contract added so rule execution is spec-driven end to end.
- 2026-07-09: Chart-v2 ClaimGraph hardening added unsupported-check guardrails and formal claim audit artifacts.
- 2026-07-10: Chart-v2 callable tool surface added for MCP-ready local verification without expanding current readiness claims.
- 2026-07-10: Phase 2 MCP wrapper, audit schema upgrades, noisy dataset gate, and OCR validation gate added.
- 2026-07-10: Arrow-v1 free-body verifier added as the second executable vertical with a 12-case controlled dataset.
- 2026-07-10: Arrow-v1 label-based identity and noisy track added (14-case controlled, 6-case noisy, 7/7 and 4/4 typed hits).
- 2026-07-10: Arrow-v1 translational force-balance rule added (first theory-aware check; 17-case controlled set, 8/8 typed hits, force-balance 1/1).
- 2026-07-10: PrimitiveEvidenceGraph v1, geometry noisy gate, and sub-minute unified regression baseline added.
- 2026-07-11: Coordinate-graph-v1 added as the fourth executable vertical with dual independent numeric axes (11-case controlled dataset, 5/5 typed hits, 2/2 ambiguity guards).
- 2026-07-11: Flowchart-v1 added as the fifth executable vertical with shape-typed nodes and directed connector topology (10-case controlled dataset, 6/6 typed hits, 2/2 ambiguity guards).
- 2026-07-11: Coordinate-graph-v1 noisy blur/downscale/JPEG track added (6-case dataset, 4/4 typed hits, clean on first measurement).
- 2026-07-11: Flowchart-v1 PrimitiveEvidenceGraph adapter added, closing the last noted gap from its initial vertical build.
- 2026-07-11: Arrow-v1 noisy-track equilibrium case added (8-case noisy dataset, 5/5 typed hits, force-balance 1/1).
- 2026-07-11: Arrow-v1 non-zero declared expected resultant (net-force scenario) added (19-case controlled dataset, 9/9 typed hits, force-balance 2/2).
- 2026-07-11: Coordinate-graph-v1 label-based point identity added (13-case controlled dataset, 6/6 typed hits, 2/2 ambiguity guards).
- 2026-07-11: Coordinate-graph-v1 multi-series polylines added (15-case controlled dataset, 7/7 typed hits, 2/2 ambiguity guards).
- 2026-07-11: Flowchart-v1 branching/diagonal connector topology added (12-case controlled dataset, 7/7 typed hits, 2/2 ambiguity guards).
- 2026-07-11: Chart-v2 additive round-trip re-rendering accuracy check added (verdict-unaffected, measured pixel-delta distribution across controlled/noisy/pilot datasets, no tolerance set yet).
- 2026-07-11: Chart-v2 round-trip check made layout-aware (carries `layout_overrides`/font sizes through); p90 delta dropped from 6px to 1px across all three datasets, remaining 19px outlier explained as an intentional defect case.
- 2026-07-11: Circuit-v1a/v1b committed and pushed to a new GitHub remote (`roan2008/visual-qa-mcp`), closing a ~9-session-old operational risk item.
- 2026-07-11: Renderer crutch-stripping experiment on chart-v2's Matplotlib path found and fixed a real crash-safety gap (unmatched layout raised `ValueError` instead of `needs_review`); off-catalog ticks and non-Arial fonts both confirmed to degrade safely. Vertical count frozen at six going forward.
