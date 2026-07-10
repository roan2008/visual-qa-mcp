from __future__ import annotations

from pathlib import Path
from typing import Any

from .claim_graph import build_chart_claim_graph
from .contracts import ClaimCheck, ClaimGraph, EvidenceGraph, Finding, OverlayAnnotation, VisualQaReport


def _severity_rank(severity: str) -> int:
    return {"low": 1, "medium": 2, "high": 3, "critical": 4}[severity]


def _make_finding(
    finding_id: str,
    rule_id: str,
    finding_type: str,
    severity: str,
    message: str,
    evidence: dict[str, Any],
    recommendation: str,
) -> Finding:
    return Finding(
        id=finding_id,
        rule_id=rule_id,
        type=finding_type,
        severity=severity,
        message=message,
        evidence=evidence,
        recommendation=recommendation,
    )


def _overall_verdict(findings: list[Finding], skipped: list[dict[str, str]]) -> str:
    if skipped:
        return "needs_review"
    if any(finding.severity == "critical" for finding in findings):
        return "fail"
    if any(finding.severity == "high" for finding in findings):
        return "fail"
    if findings:
        return "warning"
    return "pass"


def _claim_by_check_id(claim_graph: ClaimGraph) -> dict[str, ClaimCheck]:
    return {claim.check_id: claim for claim in claim_graph.claims}


def _estimate_rule_confidence(
    checks_run: list[str],
    checks_skipped: list[dict[str, str]],
    findings: list[Finding],
) -> float:
    total_checks = len(checks_run) + len(checks_skipped)
    if total_checks == 0:
        return 0.0
    if not findings and not checks_skipped:
        return 1.0
    severity_weights = {"low": 0.05, "medium": 0.1, "high": 0.2, "critical": 0.3}
    skip_penalty = min(0.6, len(checks_skipped) / total_checks)
    finding_penalty = min(0.7, sum(severity_weights[finding.severity] for finding in findings))
    return round(max(0.0, 1.0 - skip_penalty - finding_penalty), 2)


