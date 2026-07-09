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
