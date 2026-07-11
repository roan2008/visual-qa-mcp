from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache

import numpy as np
from PIL import Image, ImageDraw

from .chart_generator import BACKGROUND_COLOR, get_font

# Fixed catalog of flowchart node labels. Mirrors arrow_labels.py's small,
# fixed-alphabet template-matching approach rather than general OCR.
LABEL_CATALOG: tuple[str, ...] = ("Start", "Input", "Process", "Decision", "Output", "End")

LABEL_BOX_WIDTH = 76
LABEL_BOX_HEIGHT = 22
LABEL_SIDE_OFFSET_PX = 10.0


@dataclass(frozen=True)
class NodeLabelCandidate:
    text: str
    score: float


def node_label_box(bbox: list[int], side_offset: float = LABEL_SIDE_OFFSET_PX) -> list[int]:
    """Deterministic label region to the right of a node's bbox, on white background.

    Placing the label beside the node (not on top of its colored fill) keeps the
    achromatic-glyph mask reliable regardless of the node's fill color, mirroring
    arrow_labels.label_anchor_box's rationale for staying off the colored object.
    """
    left, top, right, bottom = bbox
    center_y = (top + bottom) / 2.0
    x0 = right + side_offset
    return [
        int(x0),
        int(center_y - LABEL_BOX_HEIGHT / 2),
        int(x0 + LABEL_BOX_WIDTH),
        int(center_y + LABEL_BOX_HEIGHT / 2),
    ]


def _normalize_foreground(image: Image.Image) -> np.ndarray | None:
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
    resized = crop.resize((64, 20))
    return (np.array(resized) > 127).astype(float)


def _difference_score(array_a: np.ndarray, array_b: np.ndarray) -> float:
    return float(np.mean(np.abs(array_a - array_b)))


@lru_cache(maxsize=8)
def _candidate_templates(catalog: tuple[str, ...] = LABEL_CATALOG) -> dict[str, list[np.ndarray]]:
    templates: dict[str, list[np.ndarray]] = {}
    for text in catalog:
        variants: list[np.ndarray] = []
        for size in (11, 12, 13):
            canvas = Image.new("RGB", (LABEL_BOX_WIDTH, LABEL_BOX_HEIGHT + 4), BACKGROUND_COLOR)
            draw = ImageDraw.Draw(canvas)
            font = get_font(size)
            bbox = draw.textbbox((0, 0), text, font=font)
            x = (LABEL_BOX_WIDTH - (bbox[2] - bbox[0])) / 2
            y = ((LABEL_BOX_HEIGHT + 4) - (bbox[3] - bbox[1])) / 2
            draw.text((x, y), text, fill=(0, 0, 0), font=font)
            normalized = _normalize_foreground(canvas)
            if normalized is not None:
                variants.append(normalized)
        templates[text] = variants
    return templates


def rank_node_label_templates(
    crop: Image.Image,
    limit: int = 3,
    catalog: tuple[str, ...] = LABEL_CATALOG,
) -> list[NodeLabelCandidate]:
    normalized_crop = _normalize_foreground(crop)
    if normalized_crop is None:
        return []
    ranked = [
        NodeLabelCandidate(
            text=text,
            score=min(_difference_score(normalized_crop, template) for template in variants),
        )
        for text, variants in _candidate_templates(catalog).items()
        if variants
    ]
    ranked.sort(key=lambda candidate: candidate.score)
    return ranked[:limit]


def read_node_label_text(
    crop: Image.Image,
    catalog: tuple[str, ...] = LABEL_CATALOG,
) -> tuple[str | None, float]:
    ranked = rank_node_label_templates(crop, limit=2, catalog=catalog)
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
