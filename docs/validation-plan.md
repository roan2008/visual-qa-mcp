# Validation Plan

## Principle

For educational visuals, false negatives are more dangerous than false positives. The system should prefer "needs review" over a confident but unsupported pass.

## Dataset Plan

### Golden Set

Images known to be correct for a narrow teaching objective.

Each image should include:

- Source or reference material.
- `visual_spec.json`.
- Expected extracted objects.
- Expected checks.

### Mutated Error Set

Copies of golden images with deliberate defects.

Error types:

- Wrong label.
- Missing label.
- Arrow moved to the wrong object.
- Arrow direction reversed.
- Bar height changed.
- Axis unit changed.
- Required object removed.
- Extra hallucinated object added.
- Geometry shifted outside tolerance.

## Metrics

- Critical error recall.
- False negative rate.
- False positive rate.
- Label extraction accuracy.
- Arrow endpoint accuracy.
- Geometry tolerance pass rate.
- Chart data fidelity.
- Human reviewer agreement.

## Review Tiers

### Tier 1: Automated

Use OCR, image processing, parsing, and rules.

### Tier 2: Agent Review

Use a vision-language model to interpret ambiguous findings, but require evidence references.

### Tier 3: Expert Review

Required for medical, safety, lab, and professional engineering content.

## Release Rule

No generated image should be marked `pass` unless required checks were executed and the evidence is present.
