# Tool Contracts

## `ocr_labels(image_path)`

Returns text boxes and confidence scores.

## `detect_arrows(image_path)`

Returns detected arrows, endpoints, direction angles, and confidence scores.

## `detect_geometry(image_path)`

Returns lines, circles, contours, angles, distances, and bounding boxes.

## `parse_chart(image_path)`

Returns axis labels, chart type, extracted marks, estimated values, and parsing confidence.

## `run_rules(scene_json, visual_spec_json)`

Compares extracted evidence to the visual spec and returns a QA report.

## `make_overlay(image_path, findings_json)`

Creates an annotated copy of the image with boxes, arrows, and labels showing errors.

## `suggest_repair_prompt(findings_json)`

Creates targeted repair instructions for regenerating or editing the image.
