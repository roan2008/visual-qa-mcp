---
name: impl-primitive-evidence-foundation
description: Shared primitive evidence, geometry noisy gate, compatibility, and validation bounds
metadata:
  type: implementation
  status: current
  last_updated: 2026-07-10
---

# Primitive Evidence Foundation

## Purpose

This milestone adds an audit-only evidence layer beneath the existing domain graphs:

```text
pixels -> primitives -> relationships -> domain evidence -> claims/rules -> findings
```

`PrimitiveEvidenceGraph` v1 is additive. Chart, arrow, and geometry rules still consume their
existing domain evidence, so the shared graph does not change verdict semantics.

## Contract

The graph records a fixed image-pixel coordinate system, deterministic primitive IDs,
type-discriminated geometry, confidence, source references, relationships, evidence gaps, and
extractor provenance. Supported profiles are `chart-v2`, `arrow-v1`, and `geometry-v1`.

Geometry and arrow profiles adapt their spec-blind extractors. Standalone chart primitive parsing
uses only low-level image detections; it does not use the visual spec to rewrite primitive evidence.
When chart scale semantics cannot be established without a spec, it records an explicit gap.

Verification artifacts now include `primitive_evidence_graph.json`, while the existing
`evidence_graph.json` remains the authoritative domain graph. Domain objects carry additive
`primitive_ids` links for audit traceability.

## Geometry Noisy Gate

`datasets/mechanical/geometry-v1-noisy` is a checksum-frozen 20-case track. Each of blur,
downscale, JPEG, low contrast, and label degradation has two golden, one typed mutated, and one
ambiguity case.

- golden passes: `10/10`
- typed defect hits: `5/5`
- ambiguity guards: `5/5`
- false unsupported passes: `0`
- verdict mismatches: `0`
- manifest: valid `20/20`

These results extend evidence only to the configured deterministic transforms. They do not establish
general mechanical-drawing, publisher-image, OCR, calibrated-unit, or CAD-native readiness.

## Performance And Compatibility

The shared connected-component implementation uses deterministic run-length union-find, and text
templates/fonts are cached. The complete 85-test suite passes in about 63 seconds on the milestone
machine; the 16-test chart end-to-end file passes in about 35 seconds, down from about 4m19s.

Controlled results remain unchanged: chart `9/9`, arrow `8/8`, geometry `7/7`, all with zero false
unsupported passes. The chart pilot remains `6/7` typed hits and is still pilot-only.

## Bounds And Next Composition Order

The primitive graph is an audit representation, not yet a replacement rule input. New verticals are
sequenced as coordinate graphs, flowcharts, then circuits. Each requires its own controlled, noisy,
and independently authored holdout gates before readiness expands.
