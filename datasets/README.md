# Datasets

This folder is reserved for small local validation sets.

## Suggested Structure

```text
golden/
  physics/
  charts/
  mechanical/

mutated-errors/
  physics/
  charts/
  mechanical/
```

Each dataset item should include:

- The image.
- A `visual_spec.json`.
- Expected findings.
- Source or reference notes.

## Current Local Dataset

The current dataset lives at:

```text
charts/chart-v2/
```

It contains:

- 8 golden bar-chart cases
- 16 mutated-error bar-chart cases

Each case also includes:

- `metadata.json`
- `expected_report.json`
- generated `report.json`, `evidence_graph.json`, and `overlay.png` after validation runs

Do not add private medical or student data to this repository.

## Phase 2 Tracks

- `charts/chart-v2-noisy/` contains 2 golden and 4 mutated cases for the configured blur,
  resize, JPEG, low-contrast, and optional-OCR transform family.
- `charts/chart-v2-realworld-pilot/` contains 24 pilot-only cases: 12 renderer-diverse cases
  and 12 locally rendered World Bank reference-backed cases.

The pilot manifest freezes image/spec/metadata/expected-report checksums. World Bank population
totals are stored as a dated CC BY 4.0 source snapshot and rounded to whole millions for the current
integer tick-reader boundary. Passing the pilot is not a general real-world readiness claim.

## Arrow And Geometry Tracks

- `physics/arrow-v1/`: 6 golden and 11 mutated controlled free-body cases.
- `physics/arrow-v1-noisy/`: 2 golden and 4 mutated blur/downscale/JPEG cases.
- `mechanical/geometry-v1/`: 5 golden and 9 mutated controlled mechanical plate cases.

Geometry-v1 currently has no noisy or independently sourced track. Its results apply only to the
controlled renderer, circular-hole, ordered-pairing, and fixed-label-catalog family.
