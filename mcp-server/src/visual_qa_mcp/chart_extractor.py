from __future__ import annotations

import json
from pathlib import Path
from statistics import mean
from typing import Any

import numpy as np
from PIL import Image, ImageChops, ImageDraw, ImageStat

from .chart_layout import ChartLayout
from .chart_generator import BACKGROUND_COLOR, get_font
from .contracts import AxisMapping, EvidenceGap, EvidenceGraph, ExtractedAxis, ExtractedBar
from .tick_reader import read_tick_texts


def _load_image(path: Path) -> Image.Image:
    return Image.open(path).convert("RGB")


def _render_text(text: str, size: tuple[int, int], font_size: int) -> Image.Image:
    image = Image.new("RGB", size, BACKGROUND_COLOR)
    draw = ImageDraw.Draw(image)
    font = get_font(font_size)
    bbox = draw.textbbox((0, 0), text, font=font)
    x = (size[0] - (bbox[2] - bbox[0])) / 2
    y = (size[1] - (bbox[3] - bbox[1])) / 2
    draw.text((x, y), text, fill=(25, 25, 25), font=font)
    return image


def _difference_score(image_a: Image.Image, image_b: Image.Image) -> float:
    diff = ImageChops.difference(image_a.convert("L"), image_b.convert("L"))
    return float(ImageStat.Stat(diff).mean[0])


def _normalize_foreground(image: Image.Image, size: tuple[int, int] = (92, 26)) -> np.ndarray | None:
    gray = np.array(image.convert("L"))
    binary = gray < 225
    coords = np.argwhere(binary)
    if len(coords) == 0:
        return None
    min_row, min_col = coords.min(axis=0)
    max_row, max_col = coords.max(axis=0)
    crop = Image.fromarray((binary[min_row : max_row + 1, min_col : max_col + 1].astype(np.uint8) * 255))
    resized = crop.resize(size)
    return (np.array(resized) > 127).astype(float)


def _match_text(crop: Image.Image, candidates: list[str], font_size: int = 16, threshold: float = 0.72) -> tuple[str | None, float]:
    if not candidates:
        return None, 0.0
    normalized_crop = _normalize_foreground(crop)
    if normalized_crop is None:
        return None, 0.0
    scores: list[tuple[str, float]] = []
    for candidate in candidates:
        template = _render_text(candidate, crop.size, font_size)
        normalized_template = _normalize_foreground(template)
        if normalized_template is None:
            continue
        score = float(np.mean(np.abs(normalized_crop - normalized_template)))
        scores.append((candidate, score))
    best_text, best_score = min(scores, key=lambda item: item[1])
    confidence = max(0.0, 1.0 - min(best_score * 1.8, 1.0))
    if confidence < threshold:
        return None, confidence
    return best_text, round(confidence, 2)


def _to_np(image: Image.Image) -> np.ndarray:
    return np.array(image)


def _intensity(rgb: np.ndarray) -> np.ndarray:
    return rgb.mean(axis=2)


def _saturation(rgb: np.ndarray) -> np.ndarray:
    return rgb.max(axis=2) - rgb.min(axis=2)


def _blue_bar_mask(rgb: np.ndarray) -> np.ndarray:
    intensity = _intensity(rgb)
    return (
        (rgb[:, :, 2] > rgb[:, :, 1] + 15)
        & (rgb[:, :, 2] > rgb[:, :, 0] + 15)
        & (intensity < 250)
    )


def _line_mask(rgb: np.ndarray) -> np.ndarray:
    intensity = _intensity(rgb)
    saturation = _saturation(rgb)
    return (saturation < 42) & (intensity < 245)


def _dark_mask(rgb: np.ndarray) -> np.ndarray:
    intensity = _intensity(rgb)
    return intensity < 110


def _cluster_indices(indices: list[int]) -> list[list[int]]:
    if not indices:
        return []
    clusters = [[indices[0]]]
    for index in indices[1:]:
        if index - clusters[-1][-1] <= 2:
            clusters[-1].append(index)
        else:
            clusters.append([index])
    return clusters


