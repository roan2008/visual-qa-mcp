# MCP Server Plan

This folder will hold a future MCP server that exposes visual QA tools to agents.

## Planned Tools

- `create_visual_spec`
- `ocr_labels`
- `detect_arrows`
- `detect_geometry`
- `detect_objects`
- `segment_objects`
- `parse_chart`
- `run_rules`
- `make_overlay`
- `suggest_repair_prompt`

## Implementation Strategy

Start with simple local tools:

- OCR: Tesseract, PaddleOCR, or cloud OCR if configured by the user.
- Geometry: OpenCV and scikit-image.
- Charts: chart-specific parsing or WebPlotDigitizer-style extraction.
- Objects: open-vocabulary detection where available.
- Rules: deterministic Python functions over extracted scene JSON.

The first server does not need to solve every domain. It should make small evidence-backed checks easy for an agent to call.

## Current MVP Prototype

The repository now includes a local chart-only MVP in:

```text
mcp-server/src/visual_qa_mcp/
```

What it does:

- generates a 24-case chart-v2 validation dataset
- extracts chart evidence from image-readable axis and tick structure
- runs deterministic chart QA rules
- emits schema-valid reports
- creates annotated overlays
- summarizes validation metrics

### Local Commands

From the repository root:

```powershell
$env:PYTHONPATH='C:\Users\Veerapong Laptop\Documents\Codex\2026-07-09\gi\visual-qa-mcp\mcp-server\src'
python -m visual_qa_mcp.cli generate-dataset --output datasets\charts\chart-v2
python -m visual_qa_mcp.cli run-validation --dataset datasets\charts\chart-v2
pytest mcp-server\tests -q
```

This is a prototype, not yet an MCP server process. The current implementation is intentionally narrow and tuned for the controlled-to-semi-realistic chart-v2 dataset family.
