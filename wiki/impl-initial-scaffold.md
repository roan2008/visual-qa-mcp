---
name: impl-initial-scaffold
description: First project structure and schemas
metadata:
  type: implementation
  status: current
  last_updated: 2026-07-09
---

# Initial Scaffold

## Summary

The first scaffold created project docs, schemas, example specs, MCP planning notes, a draft skill, and agent guidance files.

## Files Created

- `README.md` - overview and design principle.
- `docs/problem-map.md` - visual error taxonomy.
- `docs/product-brief.md` - users, jobs, and product loop.
- `docs/mvp-scope.md` - MVP boundaries and success criteria.
- `docs/validation-plan.md` - golden/mutated dataset plan and metrics.
- `specs/visual-spec.schema.json` - expected visual structure schema.
- `specs/findings.schema.json` - QA report schema.
- `specs/examples/*.json` - physics, chart, and mechanical examples.
- `skills/educational-visual-qa/SKILL.md` - draft agent workflow.
- `mcp-server/README.md` and `mcp-server/tools.md` - planned tool contracts.
- `CLAUDE.md` and `AGENTS.md` - agent operating guidance.
- `wiki/*.md` - project memory.

## Verification

All JSON files were parsed successfully with PowerShell `ConvertFrom-Json` during setup.

## Open Questions

- [UNVERIFIED - human review needed]: Whether to initialize this workspace as a git repository.
- [UNVERIFIED - human review needed]: Which implementation language and MCP SDK version should be used first.
