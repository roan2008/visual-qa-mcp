---
name: impl-flowchart-v1-vertical-chain
description: flowchart-v1 vertical-chain node/connector verifier design, bounds, and validation
metadata:
  type: implementation
  status: current
  last_updated: 2026-07-11
---

# Flowchart v1: Vertical-Chain Node/Connector Verifier

## Purpose

Fifth executable vertical. Proves the Spec -> ClaimGraph -> EvidenceGraph -> Rules architecture
extends to diagrams with shape-typed nodes and directed connector topology, the two genuinely new
capabilities beyond the prior four verticals (bars, arrows-on-an-object, holes-in-a-plate, and a
dual-numeric-axis coordinate plane).
[source: mcp-server/src/visual_qa_mcp/flowchart_extractor.py:1]

## Scope Bounds (Controlled Only, Advisor-Gated 2026-07-11)

- Synthetic vertical-chain flowcharts rendered by `flowchart_generator.py`: nodes stacked
  top-to-bottom, each either a filled rectangle or a filled diamond, linked by straight vertical
  connector arrows. No diagonal/branching layout, no orthogonal/elbow routing, and no general
  graph reconstruction in v1 (advisor-gated scope freeze, mirroring coordinate-graph-v1's
  per-pair-edge-not-traced-topology bound).
- **Node identity is color fill**, reusing the arrow-v1/coordinate-graph-v1 color-match +
  collision-guard pattern (`_match_nodes_by_color`). Text label is a **separate opt-in
  `node-label-correct` check, not the identity key** — an advisor-gated decision so flaky label
  decoding can never block the core node/connector capability.
- Exactly two shape types: `rectangle` and `diamond`. Shape is classified purely geometrically —
  no corner/vertex detection needed.
- No OCR, no real-world images, no noisy track, no swimlanes, no multi-node-per-row layout.

## Node Shape Classification (spec-blind)

Fill ratio = `pixel_count / bbox_area`. An axis-aligned filled rectangle has ratio ~1.0; a filled
diamond inscribed in the same bbox (vertices at the bbox edge midpoints) has ratio ~0.5. Threshold:
`>= 0.75` -> rectangle, `[0.30, 0.75)` -> diamond, below that -> `degenerate_node_geometry` gap
(too small/no recognizable fill ratio). This avoids any explicit corner or vertex detection.
[source: mcp-server/src/visual_qa_mcp/flowchart_extractor.py:_classify_shape]

## Connector Extraction (spec-blind)

Connectors are straight dark-gray arrows detected via an achromatic value-band mask (`spread <=
15`, `60 <= value <= 180`), reusing the arrow-v1 principal-axis head/tail asymmetry technique
(head end has larger perpendicular spread from the arrowhead) to recover `tail_xy`/`head_xy`.
Each endpoint resolves to the nearest node bounding box within a fixed 20px attach tolerance;
resolution failure -> `unresolved_connector_attachment` gap covering `connector-links-correct`
only (not the whole graph).

## Bug Found and Fixed During Implementation

Node label text (rendered achromatic, since labels sit beside the node on white background per
the arrow-v1 label-anchor rationale) has anti-aliased glyph edges that blend black text with the
white background, producing many intermediate gray pixel values. These fell squarely inside the
connector mask's achromatic value band, so every golden case initially produced dozens of tiny
false "connector" noise components and a spurious `degenerate_connector_geometry` gap that forced
`needs_review` even with zero real defects. Narrowing the mask's value range alone did not fix it
(anti-aliasing spans the full 0-255 gradient). Fixed by explicitly blanking each detected node's
label bbox region (`flowchart_labels.node_label_box`) out of the connector mask before running
connected components, rather than trying to tune thresholds around the noise.
[source: mcp-server/src/visual_qa_mcp/flowchart_extractor.py:extract_flowchart_evidence]

## Checks and Findings

| check_id | rule_id | finding types | severity |
|---|---|---|---|
| node-count-matches | flowchart-v1.node-count-matches | node_count_mismatch | high |
| required-nodes-present | flowchart-v1.required-nodes-present | missing_node, extra_node | critical |
| node-shape-correct | flowchart-v1.node-shape-correct | node_shape_wrong | critical |
| node-label-correct (opt-in) | flowchart-v1.node-label-correct | node_label_wrong | high |
| connector-links-correct (opt-in) | flowchart-v1.connector-links-correct | missing_connector, extra_connector | critical/high |

