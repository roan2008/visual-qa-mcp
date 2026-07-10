from __future__ import annotations

import math

from .chart_rules import (
    _estimate_rule_confidence,
    _make_finding,
    _overall_verdict,
    _severity_rank,
)
from .contracts import (
    ClaimGraph,
    ExtractedHole,
    Finding,
    GeometryEvidenceGraph,
    OverlayAnnotation,
    VisualQaReport,
)

# Holes have no color or per-feature identity marker, so v1 pairs detected
# holes with expected holes by left-to-right (then top-to-bottom) order. Specs
# must list holes in that nominal order; this is a stated v1 bound.
PAIRING_NOTE = (
    "hole identity pairing uses left-to-right order and requires the detected "
    "hole count to equal the expected hole count"
)


def _paired_holes(
    expected_ordered: list[dict],
    detected: list[ExtractedHole],
) -> dict[str, ExtractedHole] | None:
    if len(expected_ordered) != len(detected):
        return None
    return {
        expected["id"]: hole
        for expected, hole in zip(expected_ordered, detected, strict=True)
    }


def _line_fit_residuals(centers: list[list[int]]) -> tuple[list[float], list[float]]:
    """Perpendicular residuals from the best-fit line plus projections along it."""
    xs = [float(center[0]) for center in centers]
    ys = [float(center[1]) for center in centers]
    mean_x = sum(xs) / len(xs)
    mean_y = sum(ys) / len(ys)
    sxx = sum((x - mean_x) ** 2 for x in xs) / len(xs)
    syy = sum((y - mean_y) ** 2 for y in ys) / len(ys)
    sxy = sum((x - mean_x) * (y - mean_y) for x, y in zip(xs, ys, strict=True)) / len(xs)
    theta = 0.5 * math.atan2(2.0 * sxy, sxx - syy)
    axis_x, axis_y = math.cos(theta), math.sin(theta)
    residuals = [
        abs(-(x - mean_x) * axis_y + (y - mean_y) * axis_x)
        for x, y in zip(xs, ys, strict=True)
    ]
    projections = [
        (x - mean_x) * axis_x + (y - mean_y) * axis_y for x, y in zip(xs, ys, strict=True)
    ]
    return residuals, projections


