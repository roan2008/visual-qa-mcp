# Visual QA MCP

Visual QA MCP is an early project workspace for building tools that help AI agents verify educational, scientific, medical-education, and engineering visuals before they are used in serious instructional or technical contexts.

The core idea is simple: AI-generated images should be checked like code, and their visual claims should be checked against theory, references, and extracted evidence. A generated diagram, chart, mechanical illustration, anatomy teaching image, or technical visual should have a machine-readable spec, automated checks, visible error evidence, and a human review path for high-risk domains.

## Project Goal

Create a toolchain that helps agents:

- Turn a lesson objective into a structured visual spec.
- Extract text, shapes, arrows, chart data, objects, and geometry from an image.
- Run domain-specific checks against the spec.
- Produce grounded findings with coordinates and evidence.
- Generate an annotated overlay and repair guidance.

## Initial Scope And Long-Term Direction

The first practical scope is educational media where correctness can be measured without model fine-tuning:

- Physics diagrams: force arrows, torque, free-body diagrams, light rays, circuits.
- Charts and infographics: axes, labels, scales, bar heights, pie totals, trend/data consistency.
- Mechanical illustrations: holes, callouts, arrows, geometry, missing or extra parts.

The long-term direction is broader and stricter: medical education, open-ended anatomy, complex chemistry and biology, and full CAD reconstruction are target high-assurance tracks. They require stronger references, theory-aligned rule modules, validation datasets, and expert review before the project can claim readiness for those domains.

See `docs/high-assurance-roadmap.md` for the roadmap toward these harder domains.

## Workspace Layout

```text
docs/
  problem-map.md
  product-brief.md
  mvp-scope.md
  validation-plan.md

specs/
  visual-spec.schema.json
  findings.schema.json
  examples/

skills/
  educational-visual-qa/
    SKILL.md

mcp-server/
  README.md
  tools.md

datasets/
  README.md

experiments/
  README.md
```

## Design Principle

Do not ask a vision model, "Is this correct?" as the only check.

Instead, ask tools to extract evidence, then run checks grounded in specs, theory, source references, and tolerances:

```text
image -> evidence graph -> claim graph -> domain rules -> findings + overlay
```

The agent can still use a vision-language model, but only as one part of an evidence-backed QA loop.

## Current Executable MVP

The current runtime has six bounded executable verticals:

- `chart-v2`: template-backed bar charts with image-read Y-axis scale evidence
- `arrow-v1`: controlled free-body diagrams with arrow identity, direction, anchor, and opt-in translational force balance
- `geometry-v1`: controlled mechanical plates with circular-hole count, relative diameter, linear alignment/spacing, and fixed-catalog dimension labels
- `coordinate-graph-v1`: controlled dual-axis scatter/polyline diagrams
- `flowchart-v1`: controlled rectangle/diamond flowcharts with directed topology
- `circuit-v1`: a two-gate controlled structural-netlist verifier (`v1a` series loops; `v1b` explicit-junction simple-parallel and bounded series-parallel branches)

The first five can also project into an additive `PrimitiveEvidenceGraph` audit layer containing basic
shapes, arrows, text regions, spatial relationships, provenance, and links back to domain evidence.
Domain rules still consume the established domain graphs.

Implemented pieces:

- `EvidenceGraph` schema with tick detections, axis mapping, and bar geometry.
- `ClaimGraph` schema and chart-v2 claim generator so rule execution consumes explicit claims instead of ad hoc spec parsing.
- claim-generation gaps and `claim_graph.json` audit artifacts so unsupported checks degrade to `needs_review` instead of disappearing silently.
- Local callable Python tool surface in `mcp-server/src/visual_qa_mcp/` for claim generation, evidence extraction, verification, and artifact writing.
- MCP server wrapper over chart, arrow, and geometry claim/extraction/verification surfaces.
- Spec-blind `parse_primitives` MCP and `extract-primitives` CLI surfaces for five bounded profiles; circuit evidence remains on its typed domain graph.
- Audit-oriented provenance and confidence separation:
  - extractor provenance in `EvidenceGraph`
  - stable `rule_id` values in claims and findings
  - separate extraction versus rule confidence in `VisualQaReport`
- Dual tick-reader path:
  - default template backend
  - optional OCR backend scaffold
- Validation dataset with 24 cases:
  - 8 golden
  - 16 mutated
- Separate noisy chart-v2 validation dataset for Phase 2 evidence expansion.
- A separate 24-case `chart-v2-realworld-pilot` track with Pillow/Matplotlib renderer diversity,
  World Bank reference-backed source snapshots, provenance/license metadata, and frozen checksums.
- Generic chart source records using `category` / `value`, while retaining compatibility with the
  original `month` / `rainfall_mm` controlled fixtures.
- Overlay generation for flagged findings.
- Verification tests, validation summary artifacts, and advisor-gate evidence packs.

Geometry-v1 has a 14-case controlled Pillow-rendered family (`7/7` typed, `2/2` ambiguity) and a
separate checksum-frozen 20-case noisy family (`5/5` typed, `5/5` ambiguity, `10/10` golden). This
does not cover arbitrary mechanical drawings, independently authored images, general OCR,
calibrated units, or native CAD.

Circuit-v1a has 11 controlled cases (`4/4` typed, `5/5` ambiguity, `2/2` golden,
terminal-netlist evidence `6/6`). Circuit-v1b has 14 controlled cases (`7/7` typed, `3/3`
ambiguity, `4/4` golden, terminal-netlist and junction-count evidence `11/11`). These claims cover
only controlled colored Pillow symbols, orthogonal non-crossing wires, explicit junction dots,
simple parallel, and one bounded series-parallel family. They do not cover arbitrary schematics,
crossings, OCR, electrical values/laws, or engineering certification.

The bounded readiness claim remains narrow: the validated default is the template backend on the
controlled chart-v2 family and the configured noisy transform family. The real-world pilot is an
evidence-expansion track, not proof of general real-world chart readiness. Its public-reference cases
are locally rendered from a frozen World Bank data snapshot; they do not establish robustness across
arbitrary publishers, fonts, palettes, or chart images. OCR remains a separate unvalidated backend.

See `docs/chart-mvp-workflow.md` for the operational workflow and advisor gates.
