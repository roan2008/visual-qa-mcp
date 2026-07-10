---
name: impl-chart-v2-noisy-realworld-pilot
description: Chart-v2 noisy hardening and bounded real-world pilot evidence
metadata:
  type: implementation
  status: current
  last_updated: 2026-07-10
---

# Chart V2 Noisy Hardening And Real-World Pilot

## Purpose

This milestone fixes deterministic extraction defects exposed by the six-case noisy track and adds a
separate 24-case pilot for renderer diversity and reference-backed data. It does not make chart-v2 a
general real-world chart verifier.

## Hardening

- Blue-channel comparisons use widened integer arithmetic to prevent light-pixel overflow.
- Bar regions require coherent width and row coverage while retaining one-pixel zero-height bars.
- Plot rows use peak evidence and minimum line coverage.
- Tick templates expose calibrated candidates and are reconciled as a visual-only linear sequence;
  expected spec values are never used to rewrite the extracted tick sequence.
- Near-tied sequences remain unresolved instead of falling back to individual digits; detected
  unreadable grid labels therefore force `needs_review`, while a genuinely missing gridline can be
  handled through the remaining linear geometry.
- Axis bounds are compared explicitly with the spec after extraction.
- Label matching supports the validated Arial/DejaVu family and small vertical crop offsets.

## Pilot Contract

`datasets/charts/chart-v2-realworld-pilot/` contains:

- 12 renderer-diverse project-generated cases
- 12 locally rendered cases backed by a frozen 2023 World Bank population snapshot
- per-case provenance, license, renderer, transform family, and optional expected extraction evidence
- `manifest.json` with checksums for images, specs, metadata, and expected reports

The World Bank source is CC BY 4.0. Population totals are rounded to whole millions because the
current validated template tick reader is integer-oriented. The checksum records the canonical
embedded source snapshot, not the raw HTTP response body.

## Verification Boundary

- Controlled: typed `9/9`, golden non-passes `0`, unsupported passes `0`
- Noisy: typed `2/2`, ambiguous guard `2/2`, golden non-passes `0`, verdict mismatches `0`
- Pilot: typed `6/7` (`0.86`), ambiguous guard `7/7`, golden non-passes `0`, unsupported passes `0`
- Pilot extraction: bar `24/24`, tick `16/17`, label `19/20`
- Tests: 43 passed

The pilot supports a claim only about the configured Pillow/Matplotlib renderers, selected blue
palettes, transform families, and the frozen reference snapshot. Independent publisher images,
broader typography/palette coverage, and OCR require separate evidence gates.