def run_geometry_claims(
    claim_graph: ClaimGraph, evidence: GeometryEvidenceGraph
) -> VisualQaReport:
    claims = {claim.check_id: claim for claim in claim_graph.claims}

    findings: list[Finding] = []
    checks_run: list[str] = []
    checks_skipped: list[dict[str, str]] = []
    overlay_annotations: list[OverlayAnnotation] = []

    skipped_by_check: dict[str, list[str]] = {}
    for gap in evidence.gaps:
        for check_id in gap.check_ids:
            skipped_by_check.setdefault(check_id, []).append(gap.message)

    for claim_gap in claim_graph.gaps:
        checks_skipped.append({"check_id": claim_gap.check_id, "reason": claim_gap.message})

    count_claim = claims.get("hole-count-correct")
    if count_claim is not None and count_claim.check_id in skipped_by_check:
        checks_skipped.append(
            {"check_id": count_claim.check_id, "reason": skipped_by_check[count_claim.check_id][0]}
        )
    elif count_claim is not None:
        checks_run.append(count_claim.check_id)
        expected_count = int(count_claim.expected["count"])
        detected_count = len(evidence.holes)
        if detected_count != expected_count:
            findings.append(
                _make_finding(
                    "finding-hole-count",
                    count_claim.rule_id,
                    "hole_count_mismatch",
                    count_claim.severity,
                    f"Detected {detected_count} circular holes but expected {expected_count}.",
                    {
                        "expected_count": expected_count,
                        "detected_count": detected_count,
                        "detected_hole_centers": [hole.center_xy for hole in evidence.holes],
                    },
                    "Regenerate the illustration with the required number of holes.",
                )
            )

    ratio_claim = claims.get("hole-diameter-ratio-correct")
    if ratio_claim is not None and ratio_claim.check_id in skipped_by_check:
        checks_skipped.append(
            {"check_id": ratio_claim.check_id, "reason": skipped_by_check[ratio_claim.check_id][0]}
        )
    elif ratio_claim is not None:
        expected_ordered = ratio_claim.expected["ordered_holes"]
        paired = _paired_holes(expected_ordered, evidence.holes)
        if paired is None:
            checks_skipped.append(
                {
                    "check_id": ratio_claim.check_id,
                    "reason": (
                        f"Detected {len(evidence.holes)} holes but expected "
                        f"{len(expected_ordered)}; {PAIRING_NOTE}."
                    ),
                }
            )
        else:
            checks_run.append(ratio_claim.check_id)
            tolerance = float(ratio_claim.tolerance.get("diameter_ratio_tolerance", 0.12))
            reference = max(expected_ordered, key=lambda hole: float(hole["diameter"]))
            reference_declared = float(reference["diameter"])
            reference_measured = paired[reference["id"]].diameter_px
            for expected in expected_ordered:
                hole = paired[expected["id"]]
                declared_ratio = float(expected["diameter"]) / reference_declared
                measured_ratio = (
                    hole.diameter_px / reference_measured if reference_measured > 0 else 0.0
                )
                deviation = (
                    abs(measured_ratio - declared_ratio) / declared_ratio
                    if declared_ratio > 0
                    else 0.0
                )
                if deviation > tolerance:
                    finding_id = f"finding-hole-diameter-{expected['id']}"
                    findings.append(
                        _make_finding(
                            finding_id,
                            ratio_claim.rule_id,
                            "hole_diameter_ratio_violation",
                            ratio_claim.severity,
                            (
                                f"Hole '{expected['id']}' measures {hole.diameter_px:.1f} px, a "
                                f"{measured_ratio:.2f} ratio to the reference hole, but the spec "
                                f"declares a {declared_ratio:.2f} ratio "
                                f"(deviation {deviation:.2f}, tolerance {tolerance:.2f})."
                            ),
                            {
                                "hole_id": expected["id"],
                                "declared_diameter": float(expected["diameter"]),
                                "measured_diameter_px": hole.diameter_px,
                                "reference_hole_id": reference["id"],
                                "reference_measured_diameter_px": reference_measured,
                                "declared_ratio": round(declared_ratio, 3),
                                "measured_ratio": round(measured_ratio, 3),
                                "ratio_deviation": round(deviation, 3),
                                "diameter_ratio_tolerance": tolerance,
                                "center_xy": hole.center_xy,
                            },
                            "Redraw the hole at its declared relative diameter.",
                        )
                    )
                    overlay_annotations.append(
                        OverlayAnnotation(
                            finding_id=finding_id,
                            kind="bbox",
                            bbox=hole.bbox,
                            label=f"{expected['id']}: diameter",
                        )
                    )

    alignment_claim = claims.get("hole-alignment-correct")
    if alignment_claim is not None and alignment_claim.check_id in skipped_by_check:
        checks_skipped.append(
            {
                "check_id": alignment_claim.check_id,
                "reason": skipped_by_check[alignment_claim.check_id][0],
            }
        )
    elif alignment_claim is not None:
        expected_ids = alignment_claim.expected["ordered_hole_ids"]
        if len(evidence.holes) != len(expected_ids):
            checks_skipped.append(
                {
                    "check_id": alignment_claim.check_id,
                    "reason": (
                        f"Detected {len(evidence.holes)} holes but expected "
                        f"{len(expected_ids)}; {PAIRING_NOTE}."
                    ),
                }
            )
        else:
            checks_run.append(alignment_claim.check_id)
            alignment_tolerance = float(
                alignment_claim.tolerance.get("alignment_tolerance_px", 6.0)
            )
            spacing_tolerance = float(
                alignment_claim.tolerance.get("spacing_ratio_tolerance", 0.15)
            )
            centers = [hole.center_xy for hole in evidence.holes]
            if len(centers) >= 2:
                residuals, projections = _line_fit_residuals(centers)
                worst_index = max(range(len(residuals)), key=lambda index: residuals[index])
                if residuals[worst_index] > alignment_tolerance:
                    hole = evidence.holes[worst_index]
                    finding_id = f"finding-hole-alignment-{expected_ids[worst_index]}"
                    findings.append(
                        _make_finding(
                            finding_id,
                            alignment_claim.rule_id,
                            "hole_alignment_violation",
                            alignment_claim.severity,
                            (
                                f"Hole '{expected_ids[worst_index]}' at {hole.center_xy} sits "
                                f"{residuals[worst_index]:.1f} px off the best-fit line through "
                                f"the declared linear layout (tolerance "
                                f"{alignment_tolerance:.1f} px)."
                            ),
                            {
                                "hole_id": expected_ids[worst_index],
                                "center_xy": hole.center_xy,
                                "line_residuals_px": [round(value, 1) for value in residuals],
                                "alignment_tolerance_px": alignment_tolerance,
                            },
                            "Reposition the hole onto the declared linear layout.",
                        )
                    )
                    overlay_annotations.append(
                        OverlayAnnotation(
                            finding_id=finding_id,
                            kind="bbox",
                            bbox=hole.bbox,
                            label=f"{expected_ids[worst_index]}: alignment",
                        )
                    )
                elif len(centers) >= 3:
                    ordered = sorted(projections)
                    spacings = [
                        second - first for first, second in zip(ordered, ordered[1:], strict=False)
                    ]
                    mean_spacing = sum(spacings) / len(spacings)
                    if mean_spacing > 0:
                        worst_deviation = max(
                            abs(spacing - mean_spacing) / mean_spacing for spacing in spacings
                        )
                        if worst_deviation > spacing_tolerance:
                            finding_id = "finding-hole-spacing"
                            findings.append(
                                _make_finding(
                                    finding_id,
                                    alignment_claim.rule_id,
                                    "hole_alignment_violation",
                                    alignment_claim.severity,
                                    (
                                        "Hole spacing along the declared linear layout is "
                                        f"uneven: worst deviation {worst_deviation:.2f} of the "
                                        f"mean spacing {mean_spacing:.1f} px (tolerance "
                                        f"{spacing_tolerance:.2f})."
                                    ),
                                    {
                                        "spacings_px": [round(value, 1) for value in spacings],
                                        "mean_spacing_px": round(mean_spacing, 1),
                                        "worst_spacing_deviation": round(worst_deviation, 3),
                                        "spacing_ratio_tolerance": spacing_tolerance,
                                    },
                                    "Space the holes evenly along the declared layout line.",
                                )
                            )

    text_claim = claims.get("dimension-text-correct")
    if text_claim is not None and text_claim.check_id in skipped_by_check:
        checks_skipped.append(
            {"check_id": text_claim.check_id, "reason": skipped_by_check[text_claim.check_id][0]}
        )
    elif text_claim is not None:
        expected_ordered = text_claim.expected["ordered_holes"]
        paired = _paired_holes(expected_ordered, evidence.holes)
        if paired is None:
            checks_skipped.append(
                {
                    "check_id": text_claim.check_id,
                    "reason": (
                        f"Detected {len(evidence.holes)} holes but expected "
                        f"{len(expected_ordered)}; {PAIRING_NOTE}."
                    ),
                }
            )
        else:
            checks_run.append(text_claim.check_id)
            for expected in expected_ordered:
                hole = paired[expected["id"]]
                expected_text = expected.get("dimension_text")
                if expected_text is None:
                    continue
                if hole.label_text != expected_text:
                    finding_id = f"finding-dimension-text-{expected['id']}"
                    findings.append(
                        _make_finding(
                            finding_id,
                            text_claim.rule_id,
                            "dimension_text_mismatch",
                            text_claim.severity,
                            (
                                f"Hole '{expected['id']}' is labeled "
                                f"'{hole.label_text}' but the spec declares "
                                f"'{expected_text}'."
                            ),
                            {
                                "hole_id": expected["id"],
                                "expected_dimension_text": expected_text,
                                "decoded_dimension_text": hole.label_text,
                                "label_confidence": hole.label_confidence,
                                "center_xy": hole.center_xy,
                            },
                            "Correct the dimension callout text for this hole.",
                        )
                    )
                    overlay_annotations.append(
                        OverlayAnnotation(
                            finding_id=finding_id,
                            kind="bbox",
                            bbox=hole.bbox,
                            label=f"{expected['id']}: dimension text",
                        )
                    )

    findings = sorted(findings, key=lambda item: _severity_rank(item.severity), reverse=True)
    verdict = _overall_verdict(findings, checks_skipped)
    rule_confidence = _estimate_rule_confidence(checks_run, checks_skipped, findings)
    return VisualQaReport(
        image_id=evidence.image_id,
        spec_id=claim_graph.spec_id,
        verdict=verdict,
        findings=findings,
        checks_run=checks_run,
        checks_skipped=checks_skipped,
        confidence=rule_confidence,
        extraction_confidence=evidence.extraction_confidence,
        rule_confidence=rule_confidence,
        overlay_annotations=overlay_annotations,
    )
