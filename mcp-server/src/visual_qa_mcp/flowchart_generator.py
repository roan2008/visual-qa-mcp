from __future__ import annotations

from pathlib import Path
from typing import Any

from PIL import Image, ImageDraw

from .chart_generator import _apply_postprocess, draw_text_centered, get_font
from .flowchart_labels import node_label_box, read_node_label_text

BACKGROUND_COLOR = (255, 255, 255)
# Kept in a mid-gray band distinct from both white background and pure-black
# label text so the extractor's connector mask can exclude label glyphs by
# value range alone (mirrors arrow_extractor's gray-object-vs-black-label split).
CONNECTOR_COLOR = (95, 95, 95)
LABEL_TEXT_COLOR = (0, 0, 0)

DEFAULT_WIDTH = 420
DEFAULT_HEIGHT = 700
DEFAULT_NODE_SIZE = [140, 60]
CONNECTOR_GAP_PX = 6.0


def _node_bbox(center_px: list[float], size_px: list[float]) -> list[float]:
    cx, cy = center_px
    half_w, half_h = size_px[0] / 2.0, size_px[1] / 2.0
    return [cx - half_w, cy - half_h, cx + half_w, cy + half_h]


def _draw_node(draw: ImageDraw.ImageDraw, node: dict[str, Any]) -> list[float]:
    bbox = _node_bbox(node["center_px"], node.get("size_px", DEFAULT_NODE_SIZE))
    left, top, right, bottom = bbox
    cx, cy = node["center_px"]
    rgb = tuple(node["rgb"])
    if node["shape"] == "diamond":
        draw.polygon(
            [(cx, top), (right, cy), (cx, bottom), (left, cy)],
            fill=rgb,
        )
    else:
        draw.rectangle(bbox, fill=rgb)
    return bbox


def _anchor_toward(center: list[float], size: list[float], shape: str, target: tuple[float, float]) -> tuple[float, float]:
    """Point on a node's boundary along the ray from its center toward `target`.

    Works for any direction (straight-down chain or diagonal branch) since it is
    a plain boundary intersection, not a hardcoded top/bottom anchor.
    """
    cx, cy = center
    tx, ty = target
    dx, dy = tx - cx, ty - cy
    half_w, half_h = size[0] / 2.0, size[1] / 2.0
    if shape == "diamond":
        denom = abs(dx) / half_w + abs(dy) / half_h
        if denom == 0:
            return cx, cy
        t = 1.0 / denom
    else:
        if dx == 0:
            t = half_h / abs(dy)
        elif dy == 0:
            t = half_w / abs(dx)
        else:
            t = min(half_w / abs(dx), half_h / abs(dy))
    return cx + dx * t, cy + dy * t


def _draw_connector_arrow(
    draw: ImageDraw.ImageDraw,
    tail_xy: tuple[float, float],
    head_xy: tuple[float, float],
    color: tuple[int, int, int] = CONNECTOR_COLOR,
    shaft_width: int = 4,
    head_length: float = 14.0,
    head_half_width: float = 8.0,
) -> None:
    dx = head_xy[0] - tail_xy[0]
    dy = head_xy[1] - tail_xy[1]
    length = max((dx * dx + dy * dy) ** 0.5, 1e-6)
    unit_x, unit_y = dx / length, dy / length
    shaft_end = (head_xy[0] - unit_x * head_length, head_xy[1] - unit_y * head_length)
    draw.line([tail_xy, shaft_end], fill=color, width=shaft_width)
    perp_x, perp_y = -unit_y, unit_x
    draw.polygon(
        [
            head_xy,
            (shaft_end[0] + perp_x * head_half_width, shaft_end[1] + perp_y * head_half_width),
            (shaft_end[0] - perp_x * head_half_width, shaft_end[1] - perp_y * head_half_width),
        ],
        fill=color,
    )


def render_flowchart_diagram(
    image_path: Path,
    nodes: list[dict[str, Any]],
    connectors: list[dict[str, Any]],
    render_options: dict[str, Any] | None = None,
) -> None:
    """Render a controlled vertical-chain flowchart.

    Each node item supports: id, shape ("rectangle" or "diamond"), rgb, center_px
    ([x, y]), size_px (optional [w, h]), label_text (optional).
    Each connector item supports: from_id, to_id (both must reference declared node
    ids); the connector is drawn as a straight arrow between the boundary anchor of
    the "from" node and the boundary anchor of the "to" node, computed along the
    line between their centers, so both a straight vertical chain and a diagonal
    branch are rendered correctly.
    """
    options = render_options or {}
    width = int(options.get("width", DEFAULT_WIDTH))
    height = int(options.get("height", DEFAULT_HEIGHT))

    image = Image.new("RGB", (width, height), BACKGROUND_COLOR)
    draw = ImageDraw.Draw(image)

    node_by_id = {node["id"]: node for node in nodes}
    bbox_by_id: dict[str, list[float]] = {}

    for connector in connectors:
        from_node = node_by_id.get(connector["from_id"])
        to_node = node_by_id.get(connector["to_id"])
        if from_node is None or to_node is None:
            continue
        from_size = from_node.get("size_px", DEFAULT_NODE_SIZE)
        to_size = to_node.get("size_px", DEFAULT_NODE_SIZE)
        raw_tail = _anchor_toward(from_node["center_px"], from_size, from_node["shape"], tuple(to_node["center_px"]))
        raw_head = _anchor_toward(to_node["center_px"], to_size, to_node["shape"], tuple(from_node["center_px"]))
        dx = raw_head[0] - raw_tail[0]
        dy = raw_head[1] - raw_tail[1]
        gap_length = max((dx * dx + dy * dy) ** 0.5, 1e-6)
        unit_x, unit_y = dx / gap_length, dy / gap_length
        tail_xy = (raw_tail[0] + unit_x * CONNECTOR_GAP_PX, raw_tail[1] + unit_y * CONNECTOR_GAP_PX)
        head_xy = (raw_head[0] - unit_x * CONNECTOR_GAP_PX, raw_head[1] - unit_y * CONNECTOR_GAP_PX)
        _draw_connector_arrow(draw, tail_xy, head_xy)

    for node in nodes:
        bbox = _draw_node(draw, node)
        bbox_by_id[node["id"]] = bbox
        label_text = node.get("label_text")
        if label_text:
            label_box = node_label_box([int(round(value)) for value in bbox])
            draw_text_centered(draw, label_box, str(label_text), get_font(14), fill=LABEL_TEXT_COLOR)

    image_path.parent.mkdir(parents=True, exist_ok=True)
    image = _apply_postprocess(image, image_path, options)
    image.save(image_path)


__all__ = [
    "render_flowchart_diagram",
    "read_node_label_text",
    "DEFAULT_NODE_SIZE",
    "DEFAULT_WIDTH",
    "DEFAULT_HEIGHT",
]