`node-label-correct` is opt-in via at least one node declaring `label_text` in
`source_reference.nodes` plus the check id in `checks[]`. `connector-links-correct` is opt-in via
`source_reference.connectors` plus the check id — both mirror the scenario_type/layout/polyline
gating pattern used by arrow-v1/geometry-v1/coordinate-graph-v1. Either half without the other
becomes a `ClaimGraph` gap -> needs_review.

An unresolved node endpoint in a declared connector edge is skipped per-edge (`continue`), not a
whole-check skip — mirroring coordinate-graph-v1's per-edge polyline pattern. This is proven by a
dedicated test: a plain `missing_node` case must still verdict `fail`, with
`connector-links-correct` staying in `checks_run` (not `checks_skipped`).

Unknown spec checks fall into `ClaimGraph` gaps -> `checks_skipped` -> needs_review, the same
guardrail as the other four verticals.

## Reused Infrastructure

- `VerificationResult` / `ArtifactPaths` / `write_verification_artifacts` (service layer)
- verdict/confidence helpers from `chart_rules.py`
- `arrow_extractor._saturation_mask` (node color-component isolation)
- `spatial.connected_components`, `spatial.bbox_from_points`, `spatial.centroid_from_points`
- arrow-v1/coordinate-graph-v1's color-match + collision-guard pattern (`_match_nodes_by_color`)
- fixed-catalog template-matched label decoding (`flowchart_labels.py`), mirroring
  `arrow_labels.py`'s catalog approach with its own 6-entry catalog
  (`Start, Input, Process, Decision, Output, End`)
- overlay writer, findings/claim-graph schemas, validation summary pattern
- new schema: `specs/flowchart-evidence-graph.schema.json`

## PrimitiveEvidenceGraph Adapter (2026-07-11, session 19)

