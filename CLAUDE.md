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
mcp-server/ -> planned MCP server contracts and implementation notes
datasets/   -> future golden and mutated-error validation sets
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
5. Read relevant knowledge pages, especially:
   - `wiki/knowledge-product-direction.md`
   - `wiki/knowledge-rules-validators.md`
   - `wiki/knowledge-no-tuning-and-3d.md`
6. Tell the user briefly what context you picked up before starting work

## Session End Protocol

Before ending a session:
1. Update `wiki/project-log.md`
2. Update `wiki/next-steps.md`
3. Add new wiki pages if new knowledge was produced
4. Update `wiki/index.md`

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

## Claim Discipline

- Use advisor gates for verifier scope freeze, implementation freeze, and readiness review.
- Keep milestone language bounded to the validated backend and dataset family.
- Report typed defect recall and ambiguity guard behavior with explicit denominators.
- Prefer `needs_review` over fallback behavior when scale evidence is unreadable, contradictory, or insufficient.

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
