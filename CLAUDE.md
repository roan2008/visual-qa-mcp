# Visual QA MCP - CLAUDE.md

## Project Goal

Visual QA MCP is a project for building a Visual Verification Runtime: tools, skills, and eventually an MCP server that help AI agents verify educational, scientific, medical-education, and engineering visuals before they are used in serious teaching or technical contexts.

The main deliverable is an evidence-backed, theory-aligned visual QA workflow for science, engineering, chart, mechanical, medical education, anatomy, chemistry, biology, and CAD-derived visuals.

Primary workstreams:
- Visual QA schemas and specs for educational images.
- EvidenceGraph / SceneGraph and ClaimGraph representations.
- MCP-style tools for OCR, arrows, geometry, charts, rules, overlays, and repair prompts.
- Rule packs and domain validators for charts, geometry, physics, mechanical diagrams, and later high-assurance tracks.
- Agent skills and documentation for using the QA workflow safely.
- Validation datasets with golden images and deliberately mutated errors.
- High-assurance domain tracks for medical/anatomy, complex chemistry/biology, and CAD reconstruction once reference standards and expert review workflows exist.

## Repository Structure

```text
wiki/       -> AI-maintained project memory only
docs/       -> project briefs, problem maps, validation plans
specs/      -> JSON schemas and example visual specs
skills/     -> agent skill drafts for educational visual QA
mcp-server/ -> executable Python runtime, MCP contracts, extractors, rules, and tests
datasets/   -> controlled, noisy-transform, and provenance-backed pilot validation sets
experiments/ -> prototypes and throwaway research scripts
```

## Domain Scope

- Educational diagrams for science and engineering.
- Physics diagrams, force arrows, torque, optics, circuits, and free-body diagrams.
- Charts, infographics, axes, labels, scales, marks, and data fidelity.
- Mechanical callouts, holes, alignment, measurements, and part illustrations.
- Biology, chemistry, and medical education visuals as later higher-risk domains.
- Full CAD reconstruction and CAD-reference comparison as a later high-assurance engineering track.
- Agent workflows for visual QA and repair guidance.
- Rendered 3D image verification first, then native 3D/CAD validation later.

## Project-Specific Rules

- Treat generated educational visuals like code that needs linting and tests.
- Prefer `visual_spec.json` before image generation or verification.
- Do not train or fine-tune foundation models for this project.
- Compose off-the-shelf extractors, computer vision, OCR, specialist tools, symbolic/domain validators, and deterministic rule packs.
- Do not use a vision-language model as the only correctness judge.
- Every finding should include evidence such as coordinates, measurements, parsed text, source data, or skipped-check reasons.
- Keep creator and verifier roles separate: image models can generate or repair; Visual QA verifies against evidence, specs, references, and rules.
- Prefer `EvidenceGraph` / `SceneGraph` for extracted image evidence and `ClaimGraph` for checkable claims derived from specs.
- Prefer `needs_review` over an unsupported `pass` when evidence is missing.
- For medical, laboratory, safety, or professional engineering content, automated QA is only a review aid; it is not a release authority.
- Do not claim clinical, diagnostic, regulatory, or professional certification without explicit validation evidence and human expert review.
- Keep MVP scope narrow unless the user explicitly asks to expand it.
- Treat medical/anatomy, complex chemistry/biology, and full CAD reconstruction as long-term target tracks, not permanent exclusions.
- For high-assurance domains, require source references, theory-aware checks, validation evidence, and human expert review paths before making strong correctness claims.

---

## Wiki Role

`wiki/` is project memory for later sessions. It is not the final deliverable.

## Session Start Protocol

Run this every new session:
1. Read `wiki/next-steps.md`
2. Read `wiki/project-log.md`
3. Read `wiki/index.md`
4. Read `wiki/impl-chart-v2-axis-scale.md` when working on charts
5. Read `wiki/impl-chart-v2-noisy-realworld-pilot.md` when working on chart-v2 readiness, noisy transforms, or the pilot dataset
6. Read `wiki/impl-arrow-v1-free-body.md` when working on arrows or force balance
7. Read `wiki/impl-geometry-v1-mechanical.md` when working on mechanical geometry
8. Read relevant knowledge pages, especially:
   - `wiki/knowledge-product-direction.md`
   - `wiki/knowledge-rules-validators.md`
   - `wiki/knowledge-no-tuning-and-3d.md`
7. Tell the user briefly what context you picked up before starting work

## Session End Protocol

Before ending a session:
1. Update `wiki/project-log.md`
2. Update `wiki/next-steps.md`
3. Add new wiki pages if new knowledge was produced
4. Update `wiki/index.md`
5. Assess `AGENTS.md` and this file against the Guide Maintenance Policy; update both automatically when a trigger is met.

Perform this automatically after every meaningful implementation, validation result, design decision, blocker, or readiness change. Do not wait for the user to ask for documentation. A small read-only answer that produces no new project knowledge does not require a wiki update.

## Ingest Workflow

When new files appear in `raw/` or another source folder:
1. Read the relevant raw sources
2. Write wiki notes immediately
3. Update `wiki/index.md`

## Query Workflow

When answering project questions:
1. Open `wiki/index.md` first
2. Read only the relevant pages
3. Answer from the wiki and project files
4. If the wiki does not contain the answer, say so and mark new conclusions as inferred or unverified

## Index Rules

- `wiki/index.md` is an index only
- One line per page: `[title](path.md) - description <= 10 words`
- If the wiki grows beyond 50 pages, split by domain into sub-indexes

