from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache

import numpy as np
from PIL import Image, ImageDraw

from .chart_generator import BACKGROUND_COLOR, get_font

LABEL_CATALOG: tuple[str, ...] = ("W", "N", "F", "f", "T", "P", "Fx", "Fy")

LABEL_BOX_WIDTH = 70
LABEL_BOX_HEIGHT = 22
LABEL_SIDE_OFFSET_PX = 38.0


@dataclass(frozen=True)
class LabelTemplateCandidate:
    text: str
    score: float


def label_anchor_box(
    tail_xy: tuple[float, float],
    head_xy: tuple[float, float],
    side_offset: float = LABEL_SIDE_OFFSET_PX,
) -> list[int]:
    """Deterministic label region beside the arrow's midpoint, offset perpendicular
    to the shaft.

    Using the tail/head midpoint (rather than the tail alone) keeps the box clear of
    the object it is anchored to, since real anchors sit exactly on the object's
    edge. Both the renderer and the extractor derive this box from the same
    tail_xy/head_xy pair, so no spec knowledge is required to locate it.
    """
    tail = np.array(tail_xy, dtype=float)
    head = np.array(head_xy, dtype=float)
    direction = head - tail
    length = float(np.hypot(direction[0], direction[1]))
    if length < 1e-6:
        unit = np.array([1.0, 0.0])
    else:
        unit = direction / length
    perp = np.array([-unit[1], unit[0]])
    midpoint = (tail + head) / 2.0
    center = midpoint + perp * side_offset
    half_w, half_h = LABEL_BOX_WIDTH / 2, LABEL_BOX_HEIGHT / 2
    return [
        int(center[0] - half_w),
        int(center[1] - half_h),
        int(center[0] + half_w),
        int(center[1] + half_h),
    ]


def _normalize_foreground(image: Image.Image) -> np.ndarray | None:
    # Only treat achromatic (low-saturation) dark pixels as text foreground so a
    # saturated arrow color bleeding into the crop edge is never mistaken for a
    # glyph stroke.
    rgb = np.array(image.convert("RGB")).astype(np.int16)
    spread = rgb.max(axis=2) - rgb.min(axis=2)
    value = rgb.mean(axis=2)
    binary = (spread <= 30) & (value < 150)
    coords = np.argwhere(binary)
    if len(coords) == 0:
        return None
    min_row, min_col = coords.min(axis=0)
    max_row, max_col = coords.max(axis=0)
    if (max_row - min_row) * (max_col - min_col) < 8:
        return None
    crop = Image.fromarray((binary[min_row : max_row + 1, min_col : max_col + 1].astype(np.uint8) * 255))
    resized = crop.resize((60, 20))
    return (np.array(resized) > 127).astype(float)


def _difference_score(array_a: np.ndarray, array_b: np.ndarray) -> float:
    return float(np.mean(np.abs(array_a - array_b)))


@lru_cache(maxsize=8)
def _candidate_templates(catalog: tuple[str, ...] = LABEL_CATALOG) -> dict[str, list[np.ndarray]]:
    templates: dict[str, list[np.ndarray]] = {}
    for text in catalog:
        variants: list[np.ndarray] = []
        for size in (12, 14, 16, 18):
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


def rank_label_templates(
    crop: Image.Image,
    limit: int = 3,
    catalog: tuple[str, ...] = LABEL_CATALOG,
) -> list[LabelTemplateCandidate]:
    normalized_crop = _normalize_foreground(crop)
    if normalized_crop is None:
        return []
    ranked = [
        LabelTemplateCandidate(
            text=text,
            score=min(_difference_score(normalized_crop, template) for template in variants),
        )
        for text, variants in _candidate_templates(catalog).items()
        if variants
    ]
    ranked.sort(key=lambda candidate: candidate.score)
    return ranked[:limit]


def read_label_text(
    crop: Image.Image,
    catalog: tuple[str, ...] = LABEL_CATALOG,
) -> tuple[str | None, float]:
    ranked = rank_label_templates(crop, limit=2, catalog=catalog)
    if not ranked:
        return None, 0.0
    best = ranked[0]
    runner_up_score = ranked[1].score if len(ranked) > 1 else None
    margin = (runner_up_score - best.score) if runner_up_score is not None else 1.0
    if best.score > 0.34 or (best.score > 0.05 and margin < 0.02):
        return None, 0.0
    absolute_quality = max(0.0, 1.0 - best.score / 0.4)
    margin_quality = min(1.0, margin / 0.08) if runner_up_score is not None else 1.0
    confidence = round(min(1.0, 0.55 + 0.35 * absolute_quality + 0.10 * margin_quality), 2)
    return best.text, confidence
