from __future__ import annotations

from itertools import product
from pathlib import Path

import numpy as np
from PIL import Image

from .arrow_extractor import _saturation_mask
from .chart_extractor import _cluster_indices, _maximum_true_run
from .contracts import (
    AxisMapping,
    CoordinateEvidenceGraph,
    DetectedPolylineEdge,
    EvidenceGap,
    ExtractedCoordinateAxis,
    ExtractedPoint,
    ExtractionProvenance,
    TickLabel,
)
from .spatial import connected_components
from .tick_reader import NumericTemplateCandidate, rank_numeric_text_templates

COORDINATE_EXTRACTOR_ID = "coordinate-graph-v1"
COORDINATE_EXTRACTOR_VERSION = "0.1.0"

DARK_INTENSITY_THRESHOLD = 110
MIN_AXIS_LINE_RUN_FRACTION = 0.4

MIN_POINT_PIXELS = 30
COLOR_AMBIGUITY_DISTANCE = 40.0

LINE_SPREAD_MAX = 20
LINE_GRAY_MIN = 70
LINE_GRAY_MAX = 180
EDGE_SAMPLE_COUNT = 24
EDGE_COVERAGE_THRESHOLD = 0.85
EDGE_HIT_RADIUS_PX = 2

Y_TICK_LABEL_OFFSET = (64, 8)
X_TICK_LABEL_SIZE = (25, 20)

COORDINATE_CHECK_IDS = [
    "point-count-matches",
    "required-points-present",
    "point-positions-correct",
    "polyline-connections-correct",
    "axis-scale-correct",
]


def _dark_mask(pixels: np.ndarray) -> np.ndarray:
    return pixels.astype(np.int16).mean(axis=2) < DARK_INTENSITY_THRESHOLD


def _find_axis_lines(dark: np.ndarray) -> tuple[int | None, int | None]:
    height, width = dark.shape
    left_limit = max(1, int(width * 0.55))
    column_runs = [_maximum_true_run(dark[:, x]) for x in range(left_limit)]
    axis_line_x = int(np.argmax(column_runs)) if column_runs else None
    if not column_runs or column_runs[axis_line_x] < MIN_AXIS_LINE_RUN_FRACTION * height:
        axis_line_x = None

    top_limit = max(0, int(height * 0.35))
    row_runs = [_maximum_true_run(dark[y, :]) for y in range(top_limit, height)]
    axis_line_y = top_limit + int(np.argmax(row_runs)) if row_runs else None
    if not row_runs or row_runs[axis_line_y - top_limit] < MIN_AXIS_LINE_RUN_FRACTION * width:
        axis_line_y = None

    return axis_line_x, axis_line_y


def _tick_positions(dark: np.ndarray, axis_line_x: int | None, axis_line_y: int | None) -> tuple[list[int], list[int]]:
    # The Y-axis tick nearest the X-axis line (its minimum value) sits at the
    # same pixel row as the X-axis, and its label text can otherwise bleed
    # into the X-tick sampling row (and symmetrically for the X-axis's
    # leftmost tick label bleeding into the Y-tick sampling column). Bound
    # each search to the side of the corner where only that axis's own tick
    # marks can legitimately appear.
    y_tick_centers: list[int] = []
    if axis_line_x is not None and axis_line_x - 4 >= 0:
        column = axis_line_x - 4
        row_limit = (axis_line_y + 2) if axis_line_y is not None else dark.shape[0]
        indices = [index for index in np.flatnonzero(dark[:, column]).tolist() if index <= row_limit]
        for cluster in _cluster_indices(indices):
            y_tick_centers.append(int(round(sum(cluster) / len(cluster))))

    x_tick_centers: list[int] = []
    if axis_line_y is not None and axis_line_y + 4 < dark.shape[0]:
        row = axis_line_y + 4
        column_limit = (axis_line_x - 2) if axis_line_x is not None else 0
        indices = [index for index in np.flatnonzero(dark[row, :]).tolist() if index >= column_limit]
        for cluster in _cluster_indices(indices):
            x_tick_centers.append(int(round(sum(cluster) / len(cluster))))

    return y_tick_centers, x_tick_centers