## Source Integrity

- Every factual claim in wiki knowledge pages should carry a citation: `[source: file:line]`
- If there is no direct source, mark it `[INFERRED]` and explain why
- If uncertain, mark it `[UNVERIFIED - human review needed]`
- Do not summarize beyond what the source supports

## Write-Early Policy

Capture knowledge immediately after each meaningful step, in this priority order:
1. formulas, constants, units
2. algorithm steps
3. context and provenance

## Current Operating Baseline

- The current executable verifier baseline is `chart-v2`.
- `chart-v2` reads Y-axis scale evidence from the image and derives bar values from that mapping.
- The validated local default is the template backend.
- Optional OCR is a scaffolded backend and must not be included in readiness claims until separately validated.
- The deterministic validation baseline is 24 controlled cases and 6 configured noisy-transform cases. The recorded outcome is 9/9 controlled and 2/2 noisy typed defects detected, with no golden non-passes or unsupported passes in those sets.
- `chart-v2-realworld-pilot` is a separately checksum-frozen 24-case pilot. It contains locally rendered Pillow/Matplotlib charts and charts backed by one frozen World Bank population-data snapshot. It is evidence for a bounded pilot, not proof of general real-world readiness.
- `run-chart-suite-validation` reports controlled, noisy, and pilot summaries. The existing validation command remains the compatibility surface for the original chart dataset.
- `arrow-v1` is the second executable vertical: controlled free-body diagrams with color-declared and label-declared arrow identity, validated on a 17-case controlled set (8/8 typed defects, 3/3 ambiguity guard, 0 unsupported passes) plus a 6-case noisy blur/downscale/JPEG track (4/4 typed defects, 0 unsupported passes). It includes one theory-aware check: opt-in translational force balance (`source_reference.scenario_type = "equilibrium"` plus a `force-balance-correct` check) that sums extractor pixel vectors and refuses to sum a partial force set. It has no torque/moment balance, no magnitude calibration, and no real-world images yet.
- `geometry-v1` is the third executable vertical: controlled rectangular mechanical plates with circular holes, relative diameter-ratio checks, opt-in linear alignment/spacing, and a fixed dimension-label catalog. Its 14-case controlled dataset records 7/7 typed defects, 2/2 ambiguity guards, 13/13 hole-count evidence, 0 unsupported passes, and 0 golden non-passes. It has no noisy/real-world evidence, general OCR, unit calibration, callout-arrow extraction, or native CAD support.
- The MCP wrapper exposes chart, arrow, and geometry claim/extraction/verification tools. The package can be installed locally with `python -m pip install -e .`, which provides the `visual-qa` console command.

## Claim Discipline

- Use advisor gates for verifier scope freeze, implementation freeze, and readiness review.
- Keep milestone language bounded to the validated backend and dataset family.
- Report typed defect recall and ambiguity guard behavior with explicit denominators.
- Prefer `needs_review` over fallback behavior when scale evidence is unreadable, contradictory, or insufficient.
- Keep expected evidence visual-only: never use expected values from `VisualSpec` to resolve ambiguous tick readings.
- Freeze and verify dataset checksums before holdout or pilot validation. Do not adjust thresholds case-by-case to improve frozen-holdout results.

## Model Selection

- Default implementation work (extractors, rules, datasets, tests) uses Sonnet 5 at moderate effort — the coding pattern is already established from chart-v2/arrow-v1 and does not need a stronger model.
- Reserve Fable 5 (or Opus 4.8 if Fable 5 is unavailable) for one-time, high-risk design decisions with long-lived consequences — the arrow-v1 force-balance magnitude-source and equilibrium-gating design was one such gate (resolved 2026-07-10: pixel-vector sums, opt-in `scenario_type`) — via an advisor-style gate before implementation starts, not for routine coding.
- Do not upgrade model tier to compensate for an underspecified task; resolve the design question first, then implement at the default tier.
- Low-effort/high-volume sourcing or curation work (e.g., real-world image gathering) can run at low effort or be delegated to a subagent.

## Guide Maintenance Policy

At the end of every meaningful implementation, validation, or design milestone, assess this policy. Update `AGENTS.md` and this file together automatically—without waiting for a user request—when progress changes agent operating instructions, the verified baseline, a readiness claim, required reading, a safety boundary, an important command, or repository structure. Record normal implementation progress, experiments, and non-baseline metric changes in `wiki/project-log.md` and the relevant implementation page instead. Agents must write these records as part of completing qualifying work, without waiting for a user instruction; explicitly record when no follow-up remains. This keeps the guides stable while preserving project memory in the wiki.

## Wiki Page Types and Naming

Every wiki page must have YAML frontmatter:

```yaml
---
name: kebab-case-slug
description: one-line summary
metadata:
  type: knowledge | implementation | reference | outdated
---
```

Naming:
- `knowledge-*.md` -> theory, algorithms, analysis, results
- `impl-*.md` -> implementation details and design decisions
- `ref-*.md` -> reference data and configs

## Outdated Pages

- Do not delete them
- Mark them as `type: outdated`
- Add a banner that says why the page is outdated and which page replaces it
- Keep outdated pages grouped under "Outdated / Superseded" in `wiki/index.md`

## Wiki Lint

When asked to lint the wiki, flag:
- claims without sources
- orphan pages
- conflicting information
- pages without frontmatter

## Units

Use SI units by default: `Pa`, `m`, `kg`, `N`, `s`, `m/s`.

If a source uses other units, write both, for example: `344,750 Pa (50 psi)`.
