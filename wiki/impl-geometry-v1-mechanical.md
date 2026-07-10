---
name: impl-geometry-v1-mechanical
description: geometry-v1 controlled mechanical plate verifier and bounds
metadata:
  type: implementation
  status: current
  last_updated: 2026-07-10
---

# Geometry v1: Controlled Mechanical Plate Verifier

## Purpose

`geometry-v1` is the third executable vertical. It verifies controlled top-view mechanical
plate illustrations using image-extracted plate, circular-hole, relative-diameter, alignment,
spacing, and fixed-catalog dimension-label evidence.

## Checks

- `hole-count-correct`
- `hole-diameter-ratio-correct`
- `hole-alignment-correct`, opt-in when `source_reference.layout = "linear"`
- `dimension-text-correct`

The verifier uses relative diameter ratios rather than pixel-to-unit calibration. Hole identity
is paired left-to-right, then top-to-bottom, and therefore requires the spec hole list to use the
same nominal ordering. Dimension text is template-matched against the closed catalog
`D6, D8, D10, D12, D16, D20`; it is not general OCR.

## Evidence And Guardrails

The extractor is spec-blind. It finds the largest light-gray plate component, detects enclosed
bright circular components as holes, measures their centers and outer ring diameters, and decodes
dimension labels from geometry-derived crop regions. Missing plates, non-circular/merged features,
and unreadable dimension text create explicit evidence gaps. Required checks then become
`needs_review`; they never silently pass.

## Validation Result

The controlled dataset contains 14 locally rendered cases: 5 golden and 9 mutated. Seven mutated
cases have typed expected findings and two exercise ambiguity guards.

- typed defects: `7/7`
- ambiguity guards: `2/2`
- hole-count evidence: `13/13`
- false unsupported passes: `0`
- golden non-passes: `0`
- verdict mismatches: `0`

## Noisy Gate

`datasets/mechanical/geometry-v1-noisy` contains 20 checksum-frozen cases across blur, downscale,
JPEG, low contrast, and dimension-label degradation. Each family has two golden, one typed defect,
and one ambiguity guard.

- golden passes: `10/10`
- typed defect hits: `5/5`
- ambiguity guards: `5/5`
- false unsupported passes: `0`
- manifest: valid `20/20`

## Bounds

This evidence applies only to the controlled Pillow-rendered family and the separately reported
configured noisy transforms: one rectangular plate,
circular through-hole symbols, unobstructed top views, the closed label catalog, and the declared
linear-layout semantics. There is no independently authored dataset, arbitrary OCR, unit calibration,
general line/callout-arrow extraction, CAD-source inspection, or professional engineering
certification claim.
