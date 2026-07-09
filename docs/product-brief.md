# Product Brief

## Working Name

Visual QA MCP

## One-Line Description

A verification toolchain for AI agents that checks generated educational, scientific, medical-education, and engineering visuals against structured specs, theory-grounded domain rules, source references, and extracted visual evidence.

## Users

- Teachers creating science and engineering materials.
- Medical and anatomy educators preparing teaching visuals.
- Science educators working with chemistry, biology, and process diagrams.
- Technical writers creating manuals and training content.
- Engineering reviewers checking CAD-derived illustrations and technical diagrams.
- Course creators using AI-generated diagrams.
- AI agents generating slides, PDFs, worksheets, and explainers.
- Reviewers who need fast visual error reports.

## Main Jobs To Be Done

- Verify that a generated educational image matches the lesson objective.
- Verify that a visual claim is consistent with theory, source references, and allowed tolerances.
- Catch label, arrow, geometry, chart, and domain-rule errors before publication.
- Produce an overlay that shows exactly where the image is wrong.
- Suggest a repair prompt or edit plan.
- Keep an auditable record of what was checked and what remains uncertain.

## Non-Goals

- Replace expert review in medical or safety-critical domains.
- Fine-tune a foundation model.
- Certify clinical diagnostic images.
- Claim universal correctness for arbitrary images.
- Claim professional engineering, clinical, regulatory, or safety certification without qualified external validation.

## Differentiator

Most image tools focus on generation or visual description. This project focuses on visual correctness, theory alignment, evidence, reference grounding, and QA workflow.

## Key Product Loop

```text
Create visual spec
Generate image
Extract scene structure
Run checks
Review findings
Repair image
Repeat until pass or escalate
```

## First Useful Demo

A generated physics infographic is checked for:

- OCR label accuracy.
- Arrow endpoint accuracy.
- Shape and line detection.
- Chart value consistency.
- Physics rule consistency.

The tool returns:

- `pass`, `warning`, or `fail`.
- A JSON report.
- An annotated image overlay.
- A suggested repair prompt.
