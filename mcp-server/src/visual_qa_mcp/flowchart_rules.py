from __future__ import annotations

import math
from typing import Any

from .chart_rules import _estimate_rule_confidence, _make_finding, _overall_verdict, _severity_rank
from .contracts import ClaimGraph, ExtractedNode, Finding, FlowchartEvidenceGraph, OverlayAnnotation, VisualQaReport


def _color_distance(first_rgb: list[int], second_rgb: list[int]) -> float:
    return math.sqrt(
        sum((float(a) - float(b)) ** 2 for a, b in zip(first_rgb, second_rgb, strict=True))
    )


def _match_nodes_by_color(
    expected_by_id: dict[str, dict[str, Any]],
    detected: list[ExtractedNode],
    color_match_distance: float,
) -> tuple[dict[str, ExtractedNode], list[ExtractedNode]]:
    matched: dict[str, ExtractedNode] = {}
    remaining = list(detected)
    pairs: list[tuple[float, str, ExtractedNode]] = []
    for node_id, expected in expected_by_id.items():
        for node in remaining:
            distance = _color_distance(expected["rgb"], node.rgb)
            if distance <= color_match_distance:
                pairs.append((distance, node_id, node))
    for _, node_id, node in sorted(pairs, key=lambda item: item[0]):
        if node_id in matched or node not in remaining:
            continue
        matched[node_id] = node
        remaining.remove(node)
    return matched, remaining


