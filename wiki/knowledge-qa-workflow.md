---
name: knowledge-qa-workflow
description: Evidence-backed QA loop
metadata:
  type: knowledge
  status: current
  last_updated: 2026-07-09
---

# QA Workflow

## Summary

Visual QA MCP should verify educational images by extracting evidence, checking it against a structured spec, and returning grounded findings with overlays and repair guidance. [source: README.md]

## Key Facts

- The project should not ask a vision model "Is this correct?" as the only check. [source: README.md]
- The intended workflow is `image -> extracted scene JSON -> domain rules -> findings + overlay`. [source: README.md]
- The MVP focuses on charts, arrows, geometry, and simple physics or mechanical checks. [source: docs/mvp-scope.md]
- A generated image should not be marked `pass` unless required checks were executed and evidence is present. [source: docs/validation-plan.md]

## Detail

The ideal loop is:

```text
lesson objective -> visual spec -> image -> extracted scene -> checks -> findings -> overlay -> repair
```

This makes the system closer to a linter or test runner for educational visuals than a generic image generator. [INFERRED: derived from README.md design principle and docs/mvp-scope.md]

## Open Questions

- [UNVERIFIED - human review needed]: Which extraction tool should be implemented first.
- [UNVERIFIED - human review needed]: Whether the first prototype should be a CLI, MCP server, or plain Python module.
