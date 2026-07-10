---
name: impl-chart-v2-claim-graph
description: Chart-v2 ClaimGraph contract and rule-runner integration
metadata:
  type: implementation
  status: current
  last_updated: 2026-07-09
---

# Chart V2 ClaimGraph

## Purpose

This milestone adds an explicit `ClaimGraph` contract for chart-v2 so rule execution consumes checkable claims derived from `VisualSpec` instead of re-parsing the spec inline.

## Scope

The current `ClaimGraph` remains bounded to chart-v2 bar-chart verification and mirrors the already validated check set:

- `bar-values-match-data`
- `bar-count-matches`
- `axis-label-present`
- `axis-unit-present`
- `axis-scale-readable`
- `axis-scale-monotonic`
- `axis-zero-line-resolved` when present in the spec

## Contract Shape

`specs/claim-graph.schema.json` defines a graph with:

- top-level spec/domain/risk metadata
- one claim record per check
- structured gaps for unsupported or unmapped checks
- expected values for each claim
- tolerance fields for numeric comparisons
- evidence requirements for skipped-check handling

For chart-value claims, expected values are grouped by category and include the expected scale mode so the validator can stay spec-driven without hidden metadata shortcuts.

## Runtime Changes

The chart-v2 runtime now:

```text
visual spec -> ClaimGraph -> EvidenceGraph -> rule execution -> report
```

`run_case` writes `claim_graph.json` beside `evidence_graph.json`, `report.json`, and `overlay.png` so each validation case now carries the claim artifact used by the validator.

Unsupported checks no longer disappear silently. They are recorded as claim-generation gaps, surfaced in `checks_skipped`, and force the verdict to `needs_review` so the verifier cannot emit an unsupported pass.

## Readiness Boundary

This change strengthens contract clarity and auditability, but it does not widen the readiness claim:

- template backend remains the only validated backend
- OCR remains scaffolded only
- readiness stays bounded to the existing 24-case chart-v2 dataset family

## Verification

- `pytest mcp-server/tests -q` passes with 23 tests
- `python -m visual_qa_mcp.cli run-validation --dataset datasets/charts/chart-v2` preserves:
  - `critical_error_recall = 1.0`
  - `ambiguous_guard_rate = 1.0`
  - `false_unsupported_passes = 0`
  - `golden_failures = 0`