def run_chart_claims(claim_graph: ClaimGraph, evidence: EvidenceGraph) -> VisualQaReport:
    claims = _claim_by_check_id(claim_graph)

    findings: list[Finding] = []
    checks_run: list[str] = []
    checks_skipped: list[dict[str, str]] = []
    overlay_annotations: list[OverlayAnnotation] = []

    gaps_by_code = {gap.code: gap for gap in evidence.gaps}
    skipped_by_check: dict[str, list[str]] = {}
    for gap in evidence.gaps:
        for check_id in gap.check_ids:
            skipped_by_check.setdefault(check_id, []).append(gap.message)

    for claim_gap in claim_graph.gaps:
        checks_skipped.append(
            {
                "check_id": claim_gap.check_id,
                "reason": claim_gap.message,
            }
        )

    bar_count_claim = claims.get("bar-count-matches")
    if bar_count_claim is not None:
        checks_run.append(bar_count_claim.check_id)
        expected_count = int(bar_count_claim.expected["count"])
        detected_count = len(evidence.bars)
        if detected_count != expected_count:
            finding = _make_finding(
                "finding-bar-count",
                bar_count_claim.rule_id,
                "bar_count_mismatch",
                bar_count_claim.severity,
                f"Detected {detected_count} bars but expected {expected_count}.",
                {"expected_count": expected_count, "detected_count": detected_count},
                "Regenerate the chart with the required number of bars.",
            )
            findings.append(finding)

    scale_readable_claim = claims.get("axis-scale-readable")
    if scale_readable_claim is not None:
        readable_codes = {"axis_scale_unreadable", "insufficient_tick_evidence", "optional_ocr_unavailable", "invalid_tick_geometry"}
        reasons = [gaps_by_code[code].message for code in readable_codes if code in gaps_by_code]
        if reasons:
            checks_skipped.append({"check_id": scale_readable_claim.check_id, "reason": reasons[0]})
        else:
            checks_run.append(scale_readable_claim.check_id)

    monotonic_claim = claims.get("axis-scale-monotonic")
    if monotonic_claim is not None:
        monotonic_codes = {"non_monotonic_tick_values", "inconsistent_tick_step"}
        reasons = [gaps_by_code[code].message for code in monotonic_codes if code in gaps_by_code]
        if reasons:
            checks_skipped.append({"check_id": monotonic_claim.check_id, "reason": reasons[0]})
        else:
            checks_run.append(monotonic_claim.check_id)

    zero_line_claim = claims.get("axis-zero-line-resolved")
    if zero_line_claim is not None:
        if "axis_zero_line_unresolved" in gaps_by_code:
            checks_skipped.append({"check_id": zero_line_claim.check_id, "reason": gaps_by_code["axis_zero_line_unresolved"].message})
        else:
            checks_run.append(zero_line_claim.check_id)

    chart_value_claim = claims.get("bar-values-match-data")
    if chart_value_claim is not None and chart_value_claim.check_id in skipped_by_check:
        checks_skipped.append({"check_id": chart_value_claim.check_id, "reason": skipped_by_check[chart_value_claim.check_id][0]})
    elif chart_value_claim is not None:
        checks_run.append(chart_value_claim.check_id)
        tolerance = float(chart_value_claim.tolerance.get("relative_tolerance", 0.05))
        expected_axis_min = chart_value_claim.expected.get("expected_min_value")
        expected_axis_max = chart_value_claim.expected.get("expected_max_value")
        mapping = evidence.y_axis.mapping
        if mapping is not None and expected_axis_min is not None and expected_axis_max is not None:
            detected_bounds = (float(mapping.min_value), float(mapping.max_value))
            expected_bounds = (float(expected_axis_min), float(expected_axis_max))
            if any(abs(detected - expected) > 0.01 for detected, expected in zip(detected_bounds, expected_bounds, strict=True)):
                findings.append(
                    _make_finding(
                        "finding-axis-range",
                        chart_value_claim.rule_id,
                        "chart_value_mismatch",
                        chart_value_claim.severity,
                        (
                            f"Displayed axis range {detected_bounds[0]:.2f}..{detected_bounds[1]:.2f} "
                            f"does not match expected {expected_bounds[0]:.2f}..{expected_bounds[1]:.2f}."
                        ),
                        {
                            "expected_min_value": expected_bounds[0],
                            "expected_max_value": expected_bounds[1],
                            "detected_min_value": detected_bounds[0],
                            "detected_max_value": detected_bounds[1],
                            "value_source": "axis_mapping",
                        },
                        "Correct the displayed tick range so it matches the source axis specification.",
                    )
                )
        expected_by_label = {
            str(label): float(value)
            for label, value in chart_value_claim.expected.get("values_by_category", {}).items()
        }
        for bar in evidence.bars:
            if bar.category is None or bar.value is None:
                continue
            expected_value = expected_by_label.get(bar.category)
            if expected_value is None:
                finding_id = f"finding-unexpected-category-{bar.bar_id}"
                findings.append(
                    _make_finding(
                        finding_id,
                        chart_value_claim.rule_id,
                        "unexpected_category",
                        "high",
                        f"Detected bar category '{bar.category}' is not part of the source data.",
                        {"bar_id": bar.bar_id, "category": bar.category},
                        "Correct the x-axis label so each bar maps to a known source-data category.",
                    )
                )
                overlay_annotations.append(
                    OverlayAnnotation(
                        finding_id=finding_id,
                        kind="bbox",
                        bbox=bar.bbox,
                        label="Unexpected category",
                    )
                )
                continue
            delta = abs(bar.value - expected_value)
            relative = delta / max(abs(expected_value), 1.0)
            if relative > tolerance:
                finding_id = f"finding-bar-value-{bar.bar_id}"
                findings.append(
                    _make_finding(
                        finding_id,
                        chart_value_claim.rule_id,
                        "chart_value_mismatch",
                        chart_value_claim.severity,
                        f"Bar '{bar.category}' value {bar.value:.2f} does not match expected {expected_value:.2f}.",
                        {
                            "bar_id": bar.bar_id,
                            "category": bar.category,
                            "expected_value": expected_value,
                            "detected_value": bar.value,
                            "relative_tolerance": tolerance,
                            "value_source": bar.value_source,
                        },
                        "Update the bar height so it matches the source data within tolerance.",
                    )
                )
                overlay_annotations.append(
                    OverlayAnnotation(
                        finding_id=finding_id,
                        kind="bbox",
                        bbox=bar.bbox,
                        label=f"{bar.category}: value mismatch",
                    )
                )

    label_claim = claims.get("axis-label-present")
    if label_claim is not None and label_claim.check_id in skipped_by_check:
        checks_skipped.append({"check_id": label_claim.check_id, "reason": skipped_by_check[label_claim.check_id][0]})
    elif label_claim is not None:
        checks_run.append(label_claim.check_id)
        expected_y_label = label_claim.expected.get("label_text")
        if evidence.y_axis.label_text != expected_y_label:
            findings.append(
                _make_finding(
                    "finding-axis-label",
                    label_claim.rule_id,
                    "label_missing_or_wrong",
                    label_claim.severity,
                    "The y-axis label is missing or does not match the expected text.",
                    {
                        "expected_label": expected_y_label,
                        "detected_label": evidence.y_axis.label_text,
                    },
                    "Restore the required y-axis label text.",
                )
            )
            overlay_annotations.append(
                OverlayAnnotation(
                    finding_id="finding-axis-label",
                    kind="bbox",
                    bbox=evidence.y_axis.label_bbox,
                    label="Axis label issue",
                )
            )

    unit_claim = claims.get("axis-unit-present")
    if unit_claim is not None and unit_claim.check_id in skipped_by_check:
        checks_skipped.append({"check_id": unit_claim.check_id, "reason": skipped_by_check[unit_claim.check_id][0]})
    elif unit_claim is not None:
        checks_run.append(unit_claim.check_id)
        expected_unit = unit_claim.expected.get("unit_text")
        if evidence.y_axis.unit_text != expected_unit:
            findings.append(
                _make_finding(
                    "finding-axis-unit",
                    unit_claim.rule_id,
                    "unit_mismatch",
                    unit_claim.severity,
                    "The y-axis unit is missing or incorrect.",
                    {"expected_unit": expected_unit, "detected_unit": evidence.y_axis.unit_text},
                    "Restore the expected y-axis unit in the label.",
                )
            )
            overlay_annotations.append(
                OverlayAnnotation(
                    finding_id="finding-axis-unit",
                    kind="bbox",
                    bbox=evidence.y_axis.label_bbox,
                    label="Axis unit issue",
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


def run_chart_rules(spec_path: Path, evidence: EvidenceGraph) -> VisualQaReport:
    claim_graph = build_chart_claim_graph(spec_path)
    return run_chart_claims(claim_graph, evidence)
