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
    ClaimGraph,
    CoordinateEvidenceGraph,
    ExtractedPoint,
    Finding,
    OverlayAnnotation,
    VisualQaReport,
)

DEFAULT_POSITION_TOLERANCE_FRACTION = 0.03


def _color_distance(first_rgb: list[int], second_rgb: list[int]) -> float:
    return math.sqrt(
        sum((float(a) - float(b)) ** 2 for a, b in zip(first_rgb, second_rgb, strict=True))
    )


def _match_points_by_color(
    expected_by_id: dict[str, dict[str, Any]],
    detected: list[ExtractedPoint],
    color_match_distance: float,
) -> tuple[dict[str, ExtractedPoint], list[ExtractedPoint]]:
    """Match detected points to expected point ids.

    Labels are decoded independently of color and take priority when a detected
    point's label exactly matches an expected label: this lets two points with
    colliding colors still be identified correctly. Remaining ids fall back to
    greedy nearest-color matching, mirroring arrow-v1's `_match_arrows_by_color`.
    """
    matched: dict[str, ExtractedPoint] = {}
    remaining = list(detected)

    label_pairs: list[tuple[str, ExtractedPoint]] = [
        (point_id, point)
        for point_id, expected in expected_by_id.items()
        for point in remaining
        if expected.get("label_text") is not None and point.label_text == expected["label_text"]
    ]
    ambiguous_ids = {
        point_id
        for point_id in {pair[0] for pair in label_pairs}
        if sum(1 for pair_id, _ in label_pairs if pair_id == point_id) > 1
    }
    for point_id, point in label_pairs:
        if point_id in ambiguous_ids or point_id in matched or point not in remaining:
            continue
        matched[point_id] = point
        remaining.remove(point)

    pairs: list[tuple[float, str, ExtractedPoint]] = []
    for point_id, expected in expected_by_id.items():
        if point_id in matched:
            continue
        for point in remaining:
            distance = _color_distance(expected["rgb"], point.rgb)
            if distance <= color_match_distance:
                pairs.append((distance, point_id, point))
    for _, point_id, point in sorted(pairs, key=lambda item: item[0]):
        if point_id in matched or point not in remaining:
            continue
        matched[point_id] = point
        remaining.remove(point)
    return matched, remaining


