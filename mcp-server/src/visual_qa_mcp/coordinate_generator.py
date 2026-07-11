from __future__ import annotations

from pathlib import Path
from typing import Any

from PIL import Image, ImageDraw

from .chart_generator import _apply_postprocess, draw_text_centered, get_font
from .coordinate_extractor import point_label_box

BACKGROUND_COLOR = (255, 255, 255)
AXIS_COLOR = (30, 30, 30)
POLYLINE_COLOR = (120, 120, 120)
TEXT_COLOR = (25, 25, 25)

DEFAULT_WIDTH = 700
DEFAULT_HEIGHT = 550
# [left, top, right, bottom]
DEFAULT_PLOT_BOX = [90, 40, 650, 460]

DEFAULT_POINT_RADIUS_PX = 7.0
TICK_MARK_LENGTH_PX = 6


def linear_map(value: float, domain_min: float, domain_max: float, range_min: float, range_max: float) -> float:
    if domain_max == domain_min:
        return range_min
    fraction = (value - domain_min) / (domain_max - domain_min)
    return range_min + fraction * (range_max - range_min)


def x_value_to_pixel(value: float, x_axis: dict[str, Any], plot_box: list[float]) -> float:
    left, _, right, _ = plot_box
    return linear_map(value, float(x_axis["min"]), float(x_axis["max"]), left, right)


def y_value_to_pixel(value: float, y_axis: dict[str, Any], plot_box: list[float]) -> float:
    _, top, _, bottom = plot_box
    # Increasing value moves up the image (toward smaller pixel y).
    return linear_map(value, float(y_axis["min"]), float(y_axis["max"]), bottom, top)


def render_coordinate_diagram(
    image_path: Path,
    points: list[dict[str, Any]],
    polyline_point_ids: list[str] | None,
    x_axis: dict[str, Any],
    y_axis: dict[str, Any],
    render_options: dict[str, Any] | None = None,
    polylines: list[list[str]] | None = None,
) -> None:
    """Render a controlled dual-numeric-axis coordinate plane.

    Each point item supports: id, center_px ([x, y]), rgb, radius_px (optional).
    x_axis/y_axis support: ticks (list of {value, label_text (optional), label_fill (optional)}).
    """
    options = render_options or {}
    width = int(options.get("width", DEFAULT_WIDTH))
    height = int(options.get("height", DEFAULT_HEIGHT))
    plot_box = [float(value) for value in options.get("plot_box", DEFAULT_PLOT_BOX)]
    left, top, right, bottom = plot_box

    image = Image.new("RGB", (width, height), BACKGROUND_COLOR)
    draw = ImageDraw.Draw(image)

    draw.line([(left, top), (left, bottom)], fill=AXIS_COLOR, width=2)
    draw.line([(left, bottom), (right, bottom)], fill=AXIS_COLOR, width=2)

    tick_font = get_font(15)
    for tick in y_axis.get("ticks", []):
        tick_y = y_value_to_pixel(float(tick["value"]), y_axis, plot_box)
        draw.line(
            [(left - TICK_MARK_LENGTH_PX, tick_y), (left, tick_y)], fill=AXIS_COLOR, width=2
        )
        label_box = [int(left - 64), int(tick_y - 10), int(left - 8), int(tick_y + 10)]
        text = str(tick.get("label_text", int(tick["value"])))
        fill = tuple(tick.get("label_fill", TEXT_COLOR))
        draw_text_centered(draw, label_box, text, tick_font, fill=fill)

    for tick in x_axis.get("ticks", []):
        tick_x = x_value_to_pixel(float(tick["value"]), x_axis, plot_box)
        draw.line(
            [(tick_x, bottom), (tick_x, bottom + TICK_MARK_LENGTH_PX)], fill=AXIS_COLOR, width=2
        )
        label_box = [int(tick_x - 25), int(bottom + 8), int(tick_x + 25), int(bottom + 28)]
        text = str(tick.get("label_text", int(tick["value"])))
        fill = tuple(tick.get("label_fill", TEXT_COLOR))
        draw_text_centered(draw, label_box, text, tick_font, fill=fill)

    id_to_point = {point["id"]: point for point in points}
    series_list = polylines if polylines is not None else ([polyline_point_ids] if polyline_point_ids else [])
    for series_point_ids in series_list:
        coords = [tuple(id_to_point[point_id]["center_px"]) for point_id in series_point_ids if point_id in id_to_point]
        if len(coords) >= 2:
            draw.line(coords, fill=POLYLINE_COLOR, width=3, joint="curve")

    label_font = get_font(14)
    for point in points:
        center_x, center_y = (float(value) for value in point["center_px"])
        radius = float(point.get("radius_px", DEFAULT_POINT_RADIUS_PX))
        draw.ellipse(
            [center_x - radius, center_y - radius, center_x + radius, center_y + radius],
            fill=tuple(point["rgb"]),
        )
        label_text = point.get("label_text")
        if label_text:
            label_box = point_label_box([int(center_x), int(center_y)], (width, height))
            draw_text_centered(draw, label_box, str(label_text), label_font, fill=TEXT_COLOR)

    image_path.parent.mkdir(parents=True, exist_ok=True)
    image = _apply_postprocess(image, image_path, options)
    image.save(image_path)
