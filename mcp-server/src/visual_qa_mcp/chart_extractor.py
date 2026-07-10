from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path
from statistics import mean
from typing import Any

import numpy as np
from PIL import Image, ImageChops, ImageDraw, ImageFont, ImageStat

from .chart_layout import ChartLayout
from .chart_generator import BACKGROUND_COLOR, get_font
from .contracts import AxisMapping, EvidenceGap, EvidenceGraph, ExtractedAxis, ExtractedBar, ExtractionProvenance
from .environment import capture_ocr_environment, capture_runtime_dependencies
from .tick_reader import read_tick_texts


def _source_category(item: dict[str, Any]) -> str:
    value = item.get("category", item.get("month"))
    if value is None:
        raise ValueError("Chart source data item is missing 'category' (or legacy 'month').")
    return str(value)


def _load_image(path: Path) -> Image.Image:
    return Image.open(path).convert("RGB")


def _render_text(
    text: str,
    size: tuple[int, int],
    font_size: int,
    font_name: str | None = None,
) -> Image.Image:
    image = Image.new("RGB", size, BACKGROUND_COLOR)
    draw = ImageDraw.Draw(image)
    try:
        font = ImageFont.truetype(font_name, font_size) if font_name else get_font(font_size)
    except OSError:
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


@lru_cache(maxsize=4096)
def _normalized_text_template(
    text: str,
    size: tuple[int, int],
    font_size: int,
    font_name: str | None,
) -> np.ndarray | None:
    return _normalize_foreground(_render_text(text, size, font_size, font_name=font_name))


def _match_text(crop: Image.Image, candidates: list[str], font_size: int = 16, threshold: float = 0.72) -> tuple[str | None, float]:
    if not candidates:
        return None, 0.0
    normalized_crop = _normalize_foreground(crop)
    if normalized_crop is None:
        return None, 0.0
    scores: list[tuple[str, float]] = []
    for candidate in candidates:
        candidate_scores: list[float] = []
        for template_size in sorted({max(10, font_size - 2), font_size, font_size + 2}):
            for font_name in (None, "DejaVuSans.ttf"):
                normalized_template = _normalized_text_template(
                    candidate,
                    crop.size,
                    template_size,
                    font_name,
                )
                if normalized_template is not None:
                    candidate_scores.append(float(np.mean(np.abs(normalized_crop - normalized_template))))
        if candidate_scores:
            scores.append((candidate, min(candidate_scores)))
    if not scores:
        return None, 0.0
    scores.sort(key=lambda item: item[1])
    best_text, best_score = scores[0]
    runner_up_score = scores[1][1] if len(scores) > 1 else 1.0
    winner_margin = runner_up_score - best_score
    confidence = max(0.0, 1.0 - min(best_score * 1.55, 1.0))
    quality_limit = min(0.34, max(0.24, (1.0 - threshold) / 1.4))
    quality_ok = best_score <= quality_limit
    margin_ok = len(scores) == 1 or winner_margin >= 0.012
    if not quality_ok or not margin_ok:
        return None, confidence
    return best_text, round(confidence, 2)


def _to_np(image: Image.Image) -> np.ndarray:
    return np.array(image)


def _intensity(rgb: np.ndarray) -> np.ndarray:
    return rgb.mean(axis=2)


def _saturation(rgb: np.ndarray) -> np.ndarray:
    return rgb.max(axis=2) - rgb.min(axis=2)


