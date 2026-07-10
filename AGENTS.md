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
6. `wiki/impl-chart-v2-noisy-realworld-pilot.md` when working on chart-v2 readiness, noisy transforms, or the pilot dataset
7. `wiki/impl-arrow-v1-free-body.md` when working on arrows or force balance
8. `wiki/impl-geometry-v1-mechanical.md` when working on mechanical geometry
9. `wiki/impl-primitive-evidence-foundation.md` when working on shared primitives, relationships, or new verticals
10. Any relevant `docs/` or `specs/` file

Then briefly tell the user what context you picked up.

## End Of Session

Update:

- `wiki/project-log.md`
- `wiki/next-steps.md`
- `wiki/index.md` if pages were added or renamed
- `AGENTS.md` and `CLAUDE.md` when the Agent-Guide Maintenance triggers are met

Do this automatically after each meaningful implementation, validation, design decision, blocker, or readiness change; do not wait for the user to request documentation. For a small read-only answer with no new project knowledge, no wiki update is required.

## Important Files

- `docs/problem-map.md` - failure taxonomy.
- `docs/mvp-scope.md` - first practical scope.
- `docs/high-assurance-roadmap.md` - long-term high-risk domain roadmap.
- `docs/validation-plan.md` - how to test the system.
- `wiki/knowledge-product-direction.md` - product framing and research ideas.
- `wiki/knowledge-rules-validators.md` - rule and validator architecture.
- `wiki/knowledge-no-tuning-and-3d.md` - no-tuning strategy and 3D roadmap.
- `specs/visual-spec.schema.json` - expected image structure.
- `specs/claim-graph.schema.json` - checkable claims derived from specs.
- `specs/findings.schema.json` - QA report shape.
- `skills/educational-visual-qa/SKILL.md` - agent workflow draft.
- `mcp-server/tools.md` - planned MCP tool contracts.
- `wiki/impl-chart-v2-noisy-realworld-pilot.md` - noisy hardening and bounded real-world-pilot results.
- `wiki/impl-geometry-v1-mechanical.md` - geometry-v1 design, evidence, validation, and bounds.
- `wiki/impl-primitive-evidence-foundation.md` - shared primitive graph, geometry noisy gate, and composition order.

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
- The deterministic validation baseline comprises 24 controlled cases and 6 configured noisy-transform cases. The observed result is 9/9 controlled and 2/2 noisy typed defects detected, with no golden non-passes or unsupported passes in those sets.
- `chart-v2-realworld-pilot` is a separate, checksum-frozen 24-case pilot of locally rendered Pillow/Matplotlib charts, including a frozen World Bank population-data snapshot. It is pilot evidence only, not a general real-world readiness claim.
- `arrow-v1` is the second executable vertical: a free-body diagram verifier for controlled synthetic diagrams with color-declared and label-declared arrow identity. Validated on a 17-case controlled set (8/8 typed defects, 3/3 ambiguity guard, 0 unsupported passes, 0 golden non-passes) plus a 6-case noisy blur/downscale/JPEG track (4/4 typed defects, 0 unsupported passes). It includes one theory-aware check: opt-in translational force balance (`scenario_type: "equilibrium"` + `force-balance-correct`), which sums extractor pixel vectors and never sums a partial force set. No torque/moment balance, no magnitude calibration, and no real-world images yet. Read `wiki/impl-arrow-v1-free-body.md` when working on arrows.
- `geometry-v1` is the third executable vertical: controlled top-view rectangular mechanical plates with circular holes, relative diameter ratios, declared linear alignment/spacing, and fixed-catalog dimension labels. Its 14-case controlled set records 7/7 typed defects and 2/2 ambiguity guards. Its separate checksum-frozen 20-case noisy track records 10/10 golden passes, 5/5 typed hits, 5/5 ambiguity guards, and 0 unsupported passes across configured blur/downscale/JPEG/low-contrast/label-degradation transforms. It has no independently authored images, general OCR, unit calibration, callout-arrow extraction, or CAD-native validation. Read `wiki/impl-geometry-v1-mechanical.md` when working on geometry.
- `PrimitiveEvidenceGraph` v1 is an additive audit layer for explicit chart/arrow/geometry profiles. It records type-discriminated primitives, relationships, provenance, gaps, and domain traceability. Current domain rules do not consume it; standalone chart primitive parsing stays spec-blind. Read `wiki/impl-primitive-evidence-foundation.md` before changing shared evidence or starting a new vertical.
- The unified 85-test suite passes in about 63 seconds on the milestone machine; chart end-to-end passes 16/16 in about 35 seconds.
- The installable console entrypoint is `visual-qa`; editable local setup is `python -m pip install -e .`.

## Readiness And Claims

- Use advisor review gates for scope/design/readiness decisions on verifier milestones.
- Keep claims bounded to the validated dataset family and configured backend.
- Do not describe optional backends as ready unless they have their own verification and validation results.
- State denominators when reporting metrics for typed defects or ambiguity handling.
- Preserve dataset provenance and checksums for pilot/holdout cases; do not tune thresholds image-by-image after a holdout is frozen.

## Advisor Policy

- Use the least expensive advisor path that materially reduces risk.
- Default to an internal Codex advisor/subagent review for normal scope, design, implementation, debugging, privacy-sensitive, and readiness decisions.
- Use Claude or another cross-model advisor only when the user explicitly requests cross-model review, or when the decision is high impact enough that an independent model perspective adds clear value.
- Before any external advisor review, build a bounded redacted evidence pack and do not share raw secrets, credentials, tokens, keys, personal data, or proprietary source material by default.
- If redaction would remove decision-critical evidence, ask the user before sharing externally.
- Treat advisor output as review input, not authority: reconcile each important claim against local evidence and label disagreements or unknowns clearly.
- Do not require a “stronger” model for advisor review by default; use any advisor path only when it improves decision quality relative to risk, privacy, and reversibility.
- Default coding work (extractors, rules, datasets, tests) runs on Sonnet 5 at moderate effort; that pattern is already established and does not need a stronger model.
- Reserve the top-tier model (Fable 5, or Opus 4.8 if unavailable) for one-time, high-risk design decisions with long-lived consequences (the arrow-v1 force-balance magnitude/equilibrium design was one such gate, resolved 2026-07-10), used as an advisor gate before implementation, not for routine coding.
- Do not upgrade model tier to compensate for an underspecified task; resolve the open design question first, then implement at the default tier.

## Agent-Guide Maintenance

- At the end of each meaningful implementation, validation, or design milestone, assess whether this file and `CLAUDE.md` need updating. When any trigger below is met, update both files in the same task without waiting for a user request.
- Triggers are changes to agent operating instructions, the verified baseline, validation/readiness claims, required session reading, safety boundaries, important commands, or repository structure.
- Do not edit these guides for ordinary progress, refactors, individual experiment results, or metric movement that does not change the operating baseline. Record those details in the wiki and project log instead.
- Keep the two guides consistent where they express shared policy; `AGENTS.md` is the concise execution guide and `CLAUDE.md` is the fuller project memory and workflow reference.
- Agents must create those project-log and next-step records as part of completing qualifying work, without waiting for a user instruction. If no follow-up remains, record that explicitly.

## Safety

- Never mark an image `pass` if required evidence could not be extracted.
- Use `needs_review` when checks are incomplete or ambiguous.
- Keep creator and verifier roles separate: image models may create or edit; Visual QA verifies and reports evidence.
- Do not present automated checks as medical, clinical, or professional engineering certification.
- Do not add private medical, student, or proprietary source data to the repository.
