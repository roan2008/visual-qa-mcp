"""Deterministic structural rules for controlled circuit-v1a evidence."""

from __future__ import annotations

import math
from typing import Any

from .chart_rules import _estimate_rule_confidence, _make_finding, _overall_verdict, _severity_rank
from .contracts import CircuitEvidenceGraph, ClaimGraph, ExtractedCircuitComponent, Finding, OverlayAnnotation, VisualQaReport


def _color_distance(first: list[int], second: list[int]) -> float:
    return math.sqrt(sum((float(a) - float(b)) ** 2 for a, b in zip(first, second, strict=True)))


def _match_components(expected: dict[str, dict[str, Any]], detected: list[ExtractedCircuitComponent], tolerance: float) -> tuple[dict[str, ExtractedCircuitComponent], list[ExtractedCircuitComponent]]:
    remaining = list(detected)
    matched: dict[str, ExtractedCircuitComponent] = {}
    candidates = [
        (distance, expected_id, component)
        for expected_id, item in expected.items()
        for component in remaining
        if (distance := _color_distance(item["rgb"], component.rgb)) <= tolerance
    ]
    for _, expected_id, component in sorted(candidates, key=lambda item: item[0]):
        if expected_id not in matched and component in remaining:
            matched[expected_id] = component
            remaining.remove(component)
    return matched, remaining


def _canonical_nets(nets: list[list[str]]) -> set[tuple[str, ...]]:
    return {tuple(sorted(net)) for net in nets}


def _observed_nets(evidence: CircuitEvidenceGraph, matched: dict[str, ExtractedCircuitComponent]) -> set[tuple[str, ...]]:
    reverse_ids = {component.component_id: expected_id for expected_id, component in matched.items()}
    mapped: list[list[str]] = []
    for net in evidence.nets:
        terminals: list[str] = []
        for attachment in net.attached_terminals:
            component_id, terminal_id = attachment.rsplit(".", 1)
            expected_id = reverse_ids.get(component_id)
            if expected_id is not None:
                terminals.append(f"{expected_id}.{terminal_id}")
        mapped.append(terminals)
    return _canonical_nets(mapped)


def _skip_map(claim_graph: ClaimGraph, evidence: CircuitEvidenceGraph) -> tuple[list[dict[str, str]], dict[str, str]]:
    skipped = [{"check_id": gap.check_id, "reason": gap.message} for gap in claim_graph.gaps]
    evidence_skips: dict[str, str] = {}
    for gap in evidence.gaps:
        for check_id in gap.check_ids:
            evidence_skips.setdefault(check_id, gap.message)
    return skipped, evidence_skips


