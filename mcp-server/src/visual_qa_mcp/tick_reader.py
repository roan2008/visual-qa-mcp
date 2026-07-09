from __future__ import annotations

from functools import lru_cache
from typing import Iterable

import numpy as np
from PIL import Image, ImageDraw

from .chart_generator import BACKGROUND_COLOR, get_font
from .contracts import TickLabel


def _normalize_foreground(image: Image.Image) -> np.ndarray | None:
    gray = np.array(image.convert("L"))
    binary = gray < 220
    coords = np.argwhere(binary)
    if len(coords) == 0:
        return None
    min_row, min_col = coords.min(axis=0)
    max_row, max_col = coords.max(axis=0)
    if (max_row - min_row) * (max_col - min_col) < 12:
        return None
    crop = Image.fromarray((binary[min_row : max_row + 1, min_col : max_col + 1].astype(np.uint8) * 255))
    resized = crop.resize((60, 20))
    return (np.array(resized) > 127).astype(float)


def _difference_score(array_a: np.ndarray, array_b: np.ndarray) -> float:
    return float(np.mean(np.abs(array_a - array_b)))


@lru_cache(maxsize=1)
def _candidate_templates() -> dict[str, list[Image.Image]]:
    templates: dict[str, list[np.ndarray]] = {}
    for value in range(-150, 155, 5):
        text = str(value)
        variants: list[np.ndarray] = []
        for size in (12, 14, 16, 18, 20, 22):
            canvas = Image.new("RGB", (84, 26), BACKGROUND_COLOR)
            draw = ImageDraw.Draw(canvas)
            font = get_font(size)
            bbox = draw.textbbox((0, 0), text, font=font)
            x = (84 - (bbox[2] - bbox[0])) / 2
            y = (26 - (bbox[3] - bbox[1])) / 2
            draw.text((x, y), text, fill=(0, 0, 0), font=font)
            normalized = _normalize_foreground(canvas)
            if normalized is not None:
                variants.append(normalized)
        templates[text] = variants
    return templates


def read_numeric_text_template(crop: Image.Image) -> tuple[str | None, float]:
    normalized_crop = _normalize_foreground(crop)
    if normalized_crop is None:
        return None, 0.0
    best_text: str | None = None
    best_score = float("inf")
    for text, variants in _candidate_templates().items():
        for template in variants:
            score = _difference_score(normalized_crop, template)
            if score < best_score:
                best_text = text
                best_score = score
    if best_text is None:
        return None, 0.0
    confidence = max(0.0, 1.0 - min(best_score / 35.0, 1.0))
    if confidence < 0.6:
        return None, round(confidence, 2)
    return best_text, round(confidence, 2)


def read_tick_texts(
    tick_candidates: Iterable[tuple[Image.Image, list[int]]],
    backend: str = "template",
) -> tuple[list[TickLabel], bool]:
    detections: list[TickLabel] = []
    backend_available = True
    for crop, bbox in tick_candidates:
        text: str | None
        confidence: float
        if backend == "optional_ocr":
            try:
                import pytesseract  # type: ignore
            except Exception:
                backend_available = False
                text, confidence = None, 0.0
            else:
                raw = pytesseract.image_to_string(crop, config="--psm 7 -c tessedit_char_whitelist=-0123456789").strip()
                text = raw or None
                confidence = 0.8 if text is not None else 0.0
        else:
            text, confidence = read_numeric_text_template(crop)

        parsed_value = None
        if text is not None:
            try:
                parsed_value = float(int(text))
            except ValueError:
                text = None
                confidence = 0.0
        detections.append(
            TickLabel(
                text=text,
                parsed_value=parsed_value,
                bbox=bbox,
                confidence=confidence,
            )
        )
    return detections, backend_available
