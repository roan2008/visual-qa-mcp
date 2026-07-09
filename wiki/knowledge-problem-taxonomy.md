---
name: knowledge-problem-taxonomy
description: Visual QA failure categories
metadata:
  type: knowledge
  status: current
  last_updated: 2026-07-09
---

# Problem Taxonomy

## Summary

AI-generated educational visuals can look plausible while being instructionally wrong. The project groups these failures into categories so QA tools can detect them systematically. [source: docs/problem-map.md]

## Key Facts

- Text and label errors include misspellings, incorrect labels, duplicate labels, wrong units, and labels pointing to the wrong object. [source: docs/problem-map.md]
- Spatial relation errors include left/right reversal, inside/outside mismatch, incorrect contact, and misaligned components. [source: docs/problem-map.md]
- Arrow and flow errors include missed targets, reversed arrows, broken paths, wrong causal order, and missing process outputs. [source: docs/problem-map.md]
- Chart and data errors include mismatched bar heights, inconsistent axes, incorrect pie totals, and trend/source-data contradictions. [source: docs/problem-map.md]
- Domain logic errors include physics, engineering, chemistry, biology, and medical errors that require domain-specific checks. [source: docs/problem-map.md]

## Detail

The highest-value project target is not detecting whether an image is AI-generated. The target is checking whether a visual claim is correct enough for its teaching purpose. [source: docs/problem-map.md]

## Open Questions

- [UNVERIFIED - human review needed]: Which initial domain has the strongest user pain and easiest validation path.
