# Visual QA MCP Server

This folder contains callable chart-v2, arrow-v1, and geometry-v1 verifier surfaces plus a thin MCP stdio server.

## Near-Term Tool Surface

- `build_claim_graph`
- `parse_chart`
- `run_rules`
- `verify_chart`
- `build_arrow_claim_graph`, `parse_arrow`, `verify_arrow`
- `build_geometry_claim_graph`, `parse_geometry`, `verify_geometry`
- `make_overlay`

Current bounded scope:

- template-backed bar charts
- controlled free-body arrow diagrams
- controlled mechanical plates with circular holes and fixed-catalog dimension labels
- template backend is the validated default
- optional OCR remains scaffolded and unvalidated

`run_rules` consumes `ClaimGraph` plus extracted evidence so validators operate on explicit checkable claims rather than re-parsing spec details ad hoc.

## Implementation Strategy

Start with simple local tools:

- OCR: Tesseract, PaddleOCR, or cloud OCR if configured by the user.
- Geometry: OpenCV and scikit-image.
- Charts: chart-specific parsing or WebPlotDigitizer-style extraction.
- Objects: open-vocabulary detection where available.
- Rules: deterministic Python functions over extracted scene JSON.

The first server does not need to solve every domain. The current step is to make small evidence-backed chart checks easy for an agent or future MCP wrapper to call.

## Current Callable Prototype

The repository now includes a local callable chart-only surface in:

```text
mcp-server/src/visual_qa_mcp/
```

What it does:

- generates a 24-case chart-v2 validation dataset plus separate noisy and 24-case pilot tracks
- generates chart-v2 `ClaimGraph` artifacts from chart specs
- extracts chart evidence from image-readable axis and tick structure
- runs deterministic chart QA rules
- exposes reusable Python entrypoints for claim generation, evidence extraction, full verification, and artifact writing
- emits schema-valid reports
- creates annotated overlays
- summarizes validation metrics

### Local Commands

Install once from the repository root:

```powershell
python -m pip install -e .
visual-qa generate-geometry-dataset --output datasets\mechanical\geometry-v1
visual-qa run-geometry-validation --dataset datasets\mechanical\geometry-v1
visual-qa verify-geometry datasets\mechanical\geometry-v1\golden\golden-01\image.png datasets\mechanical\geometry-v1\golden\golden-01\visual_spec.json
visual-qa run-arrow-validation --dataset datasets\physics\arrow-v1
visual-qa run-chart-suite-validation --controlled-dataset datasets\charts\chart-v2 --noisy-dataset datasets\charts\chart-v2-noisy --pilot-dataset datasets\charts\chart-v2-realworld-pilot
pytest mcp-server\tests -q
```

## MCP Server Wrapper

The repository now includes a thin MCP stdio server wrapper over the callable chart-v2 surface:

```powershell
visual-qa serve-mcp
```

The MCP wrapper delegates to the existing service layer and does not change verifier behavior. It exposes:

- `build_claim_graph`
- `parse_chart`
- `run_rules`
- `verify_chart`
- `build_arrow_claim_graph`, `parse_arrow`, `verify_arrow`
- `build_geometry_claim_graph`, `parse_geometry`, `verify_geometry`

## Phase 2 Validation

Phase 2 adds:

- audit provenance in `EvidenceGraph`
- stable `rule_id` values in claims/findings
- separate extraction versus rule confidence in reports
- a noisy chart-v2 dataset at `datasets/charts/chart-v2-noisy`
- a checksum-frozen 24-case pilot at `datasets/charts/chart-v2-realworld-pilot`
- an OCR gate that captures dependency availability and reports OCR-specific metrics separately

Current reality is intentionally bounded:

- controlled template-backed chart-v2 still preserves its prior metrics
- noisy chart-v2 now passes its configured six-case gate, but the claim stays bounded to those transform families
- the real-world pilot uses locally rendered Pillow/Matplotlib images and one frozen World Bank source snapshot; it is not general publisher coverage
- optional OCR remains unvalidated and degrades to `needs_review` when unavailable
