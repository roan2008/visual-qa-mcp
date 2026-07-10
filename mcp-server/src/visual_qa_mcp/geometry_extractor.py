from __future__ import annotations

from pathlib import Path

import numpy as np
from PIL import Image

from .arrow_extractor import _connected_components
from .contracts import (
    EvidenceGap,
    ExtractedHole,
    ExtractedRegion,
    ExtractionProvenance,
    GeometryEvidenceGraph,
)
from .geometry_labels import read_dimension_text, dimension_label_box

GEOMETRY_EXTRACTOR_ID = "geometry-v1"
GEOMETRY_EXTRACTOR_VERSION = "0.1.0"

PLATE_CHANNEL_TOLERANCE = 12
PLATE_MIN_VALUE = 160
PLATE_MAX_VALUE = 230
PLATE_MIN_PIXELS = 2000
HOLE_FILL_MIN_VALUE = 240
MIN_HOLE_PIXELS = 80
# Boundary-radius dispersion above this makes a component non-circular
# evidence (e.g. two merged holes), never a counted hole.
MAX_CIRCULARITY_DISPERSION = 0.12

GEOMETRY_CHECK_IDS = [
    "hole-count-correct",
    "hole-diameter-ratio-correct",
    "hole-alignment-correct",
    "dimension-text-correct",
]


def _plate_mask(pixels: np.ndarray) -> np.ndarray:
    channels = pixels.astype(np.int16)
    spread = channels.max(axis=2) - channels.min(axis=2)
    value = channels.mean(axis=2)
    return (spread <= PLATE_CHANNEL_TOLERANCE) & (value >= PLATE_MIN_VALUE) & (value <= PLATE_MAX_VALUE)


def _hole_fill_mask(pixels: np.ndarray) -> np.ndarray:
    channels = pixels.astype(np.int16)
    spread = channels.max(axis=2) - channels.min(axis=2)
    value = channels.mean(axis=2)
    return (spread <= PLATE_CHANNEL_TOLERANCE) & (value >= HOLE_FILL_MIN_VALUE)


def _component_inside_bbox(points_yx: np.ndarray, bbox: list[int], margin: int = 2) -> bool:
    left, top, right, bottom = bbox
    ys = points_yx[:, 0]
    xs = points_yx[:, 1]
    return bool(
        xs.min() > left + margin
        and xs.max() < right - margin
        and ys.min() > top + margin
        and ys.max() < bottom - margin
    )


def _boundary_radii(points_yx: np.ndarray, mask: np.ndarray) -> tuple[np.ndarray, tuple[float, float]]:
    """Radial distances of the component's boundary pixels from its centroid."""
    member = np.zeros(mask.shape, dtype=bool)
    member[points_yx[:, 0], points_yx[:, 1]] = True
    height, width = mask.shape
    boundary_points: list[tuple[int, int]] = []
    for y, x in points_yx.tolist():
        if (
            y == 0
            or y == height - 1
            or x == 0
            or x == width - 1
            or not member[y - 1, x]
            or not member[y + 1, x]
            or not member[y, x - 1]
            or not member[y, x + 1]
        ):
            boundary_points.append((y, x))
    boundary = np.array(boundary_points, dtype=np.float64)
    centroid_y = float(points_yx[:, 0].mean())
    centroid_x = float(points_yx[:, 1].mean())
    radii = np.hypot(boundary[:, 0] - centroid_y, boundary[:, 1] - centroid_x)
    return radii, (centroid_x, centroid_y)


def _outer_ring_radius(
    pixels: np.ndarray,
    centroid_xy: tuple[float, float],
    fill_radius: float,
) -> float:
    """Outer radius of the hole's dark outline ring, sampled radially.

    The white fill underestimates the drilled diameter by the outline width,
    and that bias is proportionally larger for small holes, which would skew
    diameter ratios. Walking outward through the dark ring recovers the true
    outer edge from image evidence alone.
    """
    height, width = pixels.shape[:2]
    values = pixels.astype(np.int16).mean(axis=2)
    outer_radii: list[float] = []
    for angle in np.linspace(0.0, 2.0 * np.pi, num=24, endpoint=False):
        direction_x, direction_y = float(np.cos(angle)), float(np.sin(angle))
        last_dark = None
        for step in np.arange(max(1.0, fill_radius - 2.0), fill_radius + 10.0, 0.5):
            x = int(round(centroid_xy[0] + direction_x * step))
            y = int(round(centroid_xy[1] + direction_y * step))
            if not (0 <= x < width and 0 <= y < height):
                break
            if values[y, x] < 100:
                last_dark = float(step)
        if last_dark is not None:
            outer_radii.append(last_dark + 0.5)
    if not outer_radii:
        return fill_radius
    return float(np.mean(outer_radii))