def run_circuit_claims(claim_graph: ClaimGraph, evidence: CircuitEvidenceGraph) -> VisualQaReport:
    claims = {claim.check_id: claim for claim in claim_graph.claims}
    findings: list[Finding] = []
    checks_run: list[str] = []
    checks_skipped, evidence_skips = _skip_map(claim_graph, evidence)
    annotations: list[OverlayAnnotation] = []
    matched: dict[str, ExtractedCircuitComponent] = {}

    def run_or_skip(check_id: str) -> bool:
        if check_id not in claims:
            return False
        if check_id in evidence_skips:
            checks_skipped.append({"check_id": check_id, "reason": evidence_skips[check_id]})
            return False
        checks_run.append(check_id)
        return True

    count = claims.get("component-count-matches")
    if count and run_or_skip(count.check_id) and len(evidence.components) != int(count.expected["count"]):
        findings.append(_make_finding("finding-component-count", count.rule_id, "component_count_mismatch", count.severity, f"Detected {len(evidence.components)} components but expected {count.expected['count']}.", {"expected_count": count.expected["count"], "detected_count": len(evidence.components)}, "Regenerate the diagram with the declared number of components."))

    presence = claims.get("required-components-present")
    if presence and run_or_skip(presence.check_id):
        expected = presence.expected["components_by_id"]
        matched, unmatched = _match_components(expected, evidence.components, float(presence.tolerance["color_match_distance"]))
        for component_id, details in expected.items():
            if component_id not in matched:
                findings.append(_make_finding(f"finding-component-missing-{component_id}", presence.rule_id, "missing_component", presence.severity, f"Required component '{details.get('name') or component_id}' was not detected.", {"component_id": component_id, "expected_rgb": details["rgb"]}, "Add the missing declared component."))
        for component in unmatched:
            finding_id = f"finding-component-extra-{component.component_id}"
            findings.append(_make_finding(finding_id, presence.rule_id, "extra_component", "high", f"Detected component '{component.component_id}' does not match a declared component color.", {"component_id": component.component_id, "detected_rgb": component.rgb, "bbox": component.bbox}, "Remove the extra component or declare it in the spec."))
            annotations.append(OverlayAnnotation(finding_id=finding_id, kind="bbox", bbox=component.bbox, label="Unexpected component"))

    type_claim = claims.get("component-type-correct")
    if type_claim and run_or_skip(type_claim.check_id):
        expected = type_claim.expected["components_by_id"]
        if not matched:
            matched, _ = _match_components(expected, evidence.components, float(type_claim.tolerance["color_match_distance"]))
        for component_id, details in expected.items():
            component = matched.get(component_id)
            if component is not None and component.symbol_type != details["symbol_type"]:
                finding_id = f"finding-component-type-{component_id}"
                findings.append(_make_finding(finding_id, type_claim.rule_id, "component_type_wrong", type_claim.severity, f"Component '{component_id}' renders as '{component.symbol_type}' but the spec declares '{details['symbol_type']}'.", {"component_id": component_id, "expected_type": details["symbol_type"], "detected_type": component.symbol_type}, "Redraw the component using the declared symbol type."))
                annotations.append(OverlayAnnotation(finding_id=finding_id, kind="bbox", bbox=component.bbox, label=f"{component_id}: type"))

    netlist = claims.get("terminal-netlist-correct")
    if netlist and run_or_skip(netlist.check_id):
        expected = netlist.expected["components_by_id"]
        if not matched:
            matched, _ = _match_components(expected, evidence.components, float(netlist.tolerance["color_match_distance"]))
        expected_nets = _canonical_nets(netlist.expected["nets"])
        observed_nets = _observed_nets(evidence, matched)
        for net in sorted(expected_nets - observed_nets):
            findings.append(_make_finding(f"finding-net-missing-{'-'.join(net)}", netlist.rule_id, "missing_net", netlist.severity, f"Declared terminal net {list(net)} was not found.", {"expected_terminals": list(net)}, "Connect the declared terminals with one wire net."))
        for net in sorted(observed_nets - expected_nets):
            findings.append(_make_finding(f"finding-net-extra-{'-'.join(net)}", netlist.rule_id, "extra_net", "high", f"Detected terminal net {list(net)} is not declared.", {"detected_terminals": list(net)}, "Remove the extra wire or declare the intended net."))

    topology = claims.get("series-topology-correct")
    if topology and run_or_skip(topology.check_id):
        observed = _observed_nets(evidence, matched)
        component_ids = set(topology.expected["components_by_id"])
        terminal_counts = {component_id: 0 for component_id in component_ids}
        adjacency = {component_id: set() for component_id in component_ids}
        for net in observed:
            components = [terminal.rsplit(".", 1)[0] for terminal in net]
            for component in components:
                if component in terminal_counts:
                    terminal_counts[component] += 1
            if len(set(components)) == 2:
                first, second = components
                if first in adjacency and second in adjacency:
                    adjacency[first].add(second)
                    adjacency[second].add(first)
        reachable = set()
        if component_ids:
            stack = [next(iter(component_ids))]
            while stack:
                current = stack.pop()
                if current not in reachable:
                    reachable.add(current)
                    stack.extend(adjacency[current] - reachable)
        if any(count != 2 for count in terminal_counts.values()) or reachable != component_ids:
            findings.append(_make_finding("finding-series-topology", topology.rule_id, "series_topology_wrong", topology.severity, "Complete terminal-net evidence does not form one declared series loop.", {"terminal_counts": terminal_counts, "connected_components": len(component_ids - reachable) + 1 if component_ids else 0}, "Restore one closed series loop using the declared terminal netlist."))

    junction_claim = claims.get("junction-count-correct")
    if junction_claim and run_or_skip(junction_claim.check_id):
        expected_count = int(junction_claim.expected["count"])
        actual_count = len(evidence.junctions)
        if actual_count != expected_count:
            finding_type = "missing_junction" if actual_count < expected_count else "extra_junction"
            findings.append(_make_finding("finding-junction-count", junction_claim.rule_id, finding_type, junction_claim.severity, f"Detected {actual_count} explicit junction dots but expected {expected_count}.", {"expected_count": expected_count, "detected_count": actual_count}, "Restore the declared explicit junction dots at branch joins."))

    branch_topology = claims.get("declared-topology-correct")
    if branch_topology and run_or_skip(branch_topology.check_id):
        expected = branch_topology.expected["components_by_id"]
        if not matched:
            matched, _ = _match_components(expected, evidence.components, float(branch_topology.tolerance["color_match_distance"]))
        observed = _observed_nets(evidence, matched)
        net_degrees = sorted(len(net) for net in observed)
        component_net_counts = {component_id: 0 for component_id in expected}
        for net in observed:
            for terminal in net:
                component_id = terminal.rsplit(".", 1)[0]
                if component_id in component_net_counts:
                    component_net_counts[component_id] += 1
        topology_name = branch_topology.expected["topology"]
        if topology_name == "simple_parallel":
            topology_ok = len(observed) == 2 and net_degrees == [len(expected), len(expected)] and all(count == 2 for count in component_net_counts.values())
        else:
            topology_ok = len(observed) == 3 and net_degrees == [2, 3, 3] and all(count == 2 for count in component_net_counts.values())
        if not topology_ok:
            findings.append(_make_finding("finding-branch-topology", branch_topology.rule_id, "branch_topology_wrong", branch_topology.severity, f"Complete terminal-net evidence does not form the declared {topology_name} family.", {"net_degrees": net_degrees, "component_net_counts": component_net_counts}, "Restore the declared bounded branch topology."))

    findings = sorted(findings, key=lambda finding: _severity_rank(finding.severity), reverse=True)
    confidence = _estimate_rule_confidence(checks_run, checks_skipped, findings)
    return VisualQaReport(image_id=evidence.image_id, spec_id=claim_graph.spec_id, verdict=_overall_verdict(findings, checks_skipped), findings=findings, checks_run=checks_run, checks_skipped=checks_skipped, confidence=confidence, extraction_confidence=evidence.extraction_confidence, rule_confidence=confidence, overlay_annotations=annotations)
