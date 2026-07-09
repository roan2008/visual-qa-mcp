---
name: knowledge-rules-validators
description: Rule and validator architecture concept
metadata:
  type: knowledge
  status: current
  last_updated: 2026-07-09
---

# Rules And Validators

## Role

`run_rules` is the decision layer. It should not judge raw pixels directly. It should compare a structured `VisualSpec` against extracted image evidence such as OCR text, bounding boxes, arrows, chart marks, geometry, labels, objects, and measurements. [INFERRED from user discussion and docs/mvp-scope.md]

The validator layer is responsible for producing findings with evidence, not for hiding uncertainty. Missing required evidence should produce `needs_review` or skipped checks, not `pass`. [source: docs/high-assurance-roadmap.md]

## Core Flow

```text
VisualSpec -> checkable claims
Image -> extractors -> EvidenceGraph / SceneGraph
Claims + EvidenceGraph -> rule validators
Validator results -> findings + verdict + overlay + repair guidance
```

## Rule Registry

A rule registry should define:

- `check_type`
- supported domains
- required evidence objects
- expected parameters
- tolerance model
- severity mapping
- failure modes
- skipped-check reasons
- optional reference requirements

[INFERRED from user discussion]

## Evidence Resolver

Before a rule runs, the system needs to resolve the relevant evidence. For example, a chart-value rule must find the bar for `Feb`; an arrow-direction rule must find the target arrow; a label-target rule must find both the label and the object or region it points to. [INFERRED from user discussion]

## Validator Function

Each validator should be a small deterministic function where possible. Examples:

- Compare extracted bar value to source data within tolerance.
- Compare arrow angle to expected direction within degrees tolerance.
- Compare label text to required label.
- Compare label or callout endpoint to target object distance.
- Count required objects such as holes, arrows, bars, or labels.
- Check alignment, containment, parallelism, or proximity.

[INFERRED from user discussion]

## Verdict Aggregation

The final verdict should be derived from check results:

- Any critical or high required failure can produce `fail`.
- Missing required evidence should produce `needs_review`.
- Minor uncertainty can produce `warning`.
- `pass` is allowed only when required checks ran and evidence is present.

[source: docs/high-assurance-roadmap.md]

## Position And Direction Evidence

The project should explicitly track position and direction evidence:

- bounding boxes
- center points
- arrow start and end points
- direction and angle
- line and circle geometry
- distances
- object counts
- alignment
- containment
- target proximity

[INFERRED from user discussion]