def _analyze_hole_component(
    points_yx: np.ndarray,
    mask: np.ndarray,
    pixels: np.ndarray,
    hole_index: int,
) -> tuple[ExtractedHole | None, bool]:
    """Return (hole, is_ambiguous). Non-circular blobs are ambiguous evidence."""
    radii, (centroid_x, centroid_y) = _boundary_radii(points_yx, mask)
    mean_radius = float(radii.mean())
    if mean_radius <= 1.0:
        return None, False
    dispersion = float(radii.std()) / mean_radius
    ys = points_yx[:, 0]
    xs = points_yx[:, 1]
    if dispersion > MAX_CIRCULARITY_DISPERSION:
        return None, True
    outer_radius = _outer_ring_radius(pixels, (centroid_x, centroid_y), mean_radius)
    return (
        ExtractedHole(
            hole_id=f"hole-{hole_index:02d}",
            center_xy=[int(round(centroid_x)), int(round(centroid_y))],
            diameter_px=round(2.0 * outer_radius, 1),
            circularity=round(dispersion, 3),
            bbox=[int(xs.min()), int(ys.min()), int(xs.max()), int(ys.max())],
            pixel_count=len(points_yx),
            confidence=0.9,
        ),
        False,
    )


def _decode_hole_label(image: Image.Image, hole: ExtractedHole) -> tuple[str | None, float]:
    box = dimension_label_box(
        (float(hole.center_xy[0]), float(hole.center_xy[1])), hole.diameter_px / 2.0
    )
    left, top, right, bottom = box
    left = max(0, left)
    top = max(0, top)
    right = min(image.width, right)
    bottom = min(image.height, bottom)
    if right - left < 8 or bottom - top < 8:
        return None, 0.0
    crop = image.crop((left, top, right, bottom))
    return read_dimension_text(crop)


def extract_geometry_evidence(image_path: Path) -> GeometryEvidenceGraph:
    image = Image.open(image_path).convert("RGB")
    pixels = np.array(image)

    gaps: list[EvidenceGap] = []
    regions: list[ExtractedRegion] = []
    holes: list[ExtractedHole] = []

    plate_components = sorted(_connected_components(_plate_mask(pixels)), key=len, reverse=True)
    plate_bbox: list[int] | None = None
    if plate_components and len(plate_components[0]) >= PLATE_MIN_PIXELS:
        plate_points = plate_components[0]
        plate_bbox = [
            int(plate_points[:, 1].min()),
            int(plate_points[:, 0].min()),
            int(plate_points[:, 1].max()),
            int(plate_points[:, 0].max()),
        ]
        regions.append(
            ExtractedRegion(
                region_id="plate",
                kind="plate",
                bbox=plate_bbox,
                pixel_count=len(plate_points),
                confidence=0.95,
            )
        )
    else:
        gaps.append(
            EvidenceGap(
                code="plate_not_found",
                message="No plate region with enough gray pixel support was detected.",
                check_ids=list(GEOMETRY_CHECK_IDS),
            )
        )

    ambiguous_components = 0
    if plate_bbox is not None:
        hole_mask = _hole_fill_mask(pixels)
        for points_yx in _connected_components(hole_mask):
            if len(points_yx) < MIN_HOLE_PIXELS:
                continue
            if not _component_inside_bbox(points_yx, plate_bbox):
                # Background outside the plate is also near-white; only fully
                # enclosed bright regions count as drilled-hole evidence.
                continue
            hole, is_ambiguous = _analyze_hole_component(points_yx, hole_mask, pixels, len(holes) + 1)
            if is_ambiguous:
                ambiguous_components += 1
                continue
            if hole is None:
                continue
            label_text, label_confidence = _decode_hole_label(image, hole)
            hole.label_text = label_text
            hole.label_confidence = label_confidence
            holes.append(hole)

    holes.sort(key=lambda item: (item.center_xy[0], item.center_xy[1]))
    for index, hole in enumerate(holes, start=1):
        hole.hole_id = f"hole-{index:02d}"

    if ambiguous_components:
        gaps.append(
            EvidenceGap(
                code="ambiguous_hole_geometry",
                message=(
                    f"{ambiguous_components} bright region(s) inside the plate were not "
                    "circular enough to be counted as holes (e.g. merged or deformed "
                    "features), so the hole set is not reliable evidence."
                ),
                check_ids=list(GEOMETRY_CHECK_IDS),
            )
        )

    unreadable_labels = [hole.hole_id for hole in holes if hole.label_text is None]
    if holes and unreadable_labels:
        gaps.append(
            EvidenceGap(
                code="unreadable_dimension_text",
                message=(
                    "Dimension text for "
                    + ", ".join(f"'{hole_id}'" for hole_id in unreadable_labels)
                    + " could not be decoded against the fixed dimension catalog."
                ),
                check_ids=["dimension-text-correct"],
            )
        )

    extraction_confidence = 0.9 if not gaps else max(0.3, 0.9 - 0.2 * len(gaps))
    return GeometryEvidenceGraph(
        image_id=image_path.stem,
        diagram_type="mechanical_plate",
        holes=holes,
        regions=regions,
        extraction_confidence=round(extraction_confidence, 2),
        provenance=ExtractionProvenance(
            extractor_id=GEOMETRY_EXTRACTOR_ID,
            extractor_version=GEOMETRY_EXTRACTOR_VERSION,
            backend="component_circle",
            metadata_source="none",
        ),
        gaps=gaps,
        metadata={"image_path": str(image_path)},
    )
