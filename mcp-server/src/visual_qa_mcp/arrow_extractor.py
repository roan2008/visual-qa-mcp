from __future__ import annotations

import math
from pathlib import Path

import numpy as np
from PIL import Image

from .arrow_labels import label_anchor_box, read_label_text
from .contracts import (
    ArrowEvidenceGraph,
    EvidenceGap,
    ExtractedArrow,
    ExtractedRegion,
    ExtractionProvenance,
)
from .spatial import connected_components

ARROW_EXTRACTOR_ID = "arrow-v1"
ARROW_EXTRACTOR_VERSION = "0.1.0"

SATURATION_THRESHOLD = 50
GRAY_CHANNEL_TOLERANCE = 12
GRAY_MIN_VALUE = 90
GRAY_MAX_VALUE = 205
MIN_ARROW_PIXELS = 60
MIN_ARROW_LENGTH_PX = 24.0
COLOR_AMBIGUITY_DISTANCE = 40.0
HEAD_SPREAD_RATIO = 1.3
END_WINDOW_FRACTION = 0.2

ARROW_CHECK_IDS = [
    "arrow-count-matches",
    "required-arrows-present",
    "arrow-directions-correct",
    "arrow-anchors-object",
    "force-balance-correct",
]


def _saturation_mask(pixels: np.ndarray) -> np.ndarray:
    channels = pixels.astype(np.int16)
    spread = channels.max(axis=2) - channels.min(axis=2)
    return spread >= SATURATION_THRESHOLD


def _gray_object_mask(pixels: np.ndarray) -> np.ndarray:
    channels = pixels.astype(np.int16)
    spread = channels.max(axis=2) - channels.min(axis=2)
    value = channels.mean(axis=2)
    return (spread <= GRAY_CHANNEL_TOLERANCE) & (value >= GRAY_MIN_VALUE) & (value <= GRAY_MAX_VALUE)


def _principal_axis(points_xy: np.ndarray) -> tuple[float, float]:
    centered = points_xy - points_xy.mean(axis=0)
    sxx = float(np.mean(centered[:, 0] * centered[:, 0]))
    syy = float(np.mean(centered[:, 1] * centered[:, 1]))
    sxy = float(np.mean(centered[:, 0] * centered[:, 1]))
    theta = 0.5 * math.atan2(2.0 * sxy, sxx - syy)
    return math.cos(theta), math.sin(theta)


def _end_statistics(
    projections: np.ndarray,
    perpendicular: np.ndarray,
    points_xy: np.ndarray,
    low_end: bool,
) -> tuple[np.ndarray, float]:
    span = projections.max() - projections.min()
    window = max(span * END_WINDOW_FRACTION, 4.0)
    if low_end:
        selector = projections <= projections.min() + window
        extreme_value = projections.min()
    else:
        selector = projections >= projections.max() - window
        extreme_value = projections.max()
    spread = float(perpendicular[selector].std()) if selector.sum() > 1 else 0.0
    # Use the true geometric extremity rather than the window average: the average
    # is biased inward by roughly half the window width, which is small enough to
    # not affect direction/anchor checks but large enough to misalign the label
    # crop region computed from tail_xy.
    extreme_selector = np.abs(projections - extreme_value) <= 0.5
    return points_xy[extreme_selector].mean(axis=0), spread


def _analyze_component(points_yx: np.ndarray, component_index: int, mean_rgb: list[int]) -> ExtractedArrow | None:
    points_xy = points_yx[:, ::-1].astype(np.float64)
    axis_x, axis_y = _principal_axis(points_xy)
    centered = points_xy - points_xy.mean(axis=0)
    projections = centered @ np.array([axis_x, axis_y])
    perpendicular = centered @ np.array([-axis_y, axis_x])
    length = float(projections.max() - projections.min())
    if length < MIN_ARROW_LENGTH_PX:
        return None

    low_point, low_spread = _end_statistics(projections, perpendicular, points_xy, low_end=True)
    high_point, high_spread = _end_statistics(projections, perpendicular, points_xy, low_end=False)
    if max(low_spread, high_spread) < HEAD_SPREAD_RATIO * min(low_spread, high_spread) + 1e-6:
        return None
    if high_spread > low_spread:
        tail_point, head_point = low_point, high_point
        tail_spread, head_spread = low_spread, high_spread
    else:
        tail_point, head_point = high_point, low_point
        tail_spread, head_spread = high_spread, low_spread

    angle = math.degrees(
        math.atan2(-(head_point[1] - tail_point[1]), head_point[0] - tail_point[0])
    ) % 360.0
    min_x, min_y = points_xy.min(axis=0)
    max_x, max_y = points_xy.max(axis=0)
    tail_xy = [int(round(tail_point[0])), int(round(tail_point[1]))]
    return ExtractedArrow(
        arrow_id=f"arrow-{component_index:02d}",
        rgb=mean_rgb,
        bbox=[int(min_x), int(min_y), int(max_x), int(max_y)],
        tail_xy=tail_xy,
        head_xy=[int(round(head_point[0])), int(round(head_point[1]))],
        angle_degrees=round(angle, 1),
        length_px=round(length, 1),
        tail_spread_px=round(tail_spread, 2),
        head_spread_px=round(head_spread, 2),
        confidence=0.9,
    )


