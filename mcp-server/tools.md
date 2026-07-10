# Tool Contracts

The current MCP contracts cover bounded chart-v2, arrow-v1, and geometry-v1 verification. Tool availability does not expand readiness beyond each vertical's separately validated dataset family.

## `build_claim_graph(visual_spec_json)`

Chart-v2 only.

Returns a `ClaimGraph` artifact derived from the provided visual spec.

## `parse_primitives(image_path, profile)`

Returns a spec-blind `PrimitiveEvidenceGraph` for an explicit `chart-v2`, `arrow-v1`, or
`geometry-v1` profile. The graph is an additive audit artifact; current domain rules do not consume
it. Chart parsing exposes low-level candidates and explicit gaps rather than conditioning primitive
evidence on a visual spec.

## `parse_chart(image_path, visual_spec_json, metadata_json?, backend?)`

Chart-v2 only.

Returns an `EvidenceGraph` using the current bounded bar-chart extractor.

- `metadata_json` is optional for callable tool use.
- If required evidence cannot be derived safely, the downstream report must degrade to `needs_review`.
- `backend` remains `template` or `optional_ocr`.

## `run_rules(claim_graph_json, evidence_graph_json)`

Returns a `VisualQaReport`.

Rule execution consumes `ClaimGraph` plus extracted evidence and must preserve skipped-check evidence when required claims cannot be evaluated.
Current outputs also include stable `rule_id` values on findings plus separate extraction and rule confidence at the report level.

## `verify_chart(image_path, visual_spec_json, metadata_json?, backend?)`

Chart-v2 convenience tool.

Returns claim, evidence, and report together in one call so a future MCP wrapper can expose a single end-to-end verification surface.

The MCP stdio wrapper is now implemented for these near-term tools through `python -m visual_qa_mcp.cli serve-mcp`.

## Arrow-v1 MCP Tools

- `build_arrow_claim_graph(spec_path)` builds the arrow claim contract.
- `parse_arrow(image_path)` extracts arrow and object-region evidence.
- `verify_arrow(image_path, spec_path, metadata_path?, output_dir?)` returns claim, evidence, and report artifacts.

These tools retain arrow-v1's controlled/noisy synthetic bounds and do not imply real-world free-body diagram coverage.

## Geometry-v1 MCP Tools

- `build_geometry_claim_graph(spec_path)` builds the mechanical-hole claim contract.
- `parse_geometry(image_path)` extracts the plate, circular holes, measurements, and fixed-catalog labels.
- `verify_geometry(image_path, spec_path, metadata_path?, output_dir?)` returns claim, evidence, and report artifacts.

These tools are bounded to controlled rectangular plate renders. They are not general OCR, arbitrary drawing interpretation, unit calibration, or native CAD inspection.

The separately checksum-frozen geometry noisy track covers only its configured blur, downscale,
JPEG, low-contrast, and label-degradation transforms.

## Validation CLI Surfaces

- `generate-realworld-pilot` builds the 24-case pilot and checksum manifest.
- `run-chart-suite-validation` reports controlled, noisy, and pilot metrics separately and verifies
  the pilot manifest.
- `generate-noisy-geometry-dataset` and `run-geometry-suite-validation` build and validate the
  separate 20-case geometry robustness gate and manifest.

These are local CLI validation surfaces, not additional MCP tools. They do not widen the four MCP
tool contracts or the template-backend readiness boundary.

## `make_overlay(image_path, findings_json)`

Creates an annotated copy of the image with boxes, arrows, and labels showing errors.

## Future Broader Tools

These broader generic contracts remain planned rather than implemented today:

### `ocr_labels(image_path)`

Returns text boxes and confidence scores.

## `detect_arrows(image_path)`

Returns detected arrows, endpoints, direction angles, and confidence scores.

## `detect_geometry(image_path)`

Returns lines, circles, contours, angles, distances, and bounding boxes.

## `parse_chart(image_path)`

Returns axis labels, chart type, extracted marks, estimated values, and parsing confidence.

## `suggest_repair_prompt(findings_json)`

Creates targeted repair instructions for regenerating or editing the image.
