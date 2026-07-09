---
name: knowledge-no-tuning-and-3d
description: No-fine-tuning strategy and 3D roadmap
metadata:
  type: knowledge
  status: current
  last_updated: 2026-07-09
---

# No Tuning And 3D Roadmap

## No Fine-Tuning Strategy

The project should not fine-tune foundation models. Fine-tuning is explicitly a non-goal. [source: docs/product-brief.md]

The project should compose existing tools, extractors, deterministic checks, domain validators, and audit reports into a verification workflow. [INFERRED from user discussion]

Useful components can include:

- OCR engines.
- Computer vision libraries.
- Chart extraction tools.
- Domain validators such as chemistry or CAD tooling.
- Vision-language models as assistants or secondary witnesses.
- Rule packs written for specific domains.
- Golden and mutated datasets for regression testing.

[INFERRED from user discussion and docs/mvp-scope.md]

## Creator Versus Verifier

Image generation models such as GPT Image 2 should be treated as creators or editors. Visual QA MCP should be the verifier that checks generated images against specs, source data, references, and theory. [INFERRED from user discussion]

## 3D Direction

The project can eventually support 3D, but it should distinguish between two cases. [INFERRED from user discussion]

### Rendered 3D Images

Rendered 3D images are still 2D inputs, such as anatomy renders, mechanical part illustrations, molecular screenshots, CAD renders, or exploded views. These can be checked with the same evidence-backed approach, but only for visible information. Hidden geometry may require multiple views or `needs_review`. [INFERRED from user discussion]

### Native 3D Sources

Native 3D files such as STEP, STL, OBJ, GLB, FCStd, CAD assemblies, or molecular 3D structures can support deeper validation because geometry can be measured directly. Future checks may include distances, angles, hole counts, collisions, alignment, assemblies, section views, dimensions, and render consistency. [INFERRED from user discussion]

## 3D Roadmap

1. Prove 2D chart and diagram QA.
2. Add mechanical callout and geometry checks.
3. Validate CAD-rendered images from screenshots.
4. Add multi-view rendered image verification.
5. Accept native 3D files.
6. Validate 3D geometry and render annotated views.

[INFERRED from user discussion]
