# Visual QA MCP - Agent Guide

This file mirrors the core project guidance in `CLAUDE.md` for Codex and other coding agents.

## Mission

Build a Visual Verification Runtime for AI-generated educational, scientific, medical-education, and engineering visuals. The project should help agents verify that diagrams, charts, mechanical illustrations, anatomy visuals, chemistry/biology diagrams, and CAD-derived visuals are faithful to their intended teaching use, source references, and relevant theory.

The project is not an image-generation model and does not fine-tune foundation models. It composes existing extractors, deterministic rules, domain validators, audit reports, overlays, and repair prompts into a verification workflow.

## Working Principles

- Evidence first: do not rely on image-model judgment alone.
- Spec first: define the expected visual structure before checking or generating.
- No model tuning: prefer off-the-shelf OCR, computer vision, specialist tools, symbolic validators, and rule packs.
- Theory aligned: visual claims should be checked against equations, references, ontologies, source data, or engineering constraints where available.
- Runtime architecture: turn images into `EvidenceGraph` / `SceneGraph`, turn specs into `ClaimGraph`, then run validators over evidence.
- Narrow MVP, broad ambition: start with charts, arrows, geometry, and simple physics/mechanical checks, then expand toward high-assurance medical, anatomy, chemistry, biology, and CAD tracks.
- 3D path: first verify rendered 3D images, then later support native 3D/CAD sources with geometry-aware validation.
- Safe claims: medical and safety-critical outputs require human expert review.
- Useful outputs: every QA report should include verdict, findings, evidence, skipped checks, and repair guidance.

## Start Of Session

Read these files before making project decisions:

1. `wiki/next-steps.md`
2. `wiki/project-log.md`
3. `wiki/index.md`
4. `README.md`
5. `wiki/impl-chart-v2-axis-scale.md` when working on charts
6. Any relevant `docs/` or `specs/` file

Then briefly tell the user what context you picked up.

## End Of Session

Update:

- `wiki/project-log.md`
- `wiki/next-steps.md`
- `wiki/index.md` if pages were added or renamed

## Important Files

- `docs/problem-map.md` - failure taxonomy.
- `docs/mvp-scope.md` - first practical scope.
- `docs/high-assurance-roadmap.md` - long-term high-risk domain roadmap.
- `docs/validation-plan.md` - how to test the system.
- `wiki/knowledge-product-direction.md` - product framing and research ideas.
- `wiki/knowledge-rules-validators.md` - rule and validator architecture.
- `wiki/knowledge-no-tuning-and-3d.md` - no-tuning strategy and 3D roadmap.
- `specs/visual-spec.schema.json` - expected image structure.
- `specs/findings.schema.json` - QA report shape.
- `skills/educational-visual-qa/SKILL.md` - agent workflow draft.
- `mcp-server/tools.md` - planned MCP tool contracts.

## QA Philosophy

The project is closer to a linter/test runner for educational visuals than a generic image generator.

The target loop is:

```text
lesson objective -> visual spec -> generated image -> evidence graph -> claim graph -> validators -> findings -> overlay -> repair
```

## Current Verified Baseline

- The current executable baseline is `chart-v2`, a bar-chart verifier that derives values from image-read Y-axis scale evidence.
- The validated default backend is the template tick-reader path.
- The optional OCR path is scaffolded infrastructure only until it has separate validation evidence.

## Readiness And Claims

- Use advisor review gates for scope/design/readiness decisions on verifier milestones.
- Keep claims bounded to the validated dataset family and configured backend.
- Do not describe optional backends as ready unless they have their own verification and validation results.
- State denominators when reporting metrics for typed defects or ambiguity handling.

## Safety

- Never mark an image `pass` if required evidence could not be extracted.
- Use `needs_review` when checks are incomplete or ambiguous.
- Keep creator and verifier roles separate: image models may create or edit; Visual QA verifies and reports evidence.
- Do not present automated checks as medical, clinical, or professional engineering certification.
- Do not add private medical, student, or proprietary source data to the repository.
