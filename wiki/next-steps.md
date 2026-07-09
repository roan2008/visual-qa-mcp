---
name: next-steps
description: Current priority and queued follow-up work
metadata:
  type: reference
  status: current
  last_updated: 2026-07-09
---

# Next Steps

## Current Priority

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

1. Validate the optional OCR backend with a configured environment instead of only the template backend.
2. Expand beyond the current chart-v2 dataset family toward noisier real generated charts before making stronger generalization claims.
3. Add explicit `ClaimGraph` or claim-generation contracts so rule execution is fully spec-driven end to end.
4. Extend schemas with provenance, rule identifiers, and separate extraction versus rule confidence fields.
5. Turn the chart-v2 functions into first-class MCP tool contracts.
6. Choose the next domain jump: broader chart families or a physics-arrow prototype.

## Recent Completed Milestones

- 2026-07-09: Project scaffold and agent memory files created.
- 2026-07-09: High-assurance domain roadmap added.
- 2026-07-09: Research direction, validator architecture, no-tuning strategy, and 3D roadmap captured.
- 2026-07-09: First executable chart-only MVP implemented with advisor review and validation artifacts.
- 2026-07-09: Chart-v2 axis-scale extraction implemented with dual backend scaffolding and 24-case validation set.