def _blue_bar_mask(rgb: np.ndarray) -> np.ndarray:
    # Widen before adding the channel margin. Adding 15 to uint8 values can
    # wrap light gray pixels back toward zero and classify JPEG/grid artifacts
    # as saturated blue.
    widened = rgb.astype(np.int16)
    intensity = widened.mean(axis=2)
    return (
        (widened[:, :, 2] > widened[:, :, 1] + 15)
        & (widened[:, :, 2] > widened[:, :, 0] + 15)
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
    vertical_indices = np.where(dark[:, axis_line_x])[0].tolist()
    vertical_clusters = _cluster_indices(vertical_indices)
    if vertical_clusters:
        axis_vertical = max(vertical_clusters, key=len)
        axis_top = axis_vertical[0]
        axis_bottom = axis_vertical[-1]
    else:
        axis_top = 0
        axis_bottom = height - 1

    row_scores = line[:, axis_line_x + 4 : width - 20].sum(axis=1)
    threshold = max(int((width - axis_line_x) * 0.16), 70)
    candidate_rows = [idx for idx, score in enumerate(row_scores.tolist()) if score >= threshold]
    row_clusters = _cluster_indices(candidate_rows)
    tick_rows: list[int] = []
    minimum_line_coverage = 0.28
    available_span = max(width - (axis_line_x + 2), 1)
    for cluster in row_clusters:
        # Resampling often produces a two-row grid line. The rounded cluster
        # midpoint can be the blank row between them, so use the strongest row.
        row = max(cluster, key=lambda index: int(row_scores[index]))
        if row < axis_top - 3 or row > axis_bottom + 3:
            continue
        active = np.where(line[row, axis_line_x + 2 :])[0]
        if len(active) == 0:
            continue
        coverage = len(active) / available_span
        if coverage < minimum_line_coverage:
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
    if len(readable) < 3 or len(readable) != len(ordered):
        gaps.append(
            EvidenceGap(
                code="insufficient_tick_evidence",
                message="Every detected gridline requires a readable tick label before deriving the axis scale.",
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

    value_fit = np.polyfit(np.array(centers, dtype=float), np.array(values, dtype=float), 1)
    predicted_values = value_fit[0] * np.array(centers, dtype=float) + value_fit[1]
    value_span = max(max(values) - min(values), 5.0)
    normalized_residual = float(
        np.sqrt(np.mean((predicted_values - np.array(values, dtype=float)) ** 2)) / value_span
    )
    if value_fit[0] >= 0 or normalized_residual > 0.02:
        gaps.append(
            EvidenceGap(
                code="inconsistent_tick_step",
                message="Tick values and pixel positions do not support a consistent linear scale.",
                check_ids=["axis-scale-monotonic", "bar-values-match-data"],
            )
        )
        return None, None, None, gaps

    deltas = [abs(values[index] - values[index + 1]) for index in range(len(values) - 1)]
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


def _maximum_true_run(values: np.ndarray) -> int:
    padded = np.concatenate(([False], values.astype(bool), [False]))
    changes = np.diff(padded.astype(np.int8))
    starts = np.where(changes == 1)[0]
    ends = np.where(changes == -1)[0]
    if len(starts) == 0:
        return 0
    return int(np.max(ends - starts))


def _contiguous_ranges(indices: list[int], maximum_gap: int = 1) -> list[tuple[int, int]]:
    if not indices:
        return []
    ranges: list[tuple[int, int]] = []
    start = previous = indices[0]
    for index in indices[1:]:
        if index - previous > maximum_gap:
            ranges.append((start, previous))
            start = index
        previous = index
    ranges.append((start, previous))
    return ranges


def _find_bar_regions(rgb: np.ndarray, plot_info: dict[str, int | list[int]]) -> list[list[int]]:
    bar_mask = _blue_bar_mask(rgb)
    axis_x = int(plot_info["axis_line_x"])
    plot_top = int(plot_info["plot_top"])
    plot_bottom = int(plot_info["plot_bottom"])
    plot_right = int(plot_info["plot_right"])
    roi = bar_mask[plot_top : plot_bottom + 1, axis_x + 6 : plot_right]
    if roi.size == 0:
        return []

    # A zero-height bar is rendered as a one-pixel blue segment at the
    # baseline and still counts as a bar. Width/coverage filtering below keeps
    # isolated compression artifacts from becoming regions.
    minimum_vertical_run = 1
    qualifying_columns = [
        index for index in range(roi.shape[1])
        if _maximum_true_run(roi[:, index]) >= minimum_vertical_run
    ]
    column_ranges = _contiguous_ranges(qualifying_columns, maximum_gap=2)
    minimum_width = max(3, int(round(roi.shape[1] * 0.015)))

    regions: list[list[int]] = []
    for local_left, local_right in column_ranges:
        width = local_right - local_left + 1
        if width < minimum_width:
            continue
        component = roi[:, local_left : local_right + 1]
        row_coverage = component.mean(axis=1)
        qualifying_rows = np.where(row_coverage >= 0.45)[0].tolist()
        row_ranges = _contiguous_ranges(qualifying_rows)
        if not row_ranges:
            continue
        local_top, local_bottom = max(row_ranges, key=lambda bounds: bounds[1] - bounds[0])
        if local_bottom - local_top + 1 < minimum_vertical_run:
            continue
        regions.append(
            [
                axis_x + 6 + local_left,
                plot_top + local_top,
                axis_x + 6 + local_right,
                plot_top + local_bottom,
            ]
        )
    return regions


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


def _default_metadata(image_path: Path) -> dict[str, Any]:
    return {
        "case_id": image_path.stem,
        "image_id": image_path.stem,
        "backend": "template",
        "chart_version": "v2",
        "render_options": {},
    }


def extract_chart_evidence(
    image_path: Path,
    spec_path: Path,
    metadata_path: Path | None = None,
    backend: str | None = None,
) -> EvidenceGraph:
    image = _load_image(image_path)
    rgb = _to_np(image)
    spec = json.loads(spec_path.read_text(encoding="utf-8"))
    metadata = _default_metadata(image_path)
    metadata_source = "inferred"
    if metadata_path is not None:
        metadata.update(json.loads(metadata_path.read_text(encoding="utf-8")))
        metadata_source = "file"
    backend = backend or metadata.get("backend", "template")

    source_data = spec.get("source_reference", {}).get("data", [])
    expected_categories = [_source_category(item) for item in source_data]
    expected_axis_mode = spec.get("source_reference", {}).get("axis", {}).get("expected_scale_mode", "zero_baseline")
    candidate_units = ["mm", "cm", "kg", "N", "millions", "thousands", "percent", "people"]

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
        label_matches: list[tuple[str | None, float]] = []
        for y_offset in (0, -4, -8, -12, 4):
            candidate_box = [
                crop_box[0],
                max(0, crop_box[1] + y_offset),
                crop_box[2],
                min(image.height, crop_box[3] + y_offset),
            ]
            match = _match_text(
                image.crop(tuple(candidate_box)),
                expected_categories,
                font_size=14,
                threshold=0.55,
            )
            label_matches.append(match)
            if match[0] is not None and match[1] >= 0.65:
                break
        matched_label, label_confidence = max(
            label_matches,
            key=lambda item: (item[0] is not None, item[1]),
        )
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
        provenance=ExtractionProvenance(
            extractor_id="chart-v2",
            extractor_version="0.2.0",
            backend=backend,
            metadata_source=metadata_source,
            dependency_versions=capture_runtime_dependencies(),
            environment=capture_ocr_environment() if backend == "optional_ocr" else {},
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
