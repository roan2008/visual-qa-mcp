---
name: knowledge-product-direction
description: Product framing and external research ideas
metadata:
  type: knowledge
  status: current
  last_updated: 2026-07-09
---

# Product Direction

## Plain-Language Framing

Visual QA MCP is a fact-checker for AI-generated technical and knowledge visuals. It checks whether generated charts, diagrams, scientific figures, medical-education visuals, engineering illustrations, and later 3D/CAD visuals are not just visually polished, but correct, traceable, and safe to review. [INFERRED from user discussion and docs/product-brief.md]

The project should be framed as a verification layer, not an image generator and not a generic image scorer. [INFERRED from user discussion]

## Problem

Modern image generation can produce convincing educational and technical visuals, but plausible images can still contain subtle factual errors such as wrong chart values, missing units, reversed arrows, incorrect labels, anatomy laterality mistakes, chemistry/biology relationship errors, or engineering geometry mismatches. [source: docs/problem-map.md]

The risk is highest when the image looks credible enough that reviewers or learners trust it without checking the underlying theory, data, or reference. [INFERRED from user discussion]

## Product Promise

The project should help users answer:

- What was this image supposed to show?
- What evidence was extracted from the image?
- Which visual claims were verified?
- Which claims failed?
- Which checks were skipped because evidence was missing?
- What should be repaired before reuse?

## Research Ideas To Borrow

- Claim decomposition: turn a visual spec into smaller checkable claims. [INFERRED from research discussion around TIFA]
- Chart fact-checking: extract chart evidence and compare it to data or claims. [INFERRED from research discussion around ChartCheck and WebPlotDigitizer]
- Diagram understanding: represent text, arrows, objects, regions, and relations as a scene/evidence graph. [INFERRED from research discussion around AI2D and InfographicVQA]
- Domain validators: extract visual structure first, then validate with symbolic or domain tools such as chemistry validators, CAD geometry tools, or physics rules. [INFERRED from research discussion]
- High-risk audit discipline: record intended use, validation boundary, uncertainty, versioned checks, and human review requirements. [INFERRED from research discussion around medical AI reporting]

## Do Not Copy

- Do not optimize for a single benchmark score as the product value.
- Do not use a vision-language model as the only judge of correctness.
- Do not claim clinical, regulatory, safety, or professional engineering certification.
- Do not try to build a universal verifier before narrow verticals work.

## Strongest Early Demo

The best first demo is likely an AI-generated chart or scientific infographic fact-checker. It should compare a generated image against source data, extract chart evidence, flag mismatched values or units, create an overlay, and produce a repair prompt. [INFERRED from advisor review and user discussion]