def run_coordinate_claims(
    claim_graph: ClaimGraph, evidence: CoordinateEvidenceGraph
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

    matched: dict[str, ExtractedPoint] = {}

    count_claim = claims.get("point-count-matches")
    if count_claim is not None and count_claim.check_id in skipped_by_check:
        checks_skipped.append(
            {"check_id": count_claim.check_id, "reason": skipped_by_check[count_claim.check_id][0]}
        )
    elif count_claim is not None:
        checks_run.append(count_claim.check_id)
        expected_count = int(count_claim.expected["count"])
        detected_count = len(evidence.points)
        if detected_count != expected_count:
            findings.append(
                _make_finding(
                    "finding-point-count",
                    count_claim.rule_id,
                    "point_count_mismatch",
                    count_claim.severity,
                    f"Detected {detected_count} points but expected {expected_count}.",
                    {"expected_count": expected_count, "detected_count": detected_count},
                    "Regenerate the plot with the required number of points.",
                )
            )

    presence_claim = claims.get("required-points-present")
    if presence_claim is not None and presence_claim.check_id in skipped_by_check:
        checks_skipped.append(
            {
                "check_id": presence_claim.check_id,
                "reason": skipped_by_check[presence_claim.check_id][0],
            }
        )
    elif presence_claim is not None:
        checks_run.append(presence_claim.check_id)
        expected_by_id = presence_claim.expected["points_by_id"]
        color_match_distance = float(presence_claim.tolerance.get("color_match_distance", 60.0))
        matched, unmatched = _match_points_by_color(
            expected_by_id, evidence.points, color_match_distance
        )
        for point_id, expected in expected_by_id.items():
            if point_id in matched:
                continue
            findings.append(
                _make_finding(
                    f"finding-point-missing-{point_id}",
                    presence_claim.rule_id,
                    "missing_point",
                    presence_claim.severity,
                    f"Required point '{expected.get('name') or point_id}' was not detected.",
                    {"point_id": point_id, "expected_rgb": expected["rgb"]},
                    "Add the missing point with its expected color and position.",
                )
            )
        for point in unmatched:
            finding_id = f"finding-unexpected-point-{point.point_id}"
            findings.append(
                _make_finding(
                    finding_id,
                    presence_claim.rule_id,
                    "extra_point",
                    "high",
                    f"Detected point '{point.point_id}' does not match any expected point color.",
                    {"point_id": point.point_id, "detected_rgb": point.rgb, "bbox": point.bbox},
                    "Remove the extra point or map it to a declared point in the spec.",
                )
            )
            overlay_annotations.append(
                OverlayAnnotation(
                    finding_id=finding_id,
                    kind="bbox",
                    bbox=point.bbox,
                    label="Unexpected point",
                )
            )

    position_claim = claims.get("point-positions-correct")
    if position_claim is not None and position_claim.check_id in skipped_by_check:
        checks_skipped.append(
            {
                "check_id": position_claim.check_id,
                "reason": skipped_by_check[position_claim.check_id][0],
            }
        )
    elif position_claim is not None:
        checks_run.append(position_claim.check_id)
        expected_by_id = position_claim.expected["points_by_id"]
        color_match_distance = float(position_claim.tolerance.get("color_match_distance", 60.0))
        tolerance_x = float(position_claim.tolerance["position_tolerance_x"])
        tolerance_y = float(position_claim.tolerance["position_tolerance_y"])
        if not matched:
            matched, _ = _match_points_by_color(expected_by_id, evidence.points, color_match_distance)
        for point_id, expected in expected_by_id.items():
            point = matched.get(point_id)
            if point is None or point.data_xy is None:
                continue
            delta_x = abs(point.data_xy[0] - float(expected["x"]))
            delta_y = abs(point.data_xy[1] - float(expected["y"]))
            if delta_x > tolerance_x or delta_y > tolerance_y:
                finding_id = f"finding-point-position-{point_id}"
                findings.append(
                    _make_finding(
                        finding_id,
                        position_claim.rule_id,
                        "point_position_wrong",
                        position_claim.severity,
                        (
                            f"Point '{point_id}' measures data position "
                            f"({point.data_xy[0]:.2f}, {point.data_xy[1]:.2f}) but the spec "
                            f"declares ({expected['x']:.2f}, {expected['y']:.2f})."
                        ),
                        {
                            "point_id": point_id,
                            "detected_point_id": point.point_id,
                            "expected_xy": [float(expected["x"]), float(expected["y"])],
                            "detected_data_xy": point.data_xy,
                            "detected_pixel_xy": point.pixel_xy,
                            "position_tolerance_x": tolerance_x,
                            "position_tolerance_y": tolerance_y,
                        },
                        "Redraw the point at its declared data-space position.",
                    )
                )
                overlay_annotations.append(
                    OverlayAnnotation(
                        finding_id=finding_id,
                        kind="bbox",
                        bbox=point.bbox,
                        label=f"{point_id}: position",
                    )
                )

    polyline_claim = claims.get("polyline-connections-correct")
    if polyline_claim is not None and polyline_claim.check_id in skipped_by_check:
        checks_skipped.append(
            {
                "check_id": polyline_claim.check_id,
                "reason": skipped_by_check[polyline_claim.check_id][0],
            }
        )
    elif polyline_claim is not None:
        expected_by_id = polyline_claim.expected["points_by_id"]
        color_match_distance = float(polyline_claim.tolerance.get("color_match_distance", 60.0))
        if not matched:
            matched, _ = _match_points_by_color(expected_by_id, evidence.points, color_match_distance)
        checks_run.append(polyline_claim.check_id)
        detected_edges = {
            frozenset((edge.from_point_id, edge.to_point_id)) for edge in evidence.polyline_edges
        }
        for series in polyline_claim.expected["series"]:
            series_id = series["series_id"]
            expected_order = series["ordered_point_ids"]
            for first_id, second_id in zip(expected_order, expected_order[1:]):
                first_point = matched.get(first_id)
                second_point = matched.get(second_id)
                # An unresolved endpoint is already reported by the presence
                # check (or an evidence gap); silently skip judging this one
                # edge rather than discarding the whole polyline check.
                if first_point is None or second_point is None:
                    continue
                if frozenset((first_point.point_id, second_point.point_id)) not in detected_edges:
                    finding_id = f"finding-polyline-connection-{series_id}-{first_id}-{second_id}"
                    findings.append(
                        _make_finding(
                            finding_id,
                            polyline_claim.rule_id,
                            "polyline_connection_wrong",
                            polyline_claim.severity,
                            (
                                f"The declared polyline connection between '{first_id}' and "
                                f"'{second_id}' in series '{series_id}' was not found in the "
                                "rendered line evidence."
                            ),
                            {
                                "series_id": series_id,
                                "expected_edge": [first_id, second_id],
                                "detected_edges": sorted(
                                    tuple(sorted(edge)) for edge in detected_edges
                                ),
                            },
                            "Redraw the polyline so it connects the declared points in order.",
                        )
                    )
                    overlay_annotations.append(
                        OverlayAnnotation(
                            finding_id=finding_id,
                            kind="bbox",
                            bbox=first_point.bbox,
                            label=f"{first_id}-{second_id}: polyline ({series_id})",
                        )
                    )

    axis_claim = claims.get("axis-scale-correct")
    if axis_claim is not None and axis_claim.check_id in skipped_by_check:
        checks_skipped.append(
            {"check_id": axis_claim.check_id, "reason": skipped_by_check[axis_claim.check_id][0]}
        )
    elif axis_claim is not None:
        checks_run.append(axis_claim.check_id)
        tolerance = float(axis_claim.tolerance.get("axis_value_tolerance", 0.5))
        for orientation, axis_evidence in (("x", evidence.x_axis), ("y", evidence.y_axis)):
            expected_axis = axis_claim.expected.get(f"{orientation}_axis")
            if expected_axis is None or axis_evidence.mapping is None:
                continue
            expected_min = float(expected_axis["expected_min"])
            expected_max = float(expected_axis["expected_max"])
            detected_min = float(axis_evidence.mapping.min_value)
            detected_max = float(axis_evidence.mapping.max_value)
            if abs(detected_min - expected_min) > tolerance or abs(detected_max - expected_max) > tolerance:
                finding_id = f"finding-axis-scale-{orientation}"
                findings.append(
                    _make_finding(
                        finding_id,
                        axis_claim.rule_id,
                        "axis_scale_misread",
                        axis_claim.severity,
                        (
                            f"The {orientation}-axis displays range "
                            f"{detected_min:.2f}..{detected_max:.2f} but the spec declares "
                            f"{expected_min:.2f}..{expected_max:.2f}."
                        ),
                        {
                            "orientation": orientation,
                            "expected_min": expected_min,
                            "expected_max": expected_max,
                            "detected_min": detected_min,
                            "detected_max": detected_max,
                            "axis_value_tolerance": tolerance,
                        },
                        "Correct the displayed axis tick range so it matches the declared spec.",
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
