from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

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

    image = _apply_postprocess(image, image_path, metadata)
    image.save(image_path)


def _apply_postprocess(image: Image.Image, image_path: Path, metadata: dict[str, Any]) -> Image.Image:
    postprocess = metadata.get("postprocess", {})
    downscale_factor = float(postprocess.get("downscale_factor", 1.0))
    if downscale_factor < 1.0:
        resized = image.resize(
            (max(32, int(image.width * downscale_factor)), max(32, int(image.height * downscale_factor))),
            resample=Image.Resampling.BILINEAR,
        )
        image = resized.resize(image.size, resample=Image.Resampling.BILINEAR)
    blur_radius = float(postprocess.get("blur_radius", 0.0))
    if blur_radius > 0:
        image = image.filter(ImageFilter.GaussianBlur(radius=blur_radius))

    jpeg_quality = postprocess.get("jpeg_quality")
    if jpeg_quality is not None:
        temp_jpeg = image_path.with_suffix(".tmp-phase2.jpg")
        image.save(temp_jpeg, quality=int(jpeg_quality))
        image = Image.open(temp_jpeg).convert("RGB")
        temp_jpeg.unlink(missing_ok=True)
    return image


def render_matplotlib_chart_image(
    image_path: Path,
    data: list[dict[str, Any]],
    axis_config: dict[str, Any],
    metadata: dict[str, Any],
) -> None:
    try:
        import matplotlib

        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
    except ImportError as exc:  # pragma: no cover - environment guard
        raise RuntimeError("Matplotlib is required to generate the real-world pilot dataset.") from exc

    layout = ChartLayout()
    if "layout_overrides" in metadata:
        layout = layout.with_overrides(**metadata["layout_overrides"])
    dpi = 100
    fig = plt.figure(figsize=(layout.width / dpi, layout.height / dpi), dpi=dpi, facecolor="white")
    axes_left = layout.plot_left / layout.width
    axes_bottom = (layout.height - layout.plot_bottom) / layout.height
    axes_width = layout.plot_width / layout.width
    axes_height = layout.plot_height / layout.height
    ax = fig.add_axes([axes_left, axes_bottom, axes_width, axes_height])

    axis_min = float(axis_config["bar_axis"]["min"])
    axis_max = float(axis_config["bar_axis"]["max"])
    ticks = [float(value) for value in axis_config["display_ticks"]]
    labels = [str(item["label"]) for item in data]
    values = [float(item["value"]) for item in data]
    font_family = str(metadata.get("font_family", "Arial"))
    bar_color = tuple(channel / 255 for channel in metadata.get("bar_fill", BAR_COLOR))
    grid_color = tuple(channel / 255 for channel in metadata.get("grid_fill", GRID_COLOR))
    text_color = tuple(channel / 255 for channel in metadata.get("tick_label_fill", TEXT_COLOR))
    ax.bar(range(len(values)), values, color=bar_color, width=0.62, zorder=3)
    ax.set_xlim(-0.5, len(values) - 0.5)
    ax.set_ylim(axis_min, axis_max)
    ax.set_xticks(
        range(len(labels)),
        labels,
        fontsize=int(metadata.get("x_label_font_size", 14)),
        fontfamily=font_family,
    )
    tick_overrides = metadata.get("tick_text_overrides", {})
    tick_labels = [str(tick_overrides.get(str(int(value)), int(value))) for value in ticks]
    ax.set_yticks(
        ticks,
        tick_labels,
        fontsize=int(metadata.get("tick_font_size", 15)),
        fontfamily=font_family,
    )
    ax.grid(axis="y", color=grid_color, linewidth=1, zorder=0)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.spines["left"].set_linewidth(2)
    ax.spines["bottom"].set_linewidth(2)
    ax.tick_params(axis="y", colors=text_color, pad=22)
    ax.tick_params(axis="x", colors=text_color, pad=18, length=0)
    label_color = tuple(channel / 255 for channel in metadata.get("axis_label_fill", TEXT_COLOR))
    fig.text(
        0.56,
        0.92,
        axis_config["y_label"],
        ha="center",
        va="center",
        fontsize=int(metadata.get("axis_font_size", 16)),
        fontfamily=font_family,
        color=label_color,
    )
    fig.canvas.draw()
    rgba = np.asarray(fig.canvas.buffer_rgba())
    image = Image.fromarray(rgba[:, :, :3].copy(), mode="RGB")
    plt.close(fig)
    image = _apply_postprocess(image, image_path, metadata)
    image.save(image_path)


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
