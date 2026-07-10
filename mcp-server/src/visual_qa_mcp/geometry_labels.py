from __future__ import annotations

from PIL import Image

from .arrow_labels import LabelTemplateCandidate, rank_label_templates, read_label_text

# Fixed dimension-text catalog, mirroring the arrow label catalog: template
# matching against a small closed alphabet, not general OCR. "D10" stands in
# for a diameter callout (unicode diameter signs render inconsistently across
# default PIL fonts, so the catalog sticks to ASCII).
DIMENSION_CATALOG: tuple[str, ...] = ("D6", "D8", "D10", "D12", "D16", "D20")

DIMENSION_LABEL_WIDTH = 70
DIMENSION_LABEL_HEIGHT = 22
DIMENSION_LABEL_GAP_PX = 12.0


def dimension_label_box(center_xy: tuple[float, float], radius_px: float) -> list[int]:
    """Deterministic dimension-text region directly below a hole.

    Both the renderer and the extractor derive this box from the hole's center
    and radius alone, so the extractor needs no spec knowledge to locate the
    text (same trick as arrow_labels.label_anchor_box).
    """
    center_x = center_xy[0]
    top = center_xy[1] + radius_px + DIMENSION_LABEL_GAP_PX
    half_w = DIMENSION_LABEL_WIDTH / 2
    return [
        int(center_x - half_w),
        int(top),
        int(center_x + half_w),
        int(top + DIMENSION_LABEL_HEIGHT),
    ]


def rank_dimension_templates(crop: Image.Image, limit: int = 3) -> list[LabelTemplateCandidate]:
    return rank_label_templates(crop, limit=limit, catalog=DIMENSION_CATALOG)


def read_dimension_text(crop: Image.Image) -> tuple[str | None, float]:
    return read_label_text(crop, catalog=DIMENSION_CATALOG)
