from __future__ import annotations

import math
from typing import Any

from .chart_rules import (
    _estimate_rule_confidence,
    _make_finding,
    _overall_verdict,
    _severity_rank,
)
from .contracts import (
    ArrowEvidenceGraph,
    ClaimGraph,
    ExtractedArrow,
    Finding,
    OverlayAnnotation,
    VisualQaReport,
)


def _color_distance(first_rgb: list[int], second_rgb: list[int]) -> float:
    return math.sqrt(
        sum((float(a) - float(b)) ** 2 for a, b in zip(first_rgb, second_rgb, strict=True))
    )


def _angle_difference(first_degrees: float, second_degrees: float) -> float:
    difference = abs(first_degrees - second_degrees) % 360.0
    return min(difference, 360.0 - difference)


def _match_arrows_by_color(
    expected_by_id: dict[str, dict[str, Any]],
    detected: list[ExtractedArrow],
    color_match_distance: float,
) -> tuple[dict[str, ExtractedArrow], list[ExtractedArrow]]:
    """Match detected arrows to expected arrow ids.

    Labels are decoded independently of color and take priority when a detected
    arrow's label exactly matches an expected label: this lets two arrows with
    colliding colors still be identified correctly. Remaining ids fall back to
    greedy nearest-color matching, preserving prior behavior when no labels are
    declared or decoded.
    """
    matched: dict[str, ExtractedArrow] = {}
    remaining = list(detected)

    label_pairs: list[tuple[str, ExtractedArrow]] = [
        (arrow_id, arrow)
        for arrow_id, expected in expected_by_id.items()
        for arrow in remaining
        if expected.get("label_text") is not None and arrow.label_text == expected["label_text"]
    ]
    ambiguous_ids = {
        arrow_id
        for arrow_id in {pair[0] for pair in label_pairs}
        if sum(1 for pair_id, _ in label_pairs if pair_id == arrow_id) > 1
    }
    for arrow_id, arrow in label_pairs:
        if arrow_id in ambiguous_ids or arrow_id in matched or arrow not in remaining:
            continue
        matched[arrow_id] = arrow
        remaining.remove(arrow)

    pairs: list[tuple[float, str, ExtractedArrow]] = []
    for arrow_id, expected in expected_by_id.items():
        if arrow_id in matched:
            continue
        for arrow in remaining:
            distance = _color_distance(expected["rgb"], arrow.rgb)
            if distance <= color_match_distance:
                pairs.append((distance, arrow_id, arrow))
    for _, arrow_id, arrow in sorted(pairs, key=lambda item: item[0]):
        if arrow_id in matched or arrow not in remaining:
            continue
        matched[arrow_id] = arrow
        remaining.remove(arrow)
    return matched, remaining


def _point_near_bbox(point_xy: list[int], bbox: list[int], tolerance_px: float) -> bool:
    x, y = float(point_xy[0]), float(point_xy[1])
    left, top, right, bottom = (float(value) for value in bbox)
    dx = max(left - x, 0.0, x - right)
    dy = max(top - y, 0.0, y - bottom)
    return math.hypot(dx, dy) <= tolerance_px