def _decode_arrow_label(image: Image.Image, arrow: ExtractedArrow) -> tuple[str | None, float]:
    box = label_anchor_box(tuple(arrow.tail_xy), tuple(arrow.head_xy))
    left, top, right, bottom = box
    left = max(0, left)
    top = max(0, top)
    right = min(image.width, right)
    bottom = min(image.height, bottom)
    if right - left < 8 or bottom - top < 8:
        return None, 0.0
    crop = image.crop((left, top, right, bottom))
    return read_label_text(crop)


def extract_arrow_evidence(image_path: Path) -> ArrowEvidenceGraph:
    image = Image.open(image_path).convert("RGB")
    pixels = np.array(image)

    gaps: list[EvidenceGap] = []
    regions: list[ExtractedRegion] = []

    object_mask = _gray_object_mask(pixels)
    object_components = sorted(connected_components(object_mask), key=len, reverse=True)
    largest_object_component = object_components[0] if object_components else None
    if largest_object_component is not None and len(largest_object_component) >= 400:
        # Use only the largest connected blob, not the global extent of every
        # matching pixel: blur/JPEG artifacts can scatter small gray-ish noise
        # blobs far from the object, which would otherwise inflate the bbox and
        # make a genuinely detached arrow look anchored.
        object_ys = largest_object_component[:, 0]
        object_xs = largest_object_component[:, 1]
        regions.append(
            ExtractedRegion(
                region_id="object",
                kind="box",
                bbox=[
                    int(object_xs.min()),
                    int(object_ys.min()),
                    int(object_xs.max()),
                    int(object_ys.max()),
                ],
                pixel_count=len(largest_object_component),
                confidence=0.95,
            )
        )
    else:
        gaps.append(
            EvidenceGap(
                code="object_region_unresolved",
                message="No object region with enough gray pixel support was detected.",
                check_ids=["arrow-anchors-object"],
            )
        )

    arrows: list[ExtractedArrow] = []
    degenerate_components = 0
    for index, points_yx in enumerate(connected_components(_saturation_mask(pixels))):
        mean_rgb = [
            int(round(value))
            for value in pixels[points_yx[:, 0], points_yx[:, 1]].mean(axis=0)
        ]
        if len(points_yx) < MIN_ARROW_PIXELS:
            degenerate_components += 1
            continue
        arrow = _analyze_component(points_yx, len(arrows) + 1, mean_rgb)
        if arrow is None:
            degenerate_components += 1
            continue
        label_text, label_confidence = _decode_arrow_label(image, arrow)
        arrow.label_text = label_text
        arrow.label_confidence = label_confidence
        arrows.append(arrow)

    if degenerate_components:
        gaps.append(
            EvidenceGap(
                code="degenerate_arrow_geometry",
                message=(
                    f"{degenerate_components} colored component(s) were too small or lacked a "
                    "readable head/tail structure to be treated as arrow evidence."
                ),
                check_ids=list(ARROW_CHECK_IDS),
            )
        )

    for first_index in range(len(arrows)):
        for second_index in range(first_index + 1, len(arrows)):
            first_rgb = np.array(arrows[first_index].rgb, dtype=np.float64)
            second_rgb = np.array(arrows[second_index].rgb, dtype=np.float64)
            first_label = arrows[first_index].label_text
            second_label = arrows[second_index].label_text
            labels_resolve_identity = (
                first_label is not None and second_label is not None and first_label != second_label
            )
            if float(np.linalg.norm(first_rgb - second_rgb)) < COLOR_AMBIGUITY_DISTANCE and not labels_resolve_identity:
                gaps.append(
                    EvidenceGap(
                        code="ambiguous_arrow_colors",
                        message=(
                            f"Arrows '{arrows[first_index].arrow_id}' and "
                            f"'{arrows[second_index].arrow_id}' share a similar color, so "
                            "color-based identity matching is ambiguous."
                        ),
                        check_ids=[
                            "required-arrows-present",
                            "arrow-directions-correct",
                            "arrow-anchors-object",
                            "force-balance-correct",
                        ],
                    )
                )

    extraction_confidence = 0.9 if not gaps else max(0.3, 0.9 - 0.2 * len(gaps))
    return ArrowEvidenceGraph(
        image_id=image_path.stem,
        diagram_type="free_body",
        arrows=arrows,
        regions=regions,
        extraction_confidence=round(extraction_confidence, 2),
        provenance=ExtractionProvenance(
            extractor_id=ARROW_EXTRACTOR_ID,
            extractor_version=ARROW_EXTRACTOR_VERSION,
            backend="color_component",
            metadata_source="none",
        ),
        gaps=gaps,
        metadata={"image_path": str(image_path)},
    )