def _y_tick_crop(image: Image.Image, axis_line_x: int, tick_y: int) -> tuple[Image.Image, list[int]]:
    label_width, half_height = Y_TICK_LABEL_OFFSET[0], Y_TICK_LABEL_OFFSET[1]
    box = [
        max(0, axis_line_x - label_width),
        max(0, tick_y - 10),
        max(0, axis_line_x - half_height),
        min(image.height, tick_y + 10),
    ]
    return image.crop(tuple(box)), box


def _x_tick_crop(image: Image.Image, axis_line_y: int, tick_x: int) -> tuple[Image.Image, list[int]]:
    half_width, height = X_TICK_LABEL_SIZE
    box = [
        max(0, tick_x - half_width),
        min(image.height, axis_line_y + 8),
        min(image.width, tick_x + half_width),
        min(image.height, axis_line_y + 8 + height),
    ]
    return image.crop(tuple(box)), box


def _fit_axis_sequence(
    ranked_rows: list[list[NumericTemplateCandidate]],
    centers: list[float],
    direction: int,
) -> tuple[float, float, list[tuple[float, NumericTemplateCandidate]]] | None:
    """Fit value = slope * position + intercept from ranked per-tick candidates.

    direction > 0 requires values to increase with position (x-axis); direction < 0
    requires values to decrease with position (y-axis, image rows grow downward).
    This mirrors tick_reader._decode_tick_sequence_result's global-consistency
    search but is written locally so it can support either sign of monotonicity
    without touching the chart-v2 tick reader (which is hard-coded to a
    decreasing y-axis and must keep its validated behavior unchanged).
    """
    choices: list[list[NumericTemplateCandidate | None]] = [
        [*ranked, None] if ranked else [None] for ranked in ranked_rows
    ]
    best: tuple[float, float, float, list[tuple[float, NumericTemplateCandidate]]] | None = None
    for assignment in product(*choices):
        selected = [
            (centers[index], candidate)
            for index, candidate in enumerate(assignment)
            if candidate is not None
        ]
        if len(selected) < 3:
            continue
        order = sorted(selected, key=lambda item: item[0])
        values = [candidate.value for _, candidate in order]
        if direction > 0:
            if any(values[index] >= values[index + 1] for index in range(len(values) - 1)):
                continue
        else:
            if any(values[index] <= values[index + 1] for index in range(len(values) - 1)):
                continue
        positions = np.array([position for position, _ in order], dtype=float)
        value_array = np.array(values, dtype=float)
        slope, intercept = np.polyfit(positions, value_array, 1)
        if direction > 0 and slope <= 0:
            continue
        if direction < 0 and slope >= 0:
            continue
        predicted = slope * positions + intercept
        span = max(float(value_array.max() - value_array.min()), 5.0)
        residual = float(np.sqrt(np.mean((predicted - value_array) ** 2)) / span)
        if residual > 0.02:
            continue
        visual_score = float(np.mean([candidate.score for _, candidate in order]))
        missing_penalty = 0.03 * (len(assignment) - len(selected))
        total_score = visual_score + residual * 3.0 + missing_penalty
        if best is None or total_score < best[0]:
            best = (total_score, float(slope), float(intercept), order)
    if best is None:
        return None
    return best[1], best[2], best[3]


