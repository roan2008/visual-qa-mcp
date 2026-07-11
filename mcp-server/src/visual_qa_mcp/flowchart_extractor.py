from __future__ import annotations

import math
from pathlib import Path

import numpy as np
from PIL import Image

from .arrow_extractor import _saturation_mask
from .contracts import (
    EvidenceGap,
    ExtractedConnector,
    ExtractedNode,
    ExtractionProvenance,
    FlowchartEvidenceGraph,
)
from .flowchart_labels import node_label_box, read_node_label_text
from .spatial import bbox_from_points, centroid_from_points, connected_components

FLOWCHART_EXTRACTOR_ID = "flowchart-v1"
FLOWCHART_EXTRACTOR_VERSION = "0.1.0"

MIN_NODE_PIXELS = 300
RECTANGLE_FILL_RATIO_MIN = 0.75
DIAMOND_FILL_RATIO_MIN = 0.30
COLOR_AMBIGUITY_DISTANCE = 40.0

CONNECTOR_SPREAD_MAX = 15
CONNECTOR_VALUE_MIN = 60
CONNECTOR_VALUE_MAX = 180
MIN_CONNECTOR_PIXELS = 40
MIN_CONNECTOR_LENGTH_PX = 15.0
CONNECTOR_HEAD_SPREAD_RATIO = 1.3
END_WINDOW_FRACTION = 0.2
NODE_ATTACH_TOLERANCE_PX = 20.0

FLOWCHART_CHECK_IDS = [
    "node-count-matches",
    "required-nodes-present",
    "node-shape-correct",
    "connector-links-correct",
    "node-label-correct",
]


def _connector_mask(pixels: np.ndarray) -> np.ndarray:
    channels = pixels.astype(np.int16)
    spread = channels.max(axis=2) - channels.min(axis=2)
    value = channels.mean(axis=2)
    return (spread <= CONNECTOR_SPREAD_MAX) & (value >= CONNECTOR_VALUE_MIN) & (value <= CONNECTOR_VALUE_MAX)


def _classify_shape(pixel_count: int, bbox: list[int]) -> tuple[str | None, float]:
    width = bbox[2] - bbox[0] + 1
    height = bbox[3] - bbox[1] + 1
    bbox_area = max(width * height, 1)
    fill_ratio = pixel_count / bbox_area
    if fill_ratio >= RECTANGLE_FILL_RATIO_MIN:
        return "rectangle", fill_ratio
    if fill_ratio >= DIAMOND_FILL_RATIO_MIN:
        return "diamond", fill_ratio
    return None, fill_ratio


def _decode_node_label(image: Image.Image, bbox: list[int]) -> tuple[str | None, float]:
    box = node_label_box(bbox)
    left, top, right, bottom = box
    left = max(0, left)
    top = max(0, top)
    right = min(image.width, right)
    bottom = min(image.height, bottom)
    if right - left < 8 or bottom - top < 8:
        return None, 0.0
    crop = image.crop((left, top, right, bottom))
    return read_node_label_text(crop)


def _principal_axis_ends(points_xy: np.ndarray) -> tuple[np.ndarray, float, np.ndarray, float] | None:
    centered = points_xy - points_xy.mean(axis=0)
    sxx = float(np.mean(centered[:, 0] * centered[:, 0]))
    syy = float(np.mean(centered[:, 1] * centered[:, 1]))
    sxy = float(np.mean(centered[:, 0] * centered[:, 1]))
    theta = 0.5 * math.atan2(2.0 * sxy, sxx - syy)
    axis_x, axis_y = math.cos(theta), math.sin(theta)
    projections = centered @ np.array([axis_x, axis_y])
    perpendicular = centered @ np.array([-axis_y, axis_x])
    length = float(projections.max() - projections.min())
    if length < MIN_CONNECTOR_LENGTH_PX:
        return None

    def _end_stats(low_end: bool) -> tuple[np.ndarray, float]:
        span = projections.max() - projections.min()
        window = max(span * END_WINDOW_FRACTION, 4.0)
        if low_end:
            selector = projections <= projections.min() + window
            extreme_value = projections.min()
        else:
            selector = projections >= projections.max() - window
            extreme_value = projections.max()
        spread = float(perpendicular[selector].std()) if selector.sum() > 1 else 0.0
        extreme_selector = np.abs(projections - extreme_value) <= 0.5
        return points_xy[extreme_selector].mean(axis=0), spread

    low_point, low_spread = _end_stats(low_end=True)
    high_point, high_spread = _end_stats(low_end=False)
    return low_point, low_spread, high_point, high_spread