def run_flowchart_claims(claim_graph: ClaimGraph, evidence: FlowchartEvidenceGraph) -> VisualQaReport:
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

    matched: dict[str, ExtractedNode] = {}

    count_claim = claims.get("node-count-matches")
    if count_claim is not None and count_claim.check_id in skipped_by_check:
        checks_skipped.append(
            {"check_id": count_claim.check_id, "reason": skipped_by_check[count_claim.check_id][0]}
        )
    elif count_claim is not None:
        checks_run.append(count_claim.check_id)
        expected_count = int(count_claim.expected["count"])
        detected_count = len(evidence.nodes)
        if detected_count != expected_count:
            findings.append(
                _make_finding(
                    "finding-node-count",
                    count_claim.rule_id,
                    "node_count_mismatch",
                    count_claim.severity,
                    f"Detected {detected_count} nodes but expected {expected_count}.",
                    {"expected_count": expected_count, "detected_count": detected_count},
                    "Regenerate the diagram with the required number of nodes.",
                )
            )

    presence_claim = claims.get("required-nodes-present")
    if presence_claim is not None and presence_claim.check_id in skipped_by_check:
        checks_skipped.append(
            {"check_id": presence_claim.check_id, "reason": skipped_by_check[presence_claim.check_id][0]}
        )
    elif presence_claim is not None:
        checks_run.append(presence_claim.check_id)
        expected_by_id = presence_claim.expected["nodes_by_id"]
        color_match_distance = float(presence_claim.tolerance.get("color_match_distance", 60.0))
        matched, unmatched = _match_nodes_by_color(expected_by_id, evidence.nodes, color_match_distance)
        for node_id, expected in expected_by_id.items():
            if node_id in matched:
                continue
            findings.append(
                _make_finding(
                    f"finding-node-missing-{node_id}",
                    presence_claim.rule_id,
                    "missing_node",
                    presence_claim.severity,
                    f"Required node '{expected.get('name') or node_id}' was not detected.",
                    {"node_id": node_id, "expected_rgb": expected["rgb"]},
                    "Add the missing node with its expected color and shape.",
                )
            )
        for node in unmatched:
            finding_id = f"finding-unexpected-node-{node.node_id}"
            findings.append(
                _make_finding(
                    finding_id,
                    presence_claim.rule_id,
                    "extra_node",
                    "high",
                    f"Detected node '{node.node_id}' does not match any expected node color.",
                    {"node_id": node.node_id, "detected_rgb": node.rgb, "bbox": node.bbox},
                    "Remove the extra node or map it to a declared node in the spec.",
                )
            )
            overlay_annotations.append(
                OverlayAnnotation(
                    finding_id=finding_id, kind="bbox", bbox=node.bbox, label="Unexpected node"
                )
            )

    shape_claim = claims.get("node-shape-correct")
    if shape_claim is not None and shape_claim.check_id in skipped_by_check:
        checks_skipped.append(
            {"check_id": shape_claim.check_id, "reason": skipped_by_check[shape_claim.check_id][0]}
        )
    elif shape_claim is not None:
        checks_run.append(shape_claim.check_id)
        expected_by_id = shape_claim.expected["nodes_by_id"]
        color_match_distance = float(shape_claim.tolerance.get("color_match_distance", 60.0))
        if not matched:
            matched, _ = _match_nodes_by_color(expected_by_id, evidence.nodes, color_match_distance)
        for node_id, expected in expected_by_id.items():
            node = matched.get(node_id)
            if node is None:
                continue
            if node.shape != expected["shape"]:
                finding_id = f"finding-node-shape-{node_id}"
                findings.append(
                    _make_finding(
                        finding_id,
                        shape_claim.rule_id,
                        "node_shape_wrong",
                        shape_claim.severity,
                        (
                            f"Node '{node_id}' renders as a '{node.shape}' but the spec declares "
                            f"'{expected['shape']}'."
                        ),
                        {
                            "node_id": node_id,
                            "expected_shape": expected["shape"],
                            "detected_shape": node.shape,
                            "fill_ratio": node.fill_ratio,
                        },
                        "Redraw the node using its declared shape.",
                    )
                )
                overlay_annotations.append(
                    OverlayAnnotation(finding_id=finding_id, kind="bbox", bbox=node.bbox, label=f"{node_id}: shape")
                )

    label_claim = claims.get("node-label-correct")
    if label_claim is not None and label_claim.check_id in skipped_by_check:
        checks_skipped.append(
            {"check_id": label_claim.check_id, "reason": skipped_by_check[label_claim.check_id][0]}
        )
    elif label_claim is not None:
        checks_run.append(label_claim.check_id)
        expected_by_id = label_claim.expected["nodes_by_id"]
        color_match_distance = float(label_claim.tolerance.get("color_match_distance", 60.0))
        if not matched:
            matched, _ = _match_nodes_by_color(expected_by_id, evidence.nodes, color_match_distance)
        for node_id, expected in expected_by_id.items():
            expected_label = expected.get("label_text")
            if not expected_label:
                continue
            node = matched.get(node_id)
            if node is None:
                continue
            if node.label_text != expected_label:
                finding_id = f"finding-node-label-{node_id}"
                findings.append(
                    _make_finding(
                        finding_id,
                        label_claim.rule_id,
                        "node_label_wrong",
                        label_claim.severity,
                        (
                            f"Node '{node_id}' label reads "
                            f"{node.label_text!r} but the spec declares {expected_label!r}."
                        ),
                        {
                            "node_id": node_id,
                            "expected_label": expected_label,
                            "detected_label": node.label_text,
                            "label_confidence": node.label_confidence,
                        },
                        "Redraw the node's label text to match the declared spec.",
                    )
                )
                overlay_annotations.append(
                    OverlayAnnotation(finding_id=finding_id, kind="bbox", bbox=node.bbox, label=f"{node_id}: label")
                )

    connector_claim = claims.get("connector-links-correct")
    if connector_claim is not None and connector_claim.check_id in skipped_by_check:
        checks_skipped.append(
            {"check_id": connector_claim.check_id, "reason": skipped_by_check[connector_claim.check_id][0]}
        )
    elif connector_claim is not None:
        checks_run.append(connector_claim.check_id)
        expected_edges = connector_claim.expected["ordered_edges"]
        expected_by_id = connector_claim.expected["nodes_by_id"]
        color_match_distance = float(connector_claim.tolerance.get("color_match_distance", 60.0))
        if not matched:
            matched, _ = _match_nodes_by_color(expected_by_id, evidence.nodes, color_match_distance)
        detected_edges: set[tuple[str, str]] = {
            (connector.from_node_id, connector.to_node_id)
            for connector in evidence.connectors
            if connector.from_node_id is not None and connector.to_node_id is not None
        }
        for from_id, to_id in expected_edges:
            from_node = matched.get(from_id)
            to_node = matched.get(to_id)
            # An unresolved endpoint is already reported by the presence check
            # (or an evidence gap); skip judging only this edge rather than
            # discarding the whole connector check.
            if from_node is None or to_node is None:
                continue
            if (from_node.node_id, to_node.node_id) not in detected_edges:
                finding_id = f"finding-connector-missing-{from_id}-{to_id}"
                findings.append(
                    _make_finding(
                        finding_id,
                        connector_claim.rule_id,
                        "missing_connector",
                        connector_claim.severity,
                        (
                            f"The declared connector from '{from_id}' to '{to_id}' was not found in "
                            "the rendered arrow evidence."
                        ),
                        {"expected_edge": [from_id, to_id]},
                        "Draw a connector arrow from the declared source node to the target node.",
                    )
                )
                overlay_annotations.append(
                    OverlayAnnotation(
                        finding_id=finding_id, kind="bbox", bbox=from_node.bbox, label=f"{from_id}-{to_id}: connector"
                    )
                )

        expected_edge_node_ids = {
            (matched[from_id].node_id, matched[to_id].node_id)
            for from_id, to_id in expected_edges
            if from_id in matched and to_id in matched
        }
        for from_node_id, to_node_id in detected_edges:
            if (from_node_id, to_node_id) in expected_edge_node_ids:
                continue
            finding_id = f"finding-connector-extra-{from_node_id}-{to_node_id}"
            findings.append(
                _make_finding(
                    finding_id,
                    connector_claim.rule_id,
                    "extra_connector",
                    "high",
                    (
                        f"Detected a connector from '{from_node_id}' to '{to_node_id}' that is not "
                        "declared in the spec."
                    ),
                    {"detected_edge": [from_node_id, to_node_id]},
                    "Remove the extra connector or declare it in the spec.",
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
