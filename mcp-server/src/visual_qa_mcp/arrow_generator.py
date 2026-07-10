from __future__ import annotations

import math
from pathlib import Path
from typing import Any

from PIL import Image, ImageDraw

from .arrow_labels import label_anchor_box
from .chart_generator import _apply_postprocess, draw_text_centered, get_font

BACKGROUND_COLOR = (255, 255, 255)
OBJECT_COLOR = (135, 135, 135)

DEFAULT_WIDTH = 600
DEFAULT_HEIGHT = 450
DEFAULT_OBJECT_BOX = [240, 210, 360, 300]


def _unit_vector(angle_degrees: float) -> tuple[float, float]:
    radians = math.radians(angle_degrees)
    # Image y grows downward, so a positive angle (counterclockwise, 0 = right,
    # 90 = up) maps to a negative y component.
    return math.cos(radians), -math.sin(radians)


def draw_arrow(
    draw: ImageDraw.ImageDraw,
    tail_xy: tuple[float, float],
    angle_degrees: float,
    length_px: float,
    color: tuple[int, int, int],
    shaft_width: int = 5,
    head_length: float = 16.0,
    head_half_width: float = 9.0,
) -> None:
    dx, dy = _unit_vector(angle_degrees)
    head_tip = (tail_xy[0] + dx * length_px, tail_xy[1] + dy * length_px)
    shaft_end = (
        tail_xy[0] + dx * (length_px - head_length),
        tail_xy[1] + dy * (length_px - head_length),
    )
    draw.line([tail_xy, shaft_end], fill=color, width=shaft_width)
    perp_x, perp_y = -dy, dx
    draw.polygon(
        [
            head_tip,
            (shaft_end[0] + perp_x * head_half_width, shaft_end[1] + perp_y * head_half_width),
            (shaft_end[0] - perp_x * head_half_width, shaft_end[1] - perp_y * head_half_width),
        ],
        fill=color,
    )


def _anchor_point(object_box: list[float], anchor: str) -> tuple[float, float]:
    left, top, right, bottom = object_box
    center_x = (left + right) / 2
    center_y = (top + bottom) / 2
    anchors = {
        "top_center": (center_x, top),
        "bottom_center": (center_x, bottom),
        "left_center": (left, center_y),
        "right_center": (right, center_y),
        "center": (center_x, center_y),
    }
    return anchors[anchor]


def render_arrow_diagram(
    image_path: Path,
    arrows: list[dict[str, Any]],
    render_options: dict[str, Any] | None = None,
) -> None:
    """Render a controlled free-body style diagram.

    Each arrow item supports:
      rgb, anchor (named object anchor), angle_degrees, length_px,
      tail_offset ([dx, dy] applied to the anchor point),
      shaft_width, head_length, head_half_width.
    """
    options = render_options or {}
    width = int(options.get("width", DEFAULT_WIDTH))
    height = int(options.get("height", DEFAULT_HEIGHT))
    object_box = [float(value) for value in options.get("object_box", DEFAULT_OBJECT_BOX)]
    object_fill = tuple(options.get("object_fill", OBJECT_COLOR))

    image = Image.new("RGB", (width, height), BACKGROUND_COLOR)
    draw = ImageDraw.Draw(image)
    draw.rectangle(object_box, fill=object_fill)

    for arrow in arrows:
        tail_x, tail_y = _anchor_point(object_box, arrow.get("anchor", "center"))
        offset = arrow.get("tail_offset", [0, 0])
        tail_xy = (tail_x + float(offset[0]), tail_y + float(offset[1]))
        angle_degrees = float(arrow["angle_degrees"])
        length_px = float(arrow.get("length_px", 90.0))
        draw_arrow(
            draw,
            tail_xy=tail_xy,
            angle_degrees=angle_degrees,
            length_px=length_px,
            color=tuple(arrow["rgb"]),
            shaft_width=int(arrow.get("shaft_width", 5)),
            head_length=float(arrow.get("head_length", 16.0)),
            head_half_width=float(arrow.get("head_half_width", 9.0)),
        )
        label_text = arrow.get("label_text")
        if label_text:
            head_dx, head_dy = _unit_vector(angle_degrees)
            head_xy = (tail_xy[0] + head_dx * length_px, tail_xy[1] + head_dy * length_px)
            label_box = label_anchor_box(tail_xy, head_xy)
            draw_text_centered(draw, label_box, str(label_text), get_font(16), fill=(0, 0, 0))

    image_path.parent.mkdir(parents=True, exist_ok=True)
    image = _apply_postprocess(image, image_path, options)
    image.save(image_path)