def detect_plot_area(rgb: np.ndarray) -> dict[str, int | list[int]]:
    dark = _dark_mask(rgb)
    line = _line_mask(rgb)
    height, width = dark.shape
    left_half = width // 2
    column_scores = dark[:, 18:left_half].sum(axis=0)
    axis_line_x = int(np.argmax(column_scores) + 18)

    row_scores = line[:, axis_line_x + 4 : width - 20].sum(axis=1)
    threshold = max(int((width - axis_line_x) * 0.16), 70)
    candidate_rows = [idx for idx, score in enumerate(row_scores.tolist()) if score >= threshold]
    row_clusters = _cluster_indices(candidate_rows)
    tick_rows: list[int] = []
    for cluster in row_clusters:
        row = int(round(sum(cluster) / len(cluster)))
        active = np.where(line[row, axis_line_x + 2 :])[0]
        if len(active) == 0:
            continue
        span = int(active[-1] - active[0])
        if span < int((width - axis_line_x) * 0.55):
            continue
        tick_rows.append(row)
    if len(tick_rows) < 2:
        return {
            "axis_line_x": axis_line_x,
            "plot_top": 0,
            "plot_bottom": height - 1,
            "plot_right": width - 1,
            "tick_rows": tick_rows,
        }

    plot_top = min(tick_rows)
    plot_bottom = max(tick_rows)
    last_positions: list[int] = []
    for row in tick_rows:
        active = np.where(line[row, axis_line_x + 2 :])[0]
        if len(active) > 0:
            last_positions.append(int(axis_line_x + 2 + active[-1]))
    plot_right = max(last_positions) if last_positions else width - 1
    return {
        "axis_line_x": axis_line_x,
        "plot_top": plot_top,
        "plot_bottom": plot_bottom,
        "plot_right": plot_right,
        "tick_rows": tick_rows,
    }


def extract_tick_candidates(image: Image.Image, plot_info: dict[str, int | list[int]]) -> list[tuple[Image.Image, list[int]]]:
    axis_x = int(plot_info["axis_line_x"])
    candidates: list[tuple[Image.Image, list[int]]] = []
    for tick_y in plot_info["tick_rows"]:  # type: ignore[index]
        top = max(0, int(tick_y) - 13)
        bottom = min(image.height, int(tick_y) + 13)
        left = max(0, axis_x - 96)
        right = max(left + 10, axis_x - 10)
        bbox = [left, top, right, bottom]
        candidates.append((image.crop(tuple(bbox)), bbox))
    return candidates


def infer_axis_mapping(
    tick_detections: list,
    plot_info: dict[str, int | list[int]],
    expected_axis_mode: str,
) -> tuple[AxisMapping | None, int | None, int | None, list[EvidenceGap]]:
    gaps: list[EvidenceGap] = []
    ordered = sorted(tick_detections, key=lambda tick: (tick.bbox[1] + tick.bbox[3]) / 2)
    readable = [tick for tick in ordered if tick.parsed_value is not None]
    if len(readable) < 3:
        gaps.append(
            EvidenceGap(
                code="insufficient_tick_evidence",
                message="Insufficient readable tick labels to derive a stable axis scale.",
                check_ids=["axis-scale-readable", "axis-scale-monotonic", "bar-values-match-data"],
            )
        )
        if expected_axis_mode == "signed":
            gaps.append(
                EvidenceGap(
                    code="axis_zero_line_unresolved",
                    message="Signed axis requires a readable zero tick or resolvable zero line.",
                    check_ids=["axis-zero-line-resolved", "bar-values-match-data"],
                )
            )
        return None, None, None, gaps

    values = [float(tick.parsed_value) for tick in readable]
    centers = [((tick.bbox[1] + tick.bbox[3]) / 2) for tick in readable]

    if any(values[index] <= values[index + 1] for index in range(len(values) - 1)):
        gaps.append(
            EvidenceGap(
                code="non_monotonic_tick_values",
                message="Tick values are not strictly monotonic from top to bottom.",
                check_ids=["axis-scale-monotonic", "bar-values-match-data"],
            )
        )
        return None, None, None, gaps

    deltas = [abs(values[index] - values[index + 1]) for index in range(len(values) - 1)]
    if any(abs(delta - deltas[0]) > 0.01 for delta in deltas[1:]):
        gaps.append(
            EvidenceGap(
                code="inconsistent_tick_step",
                message="Tick values do not follow a consistent numeric step.",
                check_ids=["axis-scale-monotonic", "bar-values-match-data"],
            )
        )
        return None, None, None, gaps

    pixel_deltas = [abs(centers[index] - centers[index + 1]) for index in range(len(centers) - 1)]
    if any(delta <= 0 for delta in pixel_deltas):
        gaps.append(
            EvidenceGap(
                code="invalid_tick_geometry",
                message="Tick geometry could not be converted into a stable pixel-per-unit mapping.",
                check_ids=["axis-scale-readable", "bar-values-match-data"],
            )
        )
        return None, None, None, gaps

    pixels_per_unit = float(mean(pixel / value for pixel, value in zip(pixel_deltas, deltas, strict=True)))
    axis_min = min(values)
    axis_max = max(values)
    scale_mode = "signed" if axis_min < 0 < axis_max else ("zero_baseline" if axis_min == 0 else "non_zero_min")
    zero_line_y = None
    if scale_mode == "signed":
        zero_ticks = [tick for tick in readable if tick.parsed_value == 0]
        if not zero_ticks:
            gaps.append(
                EvidenceGap(
                    code="axis_zero_line_unresolved",
                    message="Signed axis requires a readable zero tick or resolvable zero line.",
                    check_ids=["axis-zero-line-resolved", "bar-values-match-data"],
                )
            )
            return None, None, None, gaps
        zero_line_y = int(round((zero_ticks[0].bbox[1] + zero_ticks[0].bbox[3]) / 2))

    mapping = AxisMapping(
        min_value=axis_min,
        max_value=axis_max,
        pixels_per_unit=round(pixels_per_unit, 4),
        scale_mode=scale_mode,
        value_direction="positive_up",
        readable=True,
    )
    baseline_y = int(round(max(centers)))
    return mapping, baseline_y, zero_line_y, gaps