def run_arrow_claims(claim_graph: ClaimGraph, evidence: ArrowEvidenceGraph) -> VisualQaReport:
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

    object_region = next(
        (region for region in evidence.regions if region.region_id == "object"), None
    )

    count_claim = claims.get("arrow-count-matches")
    if count_claim is not None and count_claim.check_id in skipped_by_check:
        checks_skipped.append(
            {"check_id": count_claim.check_id, "reason": skipped_by_check[count_claim.check_id][0]}
        )
    elif count_claim is not None:
        checks_run.append(count_claim.check_id)
        expected_count = int(count_claim.expected["count"])
        detected_count = len(evidence.arrows)
        if detected_count != expected_count:
            findings.append(
                _make_finding(
                    "finding-arrow-count",
                    count_claim.rule_id,
                    "arrow_count_mismatch",
                    count_claim.severity,
                    f"Detected {detected_count} arrows but expected {expected_count}.",
                    {"expected_count": expected_count, "detected_count": detected_count},
                    "Regenerate the diagram with the required set of force arrows.",
                )
            )

    presence_claim = claims.get("required-arrows-present")
    matched: dict[str, ExtractedArrow] = {}
    if presence_claim is not None and presence_claim.check_id in skipped_by_check:
        checks_skipped.append(
            {
                "check_id": presence_claim.check_id,
                "reason": skipped_by_check[presence_claim.check_id][0],
            }
        )
    elif presence_claim is not None:
        checks_run.append(presence_claim.check_id)
        expected_by_id = presence_claim.expected["arrows_by_id"]
        color_match_distance = float(presence_claim.tolerance.get("color_match_distance", 60.0))
        matched, unmatched = _match_arrows_by_color(
            expected_by_id, evidence.arrows, color_match_distance
        )
        for arrow_id, expected in expected_by_id.items():
            if arrow_id in matched:
                continue
            findings.append(
                _make_finding(
                    f"finding-arrow-missing-{arrow_id}",
                    presence_claim.rule_id,
                    "arrow_missing",
                    presence_claim.severity,
                    f"Required arrow '{expected.get('name') or arrow_id}' was not detected.",
                    {"arrow_id": arrow_id, "expected_rgb": expected["rgb"]},
                    "Add the missing force arrow with its expected color and direction.",
                )
            )
        for arrow in unmatched:
            finding_id = f"finding-unexpected-arrow-{arrow.arrow_id}"
            findings.append(
                _make_finding(
                    finding_id,
                    presence_claim.rule_id,
                    "unexpected_arrow",
                    "high",
                    f"Detected arrow '{arrow.arrow_id}' does not match any expected arrow color.",
                    {"arrow_id": arrow.arrow_id, "detected_rgb": arrow.rgb, "bbox": arrow.bbox},
                    "Remove the extra arrow or map it to a declared force in the spec.",
                )
            )
            overlay_annotations.append(
                OverlayAnnotation(
                    finding_id=finding_id,
                    kind="bbox",
                    bbox=arrow.bbox,
                    label="Unexpected arrow",
                )
            )

    direction_claim = claims.get("arrow-directions-correct")
    if direction_claim is not None and direction_claim.check_id in skipped_by_check:
        checks_skipped.append(
            {
                "check_id": direction_claim.check_id,
                "reason": skipped_by_check[direction_claim.check_id][0],
            }
        )
    elif direction_claim is not None:
        checks_run.append(direction_claim.check_id)
        expected_by_id = direction_claim.expected["directions_by_id"]
        color_match_distance = float(direction_claim.tolerance.get("color_match_distance", 60.0))
        angle_tolerance = float(direction_claim.tolerance.get("angle_tolerance_degrees", 15.0))
        if not matched:
            matched, _ = _match_arrows_by_color(
                expected_by_id, evidence.arrows, color_match_distance
            )
        for arrow_id, expected in expected_by_id.items():
            arrow = matched.get(arrow_id)
            if arrow is None:
                continue
            expected_angle = float(expected["direction_degrees"])
            difference = _angle_difference(arrow.angle_degrees, expected_angle)
            if difference > angle_tolerance:
                finding_id = f"finding-arrow-direction-{arrow_id}"
                findings.append(
                    _make_finding(
                        finding_id,
                        direction_claim.rule_id,
                        "arrow_direction_wrong",
                        direction_claim.severity,
                        (
                            f"Arrow '{arrow_id}' points at {arrow.angle_degrees:.1f} deg but "
                            f"expected {expected_angle:.1f} deg (difference {difference:.1f} deg)."
                        ),
                        {
                            "arrow_id": arrow_id,
                            "expected_direction_degrees": expected_angle,
                            "detected_direction_degrees": arrow.angle_degrees,
                            "angle_difference_degrees": round(difference, 1),
                            "angle_tolerance_degrees": angle_tolerance,
                            "tail_xy": arrow.tail_xy,
                            "head_xy": arrow.head_xy,
                        },
                        "Redraw the arrow so it points in the physically correct direction.",
                    )
                )
                overlay_annotations.append(
                    OverlayAnnotation(
                        finding_id=finding_id,
                        kind="bbox",
                        bbox=arrow.bbox,
                        label=f"{arrow_id}: direction",
                    )
                )

    anchor_claim = claims.get("arrow-anchors-object")
    if anchor_claim is not None and anchor_claim.check_id in skipped_by_check:
        checks_skipped.append(
            {
                "check_id": anchor_claim.check_id,
                "reason": skipped_by_check[anchor_claim.check_id][0],
            }
        )
    elif anchor_claim is not None:
        checks_run.append(anchor_claim.check_id)
        anchor_tolerance = float(anchor_claim.tolerance.get("anchor_tolerance_px", 14.0))
        color_match_distance = float(anchor_claim.tolerance.get("color_match_distance", 60.0))
        if not matched:
            matched, _ = _match_arrows_by_color(
                anchor_claim.expected["arrows_by_id"], evidence.arrows, color_match_distance
            )
        anchored_ids = anchor_claim.expected.get("anchored_arrow_ids", [])
        for arrow_id in anchored_ids:
            arrow = matched.get(arrow_id)
            if arrow is None or object_region is None:
                continue
            if not _point_near_bbox(arrow.tail_xy, object_region.bbox, anchor_tolerance):
                finding_id = f"finding-arrow-anchor-{arrow_id}"
                findings.append(
                    _make_finding(
                        finding_id,
                        anchor_claim.rule_id,
                        "arrow_anchor_detached",
                        anchor_claim.severity,
                        (
                            f"Arrow '{arrow_id}' tail at {arrow.tail_xy} is not attached to the "
                            f"object region {object_region.bbox} within {anchor_tolerance:.0f} px."
                        ),
                        {
                            "arrow_id": arrow_id,
                            "tail_xy": arrow.tail_xy,
                            "object_bbox": object_region.bbox,
                            "anchor_tolerance_px": anchor_tolerance,
                        },
                        "Attach the force arrow to the object it acts on.",
                    )
                )
                overlay_annotations.append(
                    OverlayAnnotation(
                        finding_id=finding_id,
                        kind="bbox",
                        bbox=arrow.bbox,
                        label=f"{arrow_id}: detached",
                    )
                )

    balance_claim = claims.get("force-balance-correct")
    if balance_claim is not None and balance_claim.check_id in skipped_by_check:
        checks_skipped.append(
            {
                "check_id": balance_claim.check_id,
                "reason": skipped_by_check[balance_claim.check_id][0],
            }
        )
    elif balance_claim is not None:
        expected_by_id = balance_claim.expected["arrows_by_id"]
        color_match_distance = float(balance_claim.tolerance.get("color_match_distance", 60.0))
        ratio_tolerance = float(balance_claim.tolerance.get("resultant_ratio_tolerance", 0.15))
        if not matched:
            matched, _ = _match_arrows_by_color(
                expected_by_id, evidence.arrows, color_match_distance
            )
        unmatched_ids = sorted(
            arrow_id for arrow_id in expected_by_id if arrow_id not in matched
        )
        if unmatched_ids:
            # Never sum a partial force set: a missing or unidentified arrow makes
            # any resultant computation unsupported evidence.
            checks_skipped.append(
                {
                    "check_id": balance_claim.check_id,
                    "reason": (
                        "Expected arrow(s) "
                        + ", ".join(f"'{arrow_id}'" for arrow_id in unmatched_ids)
                        + " could not be confidently matched, so the force vector sum "
                        "is not supported by evidence."
                    ),
                }
            )
        else:
            checks_run.append(balance_claim.check_id)
            arrow_vectors = {
                arrow_id: {
                    "length_px": matched[arrow_id].length_px,
                    "angle_degrees": matched[arrow_id].angle_degrees,
                }
                for arrow_id in expected_by_id
            }
            resultant_x = sum(
                vector["length_px"] * math.cos(math.radians(vector["angle_degrees"]))
                for vector in arrow_vectors.values()
            )
            resultant_y = sum(
                vector["length_px"] * math.sin(math.radians(vector["angle_degrees"]))
                for vector in arrow_vectors.values()
            )
            resultant_magnitude = math.hypot(resultant_x, resultant_y)
            max_length = max(vector["length_px"] for vector in arrow_vectors.values())
            resultant_ratio = resultant_magnitude / max_length if max_length > 0 else 0.0
            if resultant_ratio > ratio_tolerance:
                finding_id = "finding-force-balance"
                findings.append(
                    _make_finding(
                        finding_id,
                        balance_claim.rule_id,
                        "force_balance_violation",
                        balance_claim.severity,
                        (
                            "Declared equilibrium scenario is violated: drawn force vectors "
                            f"sum to {resultant_magnitude:.1f} px "
                            f"({resultant_ratio:.2f} of the longest arrow, tolerance "
                            f"{ratio_tolerance:.2f})."
                        ),
                        {
                            "scenario_type": balance_claim.expected.get("scenario_type"),
                            "arrow_vectors_px": {
                                arrow_id: {
                                    "length_px": round(vector["length_px"], 1),
                                    "angle_degrees": round(vector["angle_degrees"], 1),
                                }
                                for arrow_id, vector in arrow_vectors.items()
                            },
                            "resultant_vector_px": [
                                round(resultant_x, 1),
                                round(resultant_y, 1),
                            ],
                            "resultant_magnitude_px": round(resultant_magnitude, 1),
                            "max_arrow_length_px": round(max_length, 1),
                            "resultant_ratio": round(resultant_ratio, 3),
                            "resultant_ratio_tolerance": ratio_tolerance,
                        },
                        "Redraw the force arrows so their vector sum is zero for the declared equilibrium scenario.",
                    )
                )
                if object_region is not None:
                    overlay_annotations.append(
                        OverlayAnnotation(
                            finding_id=finding_id,
                            kind="bbox",
                            bbox=object_region.bbox,
                            label="Force balance violated",
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
