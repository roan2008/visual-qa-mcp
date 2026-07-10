from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache
from itertools import product
from typing import Iterable

import numpy as np
from PIL import Image, ImageDraw

from .chart_generator import BACKGROUND_COLOR, get_font
from .contracts import TickLabel


@dataclass(frozen=True)
class NumericTemplateCandidate:
    text: str
    value: int
    score: float


@dataclass(frozen=True)
class TickSequenceDecodeResult:
    selected: list[NumericTemplateCandidate | None] | None
    ambiguous: bool = False


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
def _candidate_templates() -> dict[str, list[np.ndarray]]:
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


def rank_numeric_text_templates(crop: Image.Image, limit: int = 5) -> list[NumericTemplateCandidate]:
    normalized_crop = _normalize_foreground(crop)
    if normalized_crop is None:
        return []
    ranked: list[NumericTemplateCandidate] = []
    for text, variants in _candidate_templates().items():
        score = min(_difference_score(normalized_crop, template) for template in variants)
        ranked.append(NumericTemplateCandidate(text=text, value=int(text), score=score))
    ranked.sort(key=lambda candidate: candidate.score)
    if not ranked:
        return []
    best_score = ranked[0].score
    return [
        candidate for candidate in ranked[:limit]
        if candidate.score <= 0.36 and candidate.score <= best_score + 0.04
    ]


def _candidate_confidence(candidate: NumericTemplateCandidate, runner_up_score: float | None = None) -> float:
    absolute_quality = max(0.0, 1.0 - candidate.score / 0.45)
    if runner_up_score is None:
        margin_quality = 1.0
    else:
        margin_quality = min(1.0, max(0.0, (runner_up_score - candidate.score) / 0.06))
    return round(min(1.0, 0.55 + 0.35 * absolute_quality + 0.10 * margin_quality), 2)


def read_numeric_text_template(crop: Image.Image) -> tuple[str | None, float]:
    ranked = rank_numeric_text_templates(crop, limit=2)
    if not ranked:
        return None, 0.0
    best = ranked[0]
    runner_up_score = ranked[1].score if len(ranked) > 1 else None
    margin = (runner_up_score - best.score) if runner_up_score is not None else 1.0
    confidence = _candidate_confidence(best, runner_up_score)
    if best.score > 0.34 or (best.score > 0.05 and margin < 0.01):
        return None, confidence
    return best.text, confidence


def _decode_tick_sequence_result(
    ranked_rows: list[list[NumericTemplateCandidate]],
    centers: list[float],
) -> TickSequenceDecodeResult:
    choices: list[list[NumericTemplateCandidate | None]] = []
    for ranked in ranked_rows:
        choices.append([*ranked, None] if ranked else [None])

    scored: list[tuple[float, tuple[NumericTemplateCandidate | None, ...]]] = []
    for assignment in product(*choices):
        selected = [(centers[index], candidate) for index, candidate in enumerate(assignment) if candidate is not None]
        if len(selected) < 3:
            continue
        values = np.array([candidate.value for _, candidate in selected], dtype=float)
        positions = np.array([center for center, _ in selected], dtype=float)
        if any(values[index] <= values[index + 1] for index in range(len(values) - 1)):
            continue
        slope, intercept = np.polyfit(positions, values, 1)
        if slope >= 0:
            continue
        predicted = slope * positions + intercept
        value_span = max(float(values.max() - values.min()), 5.0)
        normalized_residual = float(np.sqrt(np.mean((predicted - values) ** 2)) / value_span)
        if normalized_residual > 0.018:
            continue
        visual_score = float(np.mean([candidate.score for _, candidate in selected]))
        missing_penalty = 0.03 * (len(assignment) - len(selected))
        total_score = visual_score + normalized_residual * 3.0 + missing_penalty
        scored.append((total_score, assignment))

    if not scored:
        return TickSequenceDecodeResult(selected=None)
    scored.sort(key=lambda item: item[0])
    best_score, best_assignment = scored[0]
    materially_different = [
        item for item in scored[1:]
        if tuple(candidate.value if candidate is not None else None for candidate in item[1])
        != tuple(candidate.value if candidate is not None else None for candidate in best_assignment)
    ]
    if materially_different and materially_different[0][0] - best_score < 0.006:
        return TickSequenceDecodeResult(selected=None, ambiguous=True)
    return TickSequenceDecodeResult(selected=list(best_assignment))


def _decode_tick_sequence(
    ranked_rows: list[list[NumericTemplateCandidate]],
    centers: list[float],
) -> list[NumericTemplateCandidate | None] | None:
    return _decode_tick_sequence_result(ranked_rows, centers).selected


def _fallback_individual_candidate(ranked: list[NumericTemplateCandidate]) -> NumericTemplateCandidate | None:
    if not ranked:
        return None
    best = ranked[0]
    runner_up_score = ranked[1].score if len(ranked) > 1 else None
    margin = (runner_up_score - best.score) if runner_up_score is not None else 1.0
    if best.score <= 0.34 and (best.score <= 0.05 or margin >= 0.01):
        return best
    return None


def read_tick_texts(
    tick_candidates: Iterable[tuple[Image.Image, list[int]]],
    backend: str = "template",
) -> tuple[list[TickLabel], bool]:
    candidate_inputs = list(tick_candidates)
    detections: list[TickLabel] = []
    backend_available = True
    if backend == "template":
        ranked_rows = [rank_numeric_text_templates(crop) for crop, _ in candidate_inputs]
        centers = [((bbox[1] + bbox[3]) / 2) for _, bbox in candidate_inputs]
        decode_result = _decode_tick_sequence_result(ranked_rows, centers)
        if decode_result.ambiguous:
            # Do not collapse a near-tied global sequence back into individually
            # plausible digits. Unresolved required scale evidence must remain
            # unresolved so downstream validation produces needs_review.
            selected = [None for _ in ranked_rows]
        elif decode_result.selected is not None:
            selected = decode_result.selected
        else:
            selected = [_fallback_individual_candidate(ranked) for ranked in ranked_rows]
        for (_, bbox), ranked, candidate in zip(candidate_inputs, ranked_rows, selected, strict=True):
            if candidate is None:
                text, parsed_value, confidence = None, None, 0.0
            else:
                runner_up_score = next(
                    (item.score for item in ranked if item.value != candidate.value),
                    None,
                )
                text = candidate.text
                parsed_value = float(candidate.value)
                confidence = _candidate_confidence(candidate, runner_up_score)
            detections.append(
                TickLabel(
                    text=text,
                    parsed_value=parsed_value,
                    bbox=bbox,
                    confidence=confidence,
                )
            )
        return detections, backend_available

    for crop, bbox in candidate_inputs:
        text: str | None
        confidence: float
        try:
            import pytesseract  # type: ignore
        except Exception:
            backend_available = False
            text, confidence = None, 0.0
        else:
            raw = pytesseract.image_to_string(crop, config="--psm 7 -c tessedit_char_whitelist=-0123456789").strip()
            text = raw or None
            confidence = 0.8 if text is not None else 0.0

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
