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
image -> extracted scene JSON -> domain rules -> findings + overlay
```

The agent can still use a vision-language model, but only as one part of an evidence-backed QA loop.

## Current Executable MVP

The current runnable prototype is chart-v2: a chart-only verifier for bar charts that derives values from image-read axis scale evidence.

Implemented pieces:

- `EvidenceGraph` schema with tick detections, axis mapping, and bar geometry.
- Local Python extractor and rule runner in `mcp-server/src/visual_qa_mcp/`.
- Dual tick-reader path:
  - default template backend
  - optional OCR backend scaffold
- Validation dataset with 24 cases:
  - 8 golden
  - 16 mutated
- Overlay generation for flagged findings.
- Verification tests, validation summary artifacts, and advisor-gate evidence packs.

See `docs/chart-mvp-workflow.md` for the operational workflow and advisor gates.
