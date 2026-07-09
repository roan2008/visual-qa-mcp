# MVP Scope

## MVP Name

Educational Visual QA: Chart + Arrow + Geometry

## Why This Scope

This scope avoids fine-tuning and focuses on checks that can be implemented with off-the-shelf OCR, computer vision, and rule logic.

It also produces clear demos:

- A wrong arrow can be visibly shown.
- A chart mismatch can be measured.
- A geometry mismatch can be quantified.

This MVP is a proving ground for the verification loop. It is not the final domain ambition.

## Included Domains

### Physics Diagrams

- Force arrow direction.
- Lever and torque distance.
- Free-body diagram completeness.
- Simple circuit connectivity.
- Ray direction in optics diagrams.

### Charts And Infographics

- Axis label extraction.
- Data label consistency.
- Bar height comparison.
- Pie slice total checks.
- Legend-to-mark consistency.

### Mechanical Callouts

- Hole count.
- Circle and line detection.
- Arrow target accuracy.
- Dimension text extraction.
- Reference image comparison.

## Later High-Assurance Tracks

These areas are intentionally outside the first executable MVP, but they are target tracks for the broader project:

- Medical education and anatomy visuals.
- Open-ended anatomy verification.
- Complex chemistry reaction and molecular diagram validation.
- Complex biology pathway and cell/process validation.
- Full CAD reconstruction and CAD-reference comparison.

These domains require stronger reference sources, theory-aware rule modules, validation datasets, and expert review workflows before any high-confidence claims are made.

## MVP Tools

```text
ocr_labels(image)
detect_arrows(image)
detect_geometry(image)
parse_chart(image)
run_rules(scene_json, visual_spec)
make_overlay(image, findings)
suggest_repair_prompt(findings)
```

## Success Criteria

- Detect at least 80% of injected high-severity errors in a small curated golden set.
- Produce findings with coordinates or measurable evidence.
- Produce overlays that a human reviewer can understand in under 30 seconds.
- Avoid claiming pass when required evidence could not be extracted.
