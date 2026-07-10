# Advisor Review: Primitive Evidence Foundation

## Recommendation

Commit ready after traceability remediation.

Confidence: High  
Action: reversible

## Selection Rationale

Task risk: medium architecture and readiness change  
Advisor engine: internal Codex advisor  
Reason: the milestone changes shared schemas, audit artifacts, validation claims, and all three
executable verticals while keeping repository evidence local.

## Reconciled Findings

- **Agreed:** `PrimitiveEvidenceGraph` is additive and audit-only; domain rules retain their prior
  inputs and verdict semantics.
- **Agreed:** standalone `parse_primitives` is profile-selected and spec-blind. Chart emits low-level
  candidates and explicit gaps rather than spec-conditioned primitive semantics.
- **Agreed:** the geometry noisy claim is bounded to 20 deterministic project-generated cases with
  checksums and separate denominators.
- **Agreed:** cross-graph validation now enforces links for chart bars/axis/ticks, arrow regions/
  arrows, and geometry regions/holes. A typed geometry finding traces through detected domain
  evidence to primitive support.
- **Agreed:** `typing-extensions>=4.14.1` is justified by Pydantic Core package metadata and prevents
  the observed MCP startup failure with an older transitive install.
- **Nuanced:** primitive relationships are adapter interpretations over domain extraction, not an
  independent second geometric proof.
- **Nuanced:** additive JSON fields may affect strict external consumers that reject unknown fields.
- **Nuanced:** circle centers and bounds are checked, but radius-versus-bounds consistency remains a
  future hardening item before accepting externally supplied primitive graphs.

## Validation

- Unified tests: `85/85` passed in 63.16 seconds.
- Chart end-to-end: `16/16` passed in about 35 seconds.
- Geometry noisy: golden `10/10`, typed `5/5`, ambiguity `5/5`, false unsupported passes `0`,
  manifest valid `20/20`.
- Controlled baselines preserved: chart `9/9`, arrow `8/8`, geometry `7/7` typed hits.
- Clean temporary virtual environment installed declared dependencies (`mcp 1.28.1`, NumPy 2.4.6,
  Pillow 11.3.0), imported the package, and ran `extract-primitives` successfully.
- `git diff --check` passed; line-ending warnings only.
