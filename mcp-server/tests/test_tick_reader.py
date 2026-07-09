from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageDraw

from visual_qa_mcp.chart_generator import BACKGROUND_COLOR, get_font
from visual_qa_mcp.tick_reader import read_numeric_text_template


def render_tick_text(text: str, size: tuple[int, int] = (84, 26), font_size: int = 16) -> Image.Image:
    image = Image.new("RGB", size, BACKGROUND_COLOR)
    draw = ImageDraw.Draw(image)
    font = get_font(font_size)
    bbox = draw.textbbox((0, 0), text, font=font)
    x = (size[0] - (bbox[2] - bbox[0])) / 2
    y = (size[1] - (bbox[3] - bbox[1])) / 2
    draw.text((x, y), text, fill=(0, 0, 0), font=font)
    return image


def test_template_tick_reader_reads_positive_integer() -> None:
    text, confidence = read_numeric_text_template(render_tick_text("80"))
    assert text == "80"
    assert confidence > 0.7


def test_template_tick_reader_reads_negative_integer() -> None:
    text, confidence = read_numeric_text_template(render_tick_text("-20"))
    assert text == "-20"
    assert confidence > 0.7


def test_template_tick_reader_returns_none_for_blank_crop() -> None:
    text, confidence = read_numeric_text_template(Image.new("RGB", (84, 26), BACKGROUND_COLOR))
    assert text is None
    assert confidence == 0.0
