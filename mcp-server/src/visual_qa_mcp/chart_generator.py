from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from PIL import Image, ImageDraw, ImageFont

from .chart_layout import ChartLayout

BAR_COLOR = (53, 120, 246)
AXIS_COLOR = (32, 32, 32)
TEXT_COLOR = (25, 25, 25)
BACKGROUND_COLOR = (255, 255, 255)
GRID_COLOR = (222, 226, 234)


def get_font(size: int = 16) -> ImageFont.ImageFont:
    try:
        return ImageFont.truetype("arial.ttf", size)
    except OSError:
        return ImageFont.load_default()


def draw_text_centered(
    draw: ImageDraw.ImageDraw,
    box: list[int],
    text: str,
    font: ImageFont.ImageFont,
    fill: tuple[int, int, int] = TEXT_COLOR,
) -> None:
    bbox = draw.textbbox((0, 0), text, font=font)
    text_width = bbox[2] - bbox[0]
    text_height = bbox[3] - bbox[1]
    x = box[0] + (box[2] - box[0] - text_width) / 2
    y = box[1] + (box[3] - box[1] - text_height) / 2
    draw.text((x, y), text, fill=fill, font=font)


def render_chart_image(
    image_path: Path,
    data: list[dict[str, Any]],
    axis_config: dict[str, Any],
    metadata: dict[str, Any],
    layout: ChartLayout | None = None,
) -> None:
    layout = layout or ChartLayout()
    if "layout_overrides" in metadata:
        layout = layout.with_overrides(**metadata["layout_overrides"])

    axis_min = float(axis_config["bar_axis"]["min"])
    axis_max = float(axis_config["bar_axis"]["max"])
    display_ticks = axis_config["display_ticks"]
    zero_value = 0.0 if axis_min <= 0 <= axis_max else axis_min

    image = Image.new("RGB", (layout.width, layout.height), BACKGROUND_COLOR)
    draw = ImageDraw.Draw(image)
    axis_font = get_font(int(metadata.get("axis_font_size", 16)))
    tick_font = get_font(int(metadata.get("tick_font_size", 15)))
    small_font = get_font(int(metadata.get("x_label_font_size", 14)))
    axis_label_fill = tuple(metadata.get("axis_label_fill", TEXT_COLOR))
    tick_label_fill = tuple(metadata.get("tick_label_fill", TEXT_COLOR))
    bar_fill = tuple(metadata.get("bar_fill", BAR_COLOR))
    axis_fill = tuple(metadata.get("axis_fill", AXIS_COLOR))
    grid_fill = tuple(metadata.get("grid_fill", GRID_COLOR))

    tick_jitter = metadata.get("tick_jitter", {})
    tick_text_overrides = metadata.get("tick_text_overrides", {})
    tick_fill_overrides = metadata.get("tick_fill_overrides", {})
    for tick_value in display_ticks:
        tick_y = layout.value_to_y(float(tick_value), axis_min, axis_max) + int(tick_jitter.get(str(tick_value), 0))
        draw.line([(layout.plot_left, tick_y), (layout.plot_right, tick_y)], fill=grid_fill, width=1)
        draw.line([(layout.plot_left - 6, tick_y), (layout.plot_left, tick_y)], fill=axis_fill, width=2)
        tick_box = layout.tick_label_box(tick_y)
        tick_text = str(tick_text_overrides.get(str(tick_value), int(tick_value)))
        fill = tuple(tick_fill_overrides.get(str(tick_value), tick_label_fill))
        draw_text_centered(draw, tick_box, tick_text, tick_font, fill=fill)

    draw.line([(layout.plot_left, layout.plot_top), (layout.plot_left, layout.plot_bottom)], fill=axis_fill, width=3)
    baseline_y = layout.value_to_y(zero_value, axis_min, axis_max)
    draw.line([(layout.plot_left, baseline_y), (layout.plot_right, baseline_y)], fill=axis_fill, width=3)

    slot_count = len(data)
    for index, item in enumerate(data):
        box = layout.bar_box(
            bar_index=index,
            bar_count=slot_count,
            value=float(item["value"]),
            axis_min=axis_min,
            axis_max=axis_max,
            baseline_value=zero_value,
        )
        draw.rectangle(box, fill=bar_fill)
        center_x = (box[0] + box[2]) // 2
        label_box = layout.label_box(center_x)
        draw_text_centered(draw, label_box, item["label"], small_font)

    axis_label_box = list(layout.axis_label_box)
    draw_text_centered(draw, axis_label_box, axis_config["y_label"], axis_font, fill=axis_label_fill)

    image.save(image_path)


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
