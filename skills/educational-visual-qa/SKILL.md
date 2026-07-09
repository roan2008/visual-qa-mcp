---
name: educational-visual-qa
description: Verify AI-generated educational visuals for science, engineering, medical education, charts, diagrams, and technical illustrations using structured specs, extraction tools, domain rules, and evidence-backed findings.
---

# Educational Visual QA

Use this skill when an agent needs to check whether an educational image is accurate enough for teaching.

## Core Rule

Do not rely on a vision-language model as the only judge. Extract evidence, run checks, and report uncertainty.

## Workflow

1. Identify the domain and risk level.
2. Create or request a `visual_spec.json`.
3. Extract image evidence:
   - OCR labels and units.
   - Arrows and endpoints.
   - Shapes, lines, circles, and geometry.
   - Objects and segmentation masks when available.
   - Chart data when the image is a chart.
4. Run checks against the spec.
5. Produce findings with coordinates, measurements, and skipped checks.
6. Create an annotated overlay when possible.
7. Run validation when building or changing a verifier:
   - `verification` = schemas, deterministic rule tests, fixtures, and end-to-end execution
   - `validation` = defect-catching performance on golden and mutated datasets
8. Use advisor review gates for scope/design/readiness decisions on verifier milestones.
9. Suggest repair instructions.
10. Escalate to human expert review for medical, safety, or professional engineering use.

## Chart V2 Baseline

When the image is a bar chart, the current baseline is chart-v2:

- derive values from Y-axis tick labels and axis mapping, not metadata shortcuts
- support `zero_baseline`, `non_zero_min`, and `signed` within the bounded local dataset family
- treat unreadable or contradictory scale evidence as `needs_review`
- do not claim the optional OCR path is ready unless it has separate validation evidence

## Verdict Rules

- `pass`: Required checks ran and found no blocking issue.
- `warning`: Minor issues or non-critical uncertainty.
- `fail`: A required high or critical check failed.
- `needs_review`: Required evidence could not be extracted or the domain risk is too high for automated release.

## Output Shape

```json
{
  "verdict": "fail",
  "findings": [
    {
      "type": "arrow_target_error",
      "severity": "high",
      "message": "The force arrow does not point downward.",
      "evidence": {
        "arrow_angle_deg": 42,
        "expected_angle_deg": 90,
        "tolerance_deg": 8
      }
    }
  ],
  "checks_skipped": []
}
```

## Medical And Safety Note

Medical, laboratory, and safety-critical visuals must not be released solely on automated checks. Use this skill to reduce error risk and prepare evidence for expert review.
