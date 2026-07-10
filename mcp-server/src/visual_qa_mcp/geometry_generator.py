from __future__ import annotations

from pathlib import Path
from typing import Any

from PIL import Image, ImageDraw

from .chart_generator import _apply_postprocess, draw_text_centered, get_font
from .geometry_labels import dimension_label_box

BACKGROUND_COLOR = (255, 255, 255)
# Plate gray is deliberately lighter than the arrow-v1 object gray so that the
# label decoder's foreground test (value < 150 is "ink") never mistakes the
# plate surface for glyph strokes.
PLATE_COLOR = (204, 204, 204)
PLATE_OUTLINE_COLOR = (60, 60, 60)
HOLE_FILL_COLOR = (255, 255, 255)
HOLE_OUTLINE_COLOR = (20, 20, 20)

DEFAULT_WIDTH = 600
DEFAULT_HEIGHT = 450
DEFAULT_PLATE_BOX = [110, 100, 490, 350]


def render_geometry_diagram(
    image_path: Path,
    holes: list[dict[str, Any]],
    render_options: dict[str, Any] | None = None,
) -> None:
    """Render a controlled top-view plate with drilled holes and dimension labels.

    Each hole item supports:
      center ([x, y]), diameter_px, label_text (optional),
      outline_width (default 3).
    """
    options = render_options or {}
    width = int(options.get("width", DEFAULT_WIDTH))
    height = int(options.get("height", DEFAULT_HEIGHT))
    plate_box = [float(value) for value in options.get("plate_box", DEFAULT_PLATE_BOX)]

    image = Image.new("RGB", (width, height), BACKGROUND_COLOR)
    draw = ImageDraw.Draw(image)
    draw.rectangle(plate_box, fill=PLATE_COLOR, outline=PLATE_OUTLINE_COLOR, width=2)

    for hole in holes:
        center_x, center_y = (float(value) for value in hole["center"])
        radius = float(hole["diameter_px"]) / 2.0
        outline_width = int(hole.get("outline_width", 3))
        draw.ellipse(
            [center_x - radius, center_y - radius, center_x + radius, center_y + radius],
            fill=HOLE_FILL_COLOR,
            outline=HOLE_OUTLINE_COLOR,
            width=outline_width,
        )
        label_text = hole.get("label_text")
        if label_text:
            label_box = dimension_label_box((center_x, center_y), radius)
            draw_text_centered(draw, label_box, str(label_text), get_font(16), fill=(0, 0, 0))

    image_path.parent.mkdir(parents=True, exist_ok=True)
    image = _apply_postprocess(image, image_path, options)
    image.save(image_path)