def _distance_to_bbox(point_xy: tuple[float, float], bbox: list[float]) -> float:
    left, top, right, bottom = bbox
    x, y = point_xy
    dx = max(left - x, 0.0, x - right)
    dy = max(top - y, 0.0, y - bottom)
    return math.hypot(dx, dy)


def _nearest_node(
    point_xy: tuple[float, float], node_bboxes: dict[str, list[float]]
) -> tuple[str | None, float]:
    best_id: str | None = None
    best_distance = math.inf
    for node_id, bbox in node_bboxes.items():
        distance = _distance_to_bbox(point_xy, bbox)
        if distance < best_distance:
            best_distance = distance
            best_id = node_id
    return best_id, best_distance


def extract_flowchart_evidence(image_path: Path) -> FlowchartEvidenceGraph:
    image = Image.open(image_path).convert("RGB")
    pixels = np.array(image)

    gaps: list[EvidenceGap] = []
    nodes: list[ExtractedNode] = []
    node_bboxes: dict[str, list[float]] = {}

    degenerate_node_components = 0
    for points_yx in connected_components(_saturation_mask(pixels)):
        if len(points_yx) < MIN_NODE_PIXELS:
            degenerate_node_components += 1
            continue
        bbox = bbox_from_points(points_yx)
        shape, fill_ratio = _classify_shape(len(points_yx), bbox)
        node_id = f"node-{len(nodes) + 1:02d}"
        if shape is None:
            degenerate_node_components += 1
            continue
        mean_rgb = [int(round(value)) for value in pixels[points_yx[:, 0], points_yx[:, 1]].mean(axis=0)]
        centroid = centroid_from_points(points_yx)
        label_text, label_confidence = _decode_node_label(image, bbox)
        nodes.append(
            ExtractedNode(
                node_id=node_id,
                shape=shape,
                rgb=mean_rgb,
                bbox=bbox,
                center_xy=[int(round(centroid[0])), int(round(centroid[1]))],
                pixel_count=len(points_yx),
                fill_ratio=round(fill_ratio, 3),
                confidence=0.9,
                label_text=label_text,
                label_confidence=label_confidence,
            )
        )
        node_bboxes[node_id] = [float(value) for value in bbox]

    if degenerate_node_components:
        gaps.append(
            EvidenceGap(
                code="degenerate_node_geometry",
                message=(
                    f"{degenerate_node_components} colored component(s) were too small or did not "
                    "match a recognized rectangle/diamond fill ratio."
                ),
                check_ids=list(FLOWCHART_CHECK_IDS),
            )
        )

    for first_index in range(len(nodes)):
        for second_index in range(first_index + 1, len(nodes)):
            first_rgb = np.array(nodes[first_index].rgb, dtype=np.float64)
            second_rgb = np.array(nodes[second_index].rgb, dtype=np.float64)
            if float(np.linalg.norm(first_rgb - second_rgb)) < COLOR_AMBIGUITY_DISTANCE:
                gaps.append(
                    EvidenceGap(
                        code="ambiguous_node_colors",
                        message=(
                            f"Nodes '{nodes[first_index].node_id}' and "
                            f"'{nodes[second_index].node_id}' share a similar color, so "
                            "color-based identity matching is ambiguous."
                        ),
                        check_ids=[
                            "required-nodes-present",
                            "node-shape-correct",
                            "connector-links-correct",
                            "node-label-correct",
                        ],
                    )
                )

    # Anti-aliased label glyph edges (a blend of black text and the white
    # background) land squarely inside the connector mask's achromatic value
    # band, so explicitly blank out each node's label region before searching
    # for connector components rather than trying to widen/narrow the mask
    # thresholds around it.
    connector_mask = _connector_mask(pixels)
    for node in nodes:
        label_left, label_top, label_right, label_bottom = node_label_box(node.bbox)
        label_left = max(0, label_left)
        label_top = max(0, label_top)
        label_right = min(connector_mask.shape[1], label_right)
        label_bottom = min(connector_mask.shape[0], label_bottom)
        connector_mask[label_top:label_bottom, label_left:label_right] = False

    connectors: list[ExtractedConnector] = []
    degenerate_connector_components = 0
    for points_yx in connected_components(connector_mask):
        if len(points_yx) < MIN_CONNECTOR_PIXELS:
            degenerate_connector_components += 1
            continue
        points_xy = points_yx[:, ::-1].astype(np.float64)
        axis_ends = _principal_axis_ends(points_xy)
        if axis_ends is None:
            degenerate_connector_components += 1
            continue
        low_point, low_spread, high_point, high_spread = axis_ends
        if max(low_spread, high_spread) < CONNECTOR_HEAD_SPREAD_RATIO * min(low_spread, high_spread) + 1e-6:
            degenerate_connector_components += 1
            continue
        if high_spread > low_spread:
            tail_point, head_point = low_point, high_point
        else:
            tail_point, head_point = high_point, low_point
        tail_xy = (float(tail_point[0]), float(tail_point[1]))
        head_xy = (float(head_point[0]), float(head_point[1]))
        from_node_id, from_distance = _nearest_node(tail_xy, node_bboxes)
        to_node_id, to_distance = _nearest_node(head_xy, node_bboxes)
        if from_distance > NODE_ATTACH_TOLERANCE_PX:
            from_node_id = None
        if to_distance > NODE_ATTACH_TOLERANCE_PX:
            to_node_id = None
        length = float(np.hypot(head_xy[0] - tail_xy[0], head_xy[1] - tail_xy[1]))
        connectors.append(
            ExtractedConnector(
                connector_id=f"connector-{len(connectors) + 1:02d}",
                tail_xy=[int(round(tail_xy[0])), int(round(tail_xy[1]))],
                head_xy=[int(round(head_xy[0])), int(round(head_xy[1]))],
                from_node_id=from_node_id,
                to_node_id=to_node_id,
                length_px=round(length, 1),
                confidence=0.85 if from_node_id and to_node_id else 0.4,
            )
        )

    if degenerate_connector_components:
        gaps.append(
            EvidenceGap(
                code="degenerate_connector_geometry",
                message=(
                    f"{degenerate_connector_components} dark component(s) were too small or lacked "
                    "a readable head/tail structure to be treated as connector evidence."
                ),
                check_ids=["connector-links-correct"],
            )
        )

    unresolved_connectors = sum(
        1 for connector in connectors if connector.from_node_id is None or connector.to_node_id is None
    )
    if unresolved_connectors:
        gaps.append(
            EvidenceGap(
                code="unresolved_connector_attachment",
                message=(
                    f"{unresolved_connectors} connector(s) could not be confidently attached to a "
                    "node within the anchor tolerance."
                ),
                check_ids=["connector-links-correct"],
            )
        )

    extraction_confidence = 0.9 if not gaps else max(0.3, 0.9 - 0.2 * len(gaps))
    return FlowchartEvidenceGraph(
        image_id=image_path.stem,
        diagram_type="flowchart",
        nodes=nodes,
        connectors=connectors,
        extraction_confidence=round(extraction_confidence, 2),
        provenance=ExtractionProvenance(
            extractor_id=FLOWCHART_EXTRACTOR_ID,
            extractor_version=FLOWCHART_EXTRACTOR_VERSION,
            backend="shape_and_connector_component",
            metadata_source="none",
        ),
        gaps=gaps,
        metadata={"image_path": str(image_path)},
    )