def _extract_axis(
    image: Image.Image,
    dark: np.ndarray,
    orientation: str,
    axis_line_position: int | None,
    tick_centers: list[int],
    other_axis_position: int | None,
) -> tuple[ExtractedCoordinateAxis, EvidenceGap | None]:
    gap_code = f"{orientation}_axis_unreadable"
    if axis_line_position is None or other_axis_position is None or len(tick_centers) < 3:
        axis = ExtractedCoordinateAxis(
            orientation=orientation,
            tick_labels=[],
            axis_pixel_position=axis_line_position,
            reference_pixel=None,
            fit_slope=None,
            fit_intercept=None,
            mapping=None,
            confidence=0.2,
        )
        gap = EvidenceGap(
            code=gap_code,
            message=(
                f"The {orientation}-axis line or fewer than three tick marks could not be "
                "confidently detected in the image."
            ),
            check_ids=["point-positions-correct", "axis-scale-correct"],
        )
        return axis, gap

    if orientation == "y":
        crops = [_y_tick_crop(image, axis_line_position, tick_y) for tick_y in tick_centers]
        centers = [float(tick_y) for tick_y in tick_centers]
        direction = -1
    else:
        crops = [_x_tick_crop(image, axis_line_position, tick_x) for tick_x in tick_centers]
        centers = [float(tick_x) for tick_x in tick_centers]
        direction = 1

    ranked_rows = [rank_numeric_text_templates(crop) for crop, _ in crops]
    fit = _fit_axis_sequence(ranked_rows, centers, direction)
    tick_labels = [
        TickLabel(text=None, parsed_value=None, bbox=bbox, confidence=0.0)
        for _, bbox in crops
    ]
    if fit is None:
        axis = ExtractedCoordinateAxis(
            orientation=orientation,
            tick_labels=tick_labels,
            axis_pixel_position=axis_line_position,
            reference_pixel=None,
            fit_slope=None,
            fit_intercept=None,
            mapping=None,
            confidence=0.3,
        )
        gap = EvidenceGap(
            code=gap_code,
            message=(
                f"Tick labels on the {orientation}-axis do not support a consistent, "
                "monotonic linear scale reading."
            ),
            check_ids=["point-positions-correct", "axis-scale-correct"],
        )
        return axis, gap

    slope, intercept, selected = fit
    selected_by_position = {position: candidate for position, candidate in selected}
    for index, (_, bbox) in enumerate(crops):
        candidate = selected_by_position.get(centers[index])
        if candidate is not None:
            tick_labels[index] = TickLabel(
                text=candidate.text,
                parsed_value=float(candidate.value),
                bbox=bbox,
                confidence=0.85,
            )

    values = [candidate.value for _, candidate in selected]
    axis_min = float(min(values))
    axis_max = float(max(values))
    scale_mode = "signed" if axis_min < 0 < axis_max else ("zero_baseline" if axis_min == 0 else "non_zero_min")
    reference_position, reference_candidate = min(selected, key=lambda item: item[1].value)
    mapping = AxisMapping(
        min_value=axis_min,
        max_value=axis_max,
        pixels_per_unit=round(abs(1.0 / slope), 4) if slope != 0 else 0.0,
        scale_mode=scale_mode,
        value_direction="positive_right" if orientation == "x" else "positive_up",
        readable=True,
    )
    axis = ExtractedCoordinateAxis(
        orientation=orientation,
        tick_labels=tick_labels,
        axis_pixel_position=axis_line_position,
        reference_pixel=int(round(reference_position)),
        fit_slope=round(slope, 6),
        fit_intercept=round(intercept, 4),
        mapping=mapping,
        confidence=0.9,
    )
    return axis, None


def _line_mask(pixels: np.ndarray) -> np.ndarray:
    channels = pixels.astype(np.int16)
    spread = channels.max(axis=2) - channels.min(axis=2)
    value = channels.mean(axis=2)
    return (spread <= LINE_SPREAD_MAX) & (value >= LINE_GRAY_MIN) & (value <= LINE_GRAY_MAX)


def _edge_coverage(line_mask: np.ndarray, first_xy: list[int], second_xy: list[int]) -> float:
    height, width = line_mask.shape
    hits = 0
    total = 0
    for fraction in np.linspace(0.08, 0.92, EDGE_SAMPLE_COUNT):
        x = first_xy[0] + (second_xy[0] - first_xy[0]) * fraction
        y = first_xy[1] + (second_xy[1] - first_xy[1]) * fraction
        center_x, center_y = int(round(x)), int(round(y))
        total += 1
        found = False
        for dx in range(-EDGE_HIT_RADIUS_PX, EDGE_HIT_RADIUS_PX + 1):
            for dy in range(-EDGE_HIT_RADIUS_PX, EDGE_HIT_RADIUS_PX + 1):
                sample_x, sample_y = center_x + dx, center_y + dy
                if 0 <= sample_x < width and 0 <= sample_y < height and line_mask[sample_y, sample_x]:
                    found = True
                    break
            if found:
                break
        if found:
            hits += 1
    return hits / total if total else 0.0