def _pixel_to_value(pixel_y: int, baseline_y: int, mapping: AxisMapping) -> float:
    return round(mapping.min_value + ((baseline_y - pixel_y) / mapping.pixels_per_unit), 2)


def _find_bar_regions(rgb: np.ndarray, plot_info: dict[str, int | list[int]]) -> list[list[int]]:
    bar_mask = _blue_bar_mask(rgb)
    axis_x = int(plot_info["axis_line_x"])
    plot_top = int(plot_info["plot_top"])
    plot_bottom = int(plot_info["plot_bottom"])
    plot_right = int(plot_info["plot_right"])
    regions: list[list[int]] = []
    in_region = False
    start_x = 0
    region_top = plot_bottom
    region_bottom = plot_top
    for x in range(axis_x + 6, plot_right):
        ys = np.where(bar_mask[plot_top : plot_bottom + 1, x])[0]
        if len(ys) > 0:
            y_top = int(plot_top + ys.min())
            y_bottom = int(plot_top + ys.max())
            if not in_region:
                start_x = x
                in_region = True
                region_top = y_top
                region_bottom = y_bottom
            else:
                region_top = min(region_top, y_top)
                region_bottom = max(region_bottom, y_bottom)
        elif in_region:
            regions.append([start_x, region_top, x - 1, region_bottom])
            in_region = False
    if in_region:
        regions.append([start_x, region_top, plot_right - 1, region_bottom])

    merged: list[list[int]] = []
    for region in regions:
        if merged and region[0] - merged[-1][2] <= 2:
            merged[-1][2] = region[2]
            merged[-1][1] = min(merged[-1][1], region[1])
            merged[-1][3] = max(merged[-1][3], region[3])
        else:
            merged.append(region)
    return merged


def _derive_bar_value(
    region: list[int],
    mapping: AxisMapping | None,
    baseline_y: int | None,
    expected_axis_mode: str,
    zero_line_y: int | None,
) -> tuple[float | None, int | None, int | None]:
    top_y = region[1]
    bottom_y = region[3]
    if mapping is None or baseline_y is None:
        return None, top_y, bottom_y

    if mapping.scale_mode == "signed" or expected_axis_mode == "signed":
        if zero_line_y is None:
            return None, top_y, bottom_y
        if abs(bottom_y - zero_line_y) <= 8:
            return _pixel_to_value(top_y, baseline_y, mapping), top_y, bottom_y
        if abs(top_y - zero_line_y) <= 8:
            return _pixel_to_value(bottom_y, baseline_y, mapping), top_y, bottom_y
        return None, top_y, bottom_y

    return _pixel_to_value(top_y, baseline_y, mapping), top_y, bottom_y


