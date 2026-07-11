---
name: knowledge-representation-centric-architecture
description: Long-arc architecture direction — structural evidence as the shared verdict core, with rules shrinking to thin domain adapters
metadata:
  type: knowledge
  status: current
  last_updated: 2026-07-11
---

# Representation-Centric Architecture: The Long Arc

Captured from a user design discussion (session 2026-07-11, post covering-array-input-model
implementation). Not yet implemented — this is direction, not a delivered feature. Extends
[knowledge-accuracy-and-synthetic-data-roadmap](knowledge-accuracy-and-synthetic-data-roadmap.md)
and [knowledge-synthetic-coverage-deep-research](knowledge-synthetic-coverage-deep-research.md).

## The question that prompted this

User asked whether the project should move toward a mid-level representation between
language and pixels: generate structured geometry (points, curves, surfaces, regions,
connections, relative positions, distances, angles, constraints) *before* rendering, then
recover the same kind of structural representation from the rendered pixels and diff the
two — with the mathematical structure itself as the reference, rather than per-domain QA
rules.

## Finding: this is already most of the current architecture, not an alternative to it

Mapping the proposed loop (`LLM intent -> geometric representation -> image generation ->
geometry recovery from image -> compare intended vs. recovered -> repair`) onto what
exists:

| Proposed loop stage | Existing project component |
|---|---|
| Intent -> structured representation | `VisualSpec`, declared before rendering (project rule: prefer `visual_spec.json` before image generation) |
| Structured representation -> image | deterministic per-vertical renderers (`chart_generator.py` etc.) |
| Image -> recovered geometry | `EvidenceGraph`, and specifically `PrimitiveEvidenceGraph` — domain-blind points/segments/regions/relationships/provenance |
| Compare intended vs. recovered | rule layer today; `chart_round_trip.py` is literal analysis-by-synthesis (re-render from extracted evidence, compare to source image) |
| Repair | repair-prompt workflow — declared in scope, not yet implemented |

The deep-research ingest's section 8 ("Structural generation: grammar first, layout
second") already recommends the generation-side half of this: generate from a typed
graph/constraint grammar, then deterministic layout/render, so the grammar's production
history *is* exact structural ground truth. The project's long-term CAD-reconstruction
track is the extreme version of the same idea (full CAD model as mathematical reference).

## What would actually change: rules shrink to thin adapters over a generic diff

Today's rule packs are thicker than architecturally necessary — partly an MVP artifact.
Evidence: `PrimitiveEvidenceGraph` v1 already exists and is domain-blind, but current
domain rules do not consume it yet (see `impl-primitive-evidence-foundation.md`). Migrating
rules to primarily do generic structural diffing (declared graph vs. recovered graph) is a
plausible mid-term direction, one vertical at a time.

**What can't be absorbed into a generic diff, and stays domain-specific** even after that
migration:

1. **Tolerance policy** — how close counts as "matching" is a per-claim decision, not a
   geometric fact. Chart-v2's 3%-of-axis-range position tolerance was set from measured
   round-trip pixel error, not a default. A generic differ still needs someone to supply
   tolerance per claim type — a thin rule in a new form.
2. **Correspondence + abstention policy** — before diffing, ambiguous pixel blobs must be
   bound to spec elements (identity resolution), and when binding is ambiguous the correct
   output is `needs_review`, not a guess. This is policy, not geometry, and is exactly what
   keeps the project's zero-unsupported-passes safety property intact.
3. **Theory-aware checks** — a generated image can be *geometrically self-consistent with
   its own declared intent* while being *domain-wrong* (e.g. a free-body diagram whose
   declared equilibrium doesn't actually balance). Geometry-to-geometry diffing against the
   spec would pass this case, because the image matches what was declared — the declared
   intent itself is wrong. `arrow-v1`'s force-balance check exists precisely to catch this
   class. A domain-aware reference (physical law, not just declared shape) is unavoidable
   here.

## End-state sketch

```
universal structural core (primitives + relations + constraints)
        + generic structural diff engine       <- scales across domains
        + thin domain adapters                 <- tolerance, correspondence/abstention, theory checks
```

This differs from the current codebase in degree, not in kind: same layers
(`VisualSpec` -> render -> `EvidenceGraph` -> compare -> findings), but the "compare" step
becomes mostly generic instead of mostly bespoke per vertical.

## Sequencing rationale (why this isn't queued yet)

The mid-term roadmap items (boundary sweeps, failure-mining loop, degradation harness,
selective-prediction reporting, rule-mutation testing — see `next-steps.md`) are
deliberately sequenced *before* any rules-to-generic-diff migration. Reason: those items
make today's claims statistically honest and produce sensitivity/coverage baselines. Without
those baselines, a refactor of the verdict core (migrating rules to consume
`PrimitiveEvidenceGraph`) would have no way to detect whether the safety property (zero
unsupported passes) survived the change. Measure first, then refactor the thing being
measured.

## Suggested long-arc build order (added to `next-steps.md` "Suggested Next Work")

1. Migrate one vertical's rules to consume `PrimitiveEvidenceGraph` as a pilot — flowchart-v1
   is the natural first candidate (already graph-shaped: nodes, connectors, topology).
2. Grammar-based structural generation for at least one vertical, per deep-research
   section 8, so generation and verification share the same structural vocabulary.
3. Only after both above prove out: build the generic declared-vs-recovered structural diff
   engine as the shared verdict core, with per-domain adapters for tolerance,
   correspondence/abstention, and theory-aware checks.

## Honest scope

This page records direction and rationale, not a commitment or a timeline. No code changes
resulted from this discussion. The near-term roadmap (items 1-6 in `next-steps.md`)
remains the active work queue.