`primitive_graph_from_flowchart` was added, registering `flowchart-v1` as a fifth supported
primitive profile (`SUPPORTED_PRIMITIVE_PROFILES` in `primitive_evidence.py`,
`specs/primitive-evidence-graph.schema.json`'s `profile` enum). Mapping:

- Rectangle nodes -> `rectangle` primitives; diamond nodes -> `symbol` primitives (the schema's
  fixed primitive-type enum has no dedicated polygon/diamond type, and `symbol` already supports
  bounds-only geometry, matching the existing rectangle/text_region/color_region pattern).
- Node labels -> `text_region` primitives with a `connected_to` relationship back to their node,
  mirroring geometry-v1's dimension-label pattern.
- Connectors -> `arrow` primitives (tail/head geometry, identical shape to arrow-v1's arrow
  primitives) with `touches` relationships to whichever endpoint node(s) resolved during
  extraction (0, 1, or 2 per connector, matching the extractor's own attach-resolution gaps).
- `run_flowchart_verification` and `extract_flowchart_evidence_from_inputs` now populate
  `primitive_graph` (previously deliberately `None` — this closes that scope note from session 17).

Verified: 130 tests pass (128 prior + 2 new: adapter shape/count assertions and profile
dispatch). Controlled flowchart-v1 metrics re-verified unchanged after wiring
(`6/6` typed hits, `2/2` ambiguity guards, `0` unsupported passes).

## Dataset

`datasets/flowchart/flowchart-v1/`: 10 cases = 2 golden + 8 mutated (6 typed + 2 ambiguous).
Golden-01 is a 5-node chain (Start[rect] -> Input[rect] -> Decision[diamond] -> Process[rect] ->
End[rect]) with all labels and connectors declared; golden-02 is a 3-node chain with no label or
connector check requested, proving both opt-in checks can be legitimately absent.

Typed defects: `missing_node`, `extra_node`, `node_shape_wrong` (diamond rendered as rectangle),
`node_label_wrong`, `missing_connector` (declared edge not rendered), `extra_connector` (rendered
edge not declared). Ambiguous: `ambiguous_node_colors` (two nodes share a color), and
`degenerate_node_geometry` (a node shrunk to 12x8px, below the 300px minimum-pixel floor).
[source: mcp-server/src/visual_qa_mcp/flowchart_dataset.py:dataset_cases]

## Validation Result (2026-07-11)

- flowchart-v1 controlled (10 cases): typed hits `6/6`, ambiguous guard `2/2`, node-count evidence
  `9/10` (the 10th case is the deliberately degenerate node, correctly excluded from the node-count
  evidence check since it is never resolved as a node), false unsupported passes `0`, golden
  failures `0`, golden non-passes `0`, verdict mismatches `0`.
- Full test suite: 126 passing (106 prior + 20 new flowchart-focused tests, including one MCP
  tool-list update for the 3 new tools).
- chart-v2, arrow-v1, geometry-v1, and coordinate-graph-v1 controlled metrics were not touched by
  this session's changes (no shared extractor/rule files were modified; the label/connector mask
  fix was entirely local to the new `flowchart_extractor.py`).

## Known Limits

- Exactly two shape types (rectangle, diamond); no ellipse/parallelogram/general polygon shapes.
- Node label catalog is a small fixed alphabet (6 entries); does not generalize to arbitrary text.
- No noisy-image robustness track and no independently authored/real-world images yet.
- Node identity is color-only; two same-colored nodes always route to `needs_review`.
- (Branching/diagonal topology was closed in session 21d — see below.)

## Branching/Diagonal Topology (2026-07-11, session 21d)

Closed the "single vertical chain topology only" item from Known Limits. Advisor gate before
implementation: rendered a throwaway probe (one diamond with two diagonal out-edges to two
rectangles, using ad hoc boundary-intersection anchor points) and ran the existing
`extract_flowchart_evidence` against it *before* writing any dataset/rule code. Both diagonal
connectors were detected correctly with the right `from_node_id`/`to_node_id` and no gaps — the
extractor's `_principal_axis_ends` is a PCA-based direction estimate over the connector's pixels,
not a vertical-specific one, and `connected_components`/`_nearest_node` are already geometry-general.
Likewise `build_flowchart_claim_graph`'s `connector-links-correct` claim and
`flowchart_rules.run_flowchart_claims`'s connector block already operate on an arbitrary
`{from_id, to_id}` edge list, not a linear chain — so **no extractor or rule changes were needed
at all**. The entire feature was one generator change plus dataset/test additions.

### Generator change: boundary-anchored connectors

`flowchart_generator.py` previously hardcoded connector anchors to the "from" node's bottom-center
and the "to" node's top-center — correct only for a strict vertical chain. Replaced with
`_anchor_toward(center, size, shape, target)`, a plain ray/boundary intersection (rectangle:
`min(half_w/|dx|, half_h/|dy|)`; diamond: `1/(|dx|/half_w + |dy|/half_h)`), computed independently
for each end along the line between the two node centers. For a purely vertical edge this reduces
to exactly the old bottom-center/top-center calculation (verified: regenerating the pre-existing
10-case controlled dataset with the new anchor logic reproduced identical validation metrics,
confirming no rendering regression for the existing vertical-chain cases). For a diagonal edge it
produces the correct side/corner anchor on each shape.

### Dataset growth

`datasets/flowchart/flowchart-v1/` grew to 12 cases (3 golden + 9 mutated):
- `golden-03`: one decision (diamond) node with two diagonal out-edges to two rectangle nodes
  (`start -> decision -> {left, right}`), all correct -> pass. Rendered on a widened 620px canvas
  since the default 420px width put the rightmost node's label region (drawn to the node's right,
  per `flowchart_labels.node_label_box`) off-canvas, making it fail to decode purely as a rendering
  artifact of the extra horizontal spread, not an extraction issue.
- `mutated-09` (reuses `missing_connector`): same branching declaration, but only the `left`
  branch connector is rendered -> `missing_connector` for `("decision", "right")`.
- Node labels for the branch nodes reuse the existing fixed 6-entry catalog (`Output`, `End`)
  rather than adding new catalog words, since the catalog itself was out of scope for this feature.

### Validation Result (2026-07-11, session 21d)

- flowchart-v1 controlled (12 cases): typed hits `7/7`, ambiguous guard `2/2`, false unsupported
  passes `0`, golden failures `0`, verdict mismatches `0`.
- Full test suite: 141 passing (139 prior + 2 new: branching-diagram-passes and
  branching-diagram-missing-connector tests; dataset case counts grew inside existing
  dataset-summary tests).

### Updated Known Limits

- Still exactly two shape types, one fixed label catalog, no noisy/real-world track, and
  color-only node identity (unchanged from before this feature).
- Topology is still spec-declared per edge (`source_reference.connectors` is an arbitrary list),
  not inferred; there is no rule yet limiting/validating overall graph shape (e.g., "a diamond
  must have >=2 out-edges").
- No orthogonal/elbow routing — connectors are always straight lines between boundary anchors.