def extract_chart_evidence(image_path: Path, spec_path: Path, metadata_path: Path, backend: str | None = None) -> EvidenceGraph:
    image = _load_image(image_path)
    rgb = _to_np(image)
    spec = json.loads(spec_path.read_text(encoding="utf-8"))
    metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
    backend = backend or metadata.get("backend", "template")

    source_data = spec.get("source_reference", {}).get("data", [])
    expected_categories = [item["month"] for item in source_data]
    expected_axis_mode = spec.get("source_reference", {}).get("axis", {}).get("expected_scale_mode", "zero_baseline")
    candidate_units = ["mm", "cm", "kg", "N"]

    plot_info = detect_plot_area(rgb)
    tick_candidates = extract_tick_candidates(image, plot_info)
    tick_detections, backend_available = read_tick_texts(tick_candidates, backend=backend)
    mapping, baseline_y, zero_line_y, gaps = infer_axis_mapping(tick_detections, plot_info, expected_axis_mode)

    if backend == "optional_ocr" and not backend_available:
        gaps.append(
            EvidenceGap(
                code="optional_ocr_unavailable",
                message="Optional OCR backend is not configured in the current environment.",
                check_ids=["axis-scale-readable", "axis-scale-monotonic", "bar-values-match-data"],
            )
        )

    bar_regions = _find_bar_regions(rgb, plot_info)
    bars: list[ExtractedBar] = []
    layout_hint = ChartLayout()
    layout_overrides = metadata.get("render_options", {}).get("layout_overrides", {})
    if layout_overrides:
        layout_hint = layout_hint.with_overrides(**layout_overrides)
    for index, region in enumerate(bar_regions):
        center_x = (region[0] + region[2]) // 2
        crop_box = layout_hint.label_box(center_x)
        label_crop = image.crop(tuple(crop_box))
        matched_label, label_confidence = _match_text(label_crop, expected_categories, font_size=14, threshold=0.55)
        value, top_y, bottom_y = _derive_bar_value(region, mapping, baseline_y, expected_axis_mode, zero_line_y)
        bars.append(
            ExtractedBar(
                bar_id=f"bar-{index + 1}",
                category=matched_label,
                value=value,
                bbox=region,
                confidence=round((0.72 + label_confidence) / 2, 2),
                matched_label=matched_label,
                top_y=top_y,
                bottom_y=bottom_y,
                value_source="axis_mapping",
            )
        )
        if matched_label is None:
            gaps.append(
                EvidenceGap(
                    code="missing_bar_label",
                    message=f"Unable to confidently match x-axis label for bar {index + 1}.",
                    check_ids=["bar-values-match-data"],
                )
            )
        if value is None:
            gaps.append(
                EvidenceGap(
                    code="bar_value_unresolved",
                    message=f"Unable to derive a stable numeric value for bar {index + 1} from axis mapping.",
                    check_ids=["bar-values-match-data"],
                )
            )

    if len(bar_regions) != len(expected_categories):
        gaps.append(
            EvidenceGap(
                code="bar_count_mismatch",
                message=f"Detected {len(bar_regions)} bars but expected {len(expected_categories)}.",
                check_ids=["bar-count-matches"],
            )
        )

    axis_crop_box = list(layout_hint.axis_label_box)
    axis_crop = image.crop(tuple(axis_crop_box))
    expected_axis_text = next(
        (label["text"] for label in spec.get("labels", []) if label.get("target") == "y_axis"),
        "",
    )
    unit_candidates = [expected_axis_text]
    if "(" in expected_axis_text and ")" in expected_axis_text:
        prefix = expected_axis_text.split("(")[0].strip()
        unit_candidates.extend(f"{prefix} ({unit})" for unit in candidate_units if f"{prefix} ({unit})" != expected_axis_text)
    matched_axis_text, axis_confidence = _match_text(axis_crop, unit_candidates, font_size=16, threshold=0.55)
    unit_text = None
    if matched_axis_text and "(" in matched_axis_text and ")" in matched_axis_text:
        unit_text = matched_axis_text.split("(")[1].split(")")[0]
    if matched_axis_text is None:
        gaps.append(
            EvidenceGap(
                code="missing_axis_label",
                message="Unable to confidently match the y-axis label text.",
                check_ids=["axis-label-present", "axis-unit-present"],
            )
        )

    if mapping is None:
        gaps.append(
            EvidenceGap(
                code="axis_scale_unreadable",
                message="Axis scale could not be derived from the available tick evidence.",
                check_ids=["axis-scale-readable", "bar-values-match-data"],
            )
        )

    evidence = EvidenceGraph(
        image_id=metadata["image_id"],
        chart_type="bar",
        bars=bars,
        x_axis_labels=[bar.category for bar in bars],
        y_axis=ExtractedAxis(
            label_text=matched_axis_text,
            unit_text=unit_text,
            label_bbox=axis_crop_box,
            confidence=round(axis_confidence, 2),
            tick_labels=tick_detections,
            axis_line_x=int(plot_info["axis_line_x"]),
            baseline_y=baseline_y,
            top_y=int(plot_info["plot_top"]),
            zero_line_y=zero_line_y,
            mapping=mapping,
            backend=backend,
        ),
        extraction_confidence=round(
            mean(
                [axis_confidence]
                + [tick.confidence for tick in tick_detections]
                + [bar.confidence for bar in bars]
            ) if tick_detections or bars else axis_confidence,
            2,
        ),
        gaps=gaps,
        metadata={
            "chart_version": metadata.get("chart_version", "v2"),
            "axis_mode": metadata.get("axis_mode", expected_axis_mode),
            "dataset_case": metadata.get("case_id"),
            "backend": backend,
        },
    )
    return evidence