def extract_coordinate_evidence(image_path: Path) -> CoordinateEvidenceGraph:
    image = Image.open(image_path).convert("RGB")
    pixels = np.array(image)

    gaps: list[EvidenceGap] = []
    dark = _dark_mask(pixels)
    axis_line_x, axis_line_y = _find_axis_lines(dark)
    y_tick_centers, x_tick_centers = _tick_positions(dark, axis_line_x, axis_line_y)

    y_axis, y_gap = _extract_axis(image, dark, "y", axis_line_x, y_tick_centers, axis_line_y)
    x_axis, x_gap = _extract_axis(image, dark, "x", axis_line_y, x_tick_centers, axis_line_x)
    if y_gap is not None:
        gaps.append(y_gap)
    if x_gap is not None:
        gaps.append(x_gap)

    points: list[ExtractedPoint] = []
    for points_yx in connected_components(_saturation_mask(pixels)):
        if len(points_yx) < MIN_POINT_PIXELS:
            continue
        mean_rgb = [
            int(round(value)) for value in pixels[points_yx[:, 0], points_yx[:, 1]].mean(axis=0)
        ]
        centroid_x = float(points_yx[:, 1].mean())
        centroid_y = float(points_yx[:, 0].mean())
        bbox = [
            int(points_yx[:, 1].min()),
            int(points_yx[:, 0].min()),
            int(points_yx[:, 1].max()),
            int(points_yx[:, 0].max()),
        ]
        data_xy = None
        if x_axis.fit_slope is not None and y_axis.fit_slope is not None:
            data_xy = [
                round(x_axis.fit_slope * centroid_x + x_axis.fit_intercept, 3),
                round(y_axis.fit_slope * centroid_y + y_axis.fit_intercept, 3),
            ]
        points.append(
            ExtractedPoint(
                point_id=f"point-{len(points) + 1:02d}",
                rgb=mean_rgb,
                pixel_xy=[int(round(centroid_x)), int(round(centroid_y))],
                data_xy=data_xy,
                bbox=bbox,
                pixel_count=len(points_yx),
                confidence=0.9,
            )
        )

    for first_index in range(len(points)):
        for second_index in range(first_index + 1, len(points)):
            first_rgb = np.array(points[first_index].rgb, dtype=np.float64)
            second_rgb = np.array(points[second_index].rgb, dtype=np.float64)
            if float(np.linalg.norm(first_rgb - second_rgb)) < COLOR_AMBIGUITY_DISTANCE:
                gaps.append(
                    EvidenceGap(
                        code="ambiguous_point_colors",
                        message=(
                            f"Points '{points[first_index].point_id}' and "
                            f"'{points[second_index].point_id}' share a similar color, so "
                            "color-based identity matching is ambiguous."
                        ),
                        check_ids=[
                            "required-points-present",
                            "point-positions-correct",
                            "polyline-connections-correct",
                        ],
                    )
                )

    line_mask = _line_mask(pixels)
    polyline_edges: list[DetectedPolylineEdge] = []
    for first_index in range(len(points)):
        for second_index in range(first_index + 1, len(points)):
            coverage = _edge_coverage(
                line_mask, points[first_index].pixel_xy, points[second_index].pixel_xy
            )
            if coverage >= EDGE_COVERAGE_THRESHOLD:
                polyline_edges.append(
                    DetectedPolylineEdge(
                        from_point_id=points[first_index].point_id,
                        to_point_id=points[second_index].point_id,
                        coverage=round(coverage, 3),
                    )
                )

    extraction_confidence = 0.9 if not gaps else max(0.3, 0.9 - 0.2 * len(gaps))
    return CoordinateEvidenceGraph(
        image_id=image_path.stem,
        diagram_type="coordinate_plane",
        x_axis=x_axis,
        y_axis=y_axis,
        points=points,
        polyline_edges=polyline_edges,
        extraction_confidence=round(extraction_confidence, 2),
        provenance=ExtractionProvenance(
            extractor_id=COORDINATE_EXTRACTOR_ID,
            extractor_version=COORDINATE_EXTRACTOR_VERSION,
            backend="dual_axis_template",
            metadata_source="none",
        ),
        gaps=gaps,
        metadata={"image_path": str(image_path)},
    )
