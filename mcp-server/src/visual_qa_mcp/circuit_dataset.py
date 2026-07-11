"""Generated controlled dataset for the circuit-v1a series-loop verifier."""

from __future__ import annotations

import json
import shutil
from pathlib import Path
from typing import Any

from .circuit_generator import component_terminals, render_circuit_probe


COMPONENTS = [
    {"id": "battery", "symbol_type": "battery", "rgb": [220, 50, 50], "center_px": [100, 190]},
    {"id": "resistor", "symbol_type": "resistor", "rgb": [45, 155, 65], "center_px": [260, 80]},
    {"id": "lamp", "symbol_type": "lamp", "rgb": [45, 90, 220], "center_px": [420, 190]},
]

CANONICAL_TERMINAL_NETS = [
    ["battery.a", "resistor.a"],
    ["resistor.b", "lamp.a"],
    ["lamp.b", "battery.b"],
]

SWAPPED_TERMINAL_NETS = [
    ["battery.a", "resistor.b"],
    ["resistor.a", "lamp.a"],
    ["lamp.b", "battery.b"],
]

DISCONNECTED_TERMINAL_NETS = [
    ["battery.a", "battery.b"],
    ["resistor.a", "resistor.b"],
    ["lamp.a", "lamp.b"],
]


def _canonical_nets(components: list[dict[str, Any]]) -> list[dict[str, Any]]:
    ports = {component["id"]: component_terminals(component) for component in components}
    return [
        {"points": [ports["battery"]["a"], (100, 80), ports["resistor"]["a"]]},
        {"points": [ports["resistor"]["b"], (420, 80), ports["lamp"]["a"]]},
        {"points": [ports["lamp"]["b"], (420, 300), (100, 300), ports["battery"]["b"]]},
    ]


def _routing_variant_nets(components: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Same declared netlist, deliberately different non-crossing orthogonal routes."""
    ports = {component["id"]: component_terminals(component) for component in components}
    return [
        {"points": [ports["battery"]["a"], (60, 157), (60, 40), (224, 40), ports["resistor"]["a"]]},
        {"points": [ports["resistor"]["b"], (456, 80), (456, 166), ports["lamp"]["a"]]},
        {"points": [ports["lamp"]["b"], (460, 214), (460, 330), (70, 330), (70, 223), ports["battery"]["b"]]},
    ]


def _swapped_terminal_nets(components: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Complete non-crossing wiring with one terminal pairing swapped."""
    ports = {component["id"]: component_terminals(component) for component in components}
    return [
        {"points": [ports["battery"]["a"], (100, 20), (296, 20), ports["resistor"]["b"]]},
        {"points": [ports["resistor"]["a"], (224, 120), (480, 120), (480, 166), ports["lamp"]["a"]]},
        {"points": [ports["lamp"]["b"], (420, 300), (100, 300), ports["battery"]["b"]]},
    ]


def _disconnected_self_loop_nets(components: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Three complete self-nets: valid attachments, but not one series loop."""
    ports = {component["id"]: component_terminals(component) for component in components}
    return [
        {"points": [ports["battery"]["a"], (40, 157), (40, 223), ports["battery"]["b"]]},
        {"points": [ports["resistor"]["a"], (224, 20), (296, 20), ports["resistor"]["b"]]},
        {"points": [ports["lamp"]["a"], (480, 166), (480, 214), ports["lamp"]["b"]]},
    ]


def _spec(case_id: str) -> dict[str, Any]:
    return {
        "id": f"circuit-v1a-{case_id}",
        "domain": "physics",
        "risk_level": "medium",
        "learning_objective": "Verify the declared structural connectivity of a controlled series DC circuit.",
        "source_reference": {
            "topology": "series_loop",
            "components": [{key: component[key] for key in ("id", "symbol_type", "rgb")} for component in COMPONENTS],
            "nets": [{"terminals": terminals} for terminals in CANONICAL_TERMINAL_NETS],
        },
        "checks": [
            {"id": "component-count-matches", "type": "component_count_matches", "severity": "high"},
            {"id": "required-components-present", "type": "required_components_present", "severity": "critical"},
            {"id": "component-type-correct", "type": "component_type_correct", "severity": "critical"},
            {"id": "terminal-netlist-correct", "type": "terminal_netlist_correct", "severity": "critical"},
            {"id": "series-topology-correct", "type": "series_topology_correct", "severity": "critical"},
        ],
    }


def _case(case_id: str, title: str, kind: str, expected: dict[str, Any], *, defect_type: str | None = None, render_components: list[dict[str, Any]] | None = None, render_nets: list[dict[str, Any]] | None = None) -> dict[str, Any]:
    return {
        "case_id": case_id, "title": title, "kind": kind, "defect_type": defect_type,
        "expected": expected, "render_components": render_components or COMPONENTS,
        "render_nets": render_nets if render_nets is not None else _canonical_nets(COMPONENTS),
    }


def dataset_cases() -> list[dict[str, Any]]:
    golden = {"verdict": "pass", "expected_finding_types": [], "expected_evidence": {"component_count": 3, "net_count": 3, "terminal_nets": CANONICAL_TERMINAL_NETS}}
    extra = COMPONENTS + [{"id": "extra", "symbol_type": "resistor", "rgb": [180, 70, 190], "center_px": [260, 340]}]
    wrong_battery = [{**component, **({"symbol_type": "lamp"} if component["id"] == "battery" else {})} for component in COMPONENTS]
    canonical = _canonical_nets(COMPONENTS)
    broken = canonical[:2] + [
        {"points": [component_terminals(COMPONENTS[2])["b"], (420, 300), (180, 300)]},
        {"points": [(150, 300), (100, 300), component_terminals(COMPONENTS[0])["b"]]},
    ]
    near_miss = [canonical[0], {"points": [component_terminals(COMPONENTS[1])["b"], (420, 80), (434, 80), (434, 142)]}, canonical[2]]
    unknown = [{**component, **({"symbol_type": "unknown"} if component["id"] == "resistor" else {})} for component in COMPONENTS]
    return [
        _case("golden-01", "Canonical battery-resistor-lamp series loop", "golden", golden),
        _case("golden-02", "Same series netlist with an alternate orthogonal route layout", "golden", golden, render_nets=_routing_variant_nets(COMPONENTS)),
        _case("mutated-01", "Extra undeclared resistor component", "mutated", {"verdict": "fail", "expected_finding_types": ["component_count_mismatch", "extra_component"], "expected_evidence": {"component_count": 4, "net_count": 3, "terminal_nets": CANONICAL_TERMINAL_NETS}}, defect_type="extra_component", render_components=extra),
        _case("mutated-02", "Battery rendered as lamp with terminal-compatible controlled geometry", "mutated", {"verdict": "fail", "expected_finding_types": ["component_type_wrong"], "expected_evidence": {"component_count": 3, "net_count": 3, "terminal_nets": CANONICAL_TERMINAL_NETS}}, defect_type="component_type_wrong", render_components=wrong_battery),
        _case("mutated-08", "Complete circuit with swapped terminal pairings", "mutated", {"verdict": "fail", "expected_finding_types": ["missing_net", "extra_net"], "expected_evidence": {"component_count": 3, "net_count": 3, "terminal_nets": SWAPPED_TERMINAL_NETS}}, defect_type="swapped_terminal_netlist", render_nets=_swapped_terminal_nets(COMPONENTS)),
        _case("mutated-09", "Complete disconnected self-loops instead of one series loop", "mutated", {"verdict": "fail", "expected_finding_types": ["missing_net", "extra_net", "series_topology_wrong"], "expected_evidence": {"component_count": 3, "net_count": 3, "terminal_nets": DISCONNECTED_TERMINAL_NETS}}, defect_type="non_series_topology", render_nets=_disconnected_self_loop_nets(COMPONENTS)),
        _case("mutated-03", "Broken return wire creates incomplete attachment evidence", "mutated", {"verdict": "needs_review", "expected_finding_types": [], "expected_evidence": {"component_count": 3}}, defect_type="broken_wire", render_nets=broken),
        _case("mutated-04", "Wire terminates near but not at lamp terminal", "mutated", {"verdict": "needs_review", "expected_finding_types": [], "expected_evidence": {"component_count": 3}}, defect_type="near_terminal_miss", render_nets=near_miss),
        _case("mutated-05", "No wire evidence", "mutated", {"verdict": "needs_review", "expected_finding_types": [], "expected_evidence": {"component_count": 3, "net_count": 0}}, defect_type="missing_wire_evidence", render_nets=[]),
        _case("mutated-06", "Extra disconnected wire fragment", "mutated", {"verdict": "needs_review", "expected_finding_types": [], "expected_evidence": {"component_count": 3}}, defect_type="extra_wire_fragment", render_nets=canonical + [{"points": [(30, 340), (70, 340)]}]),
        _case("mutated-07", "Unrecognized colored component geometry", "mutated", {"verdict": "needs_review", "expected_finding_types": [], "expected_evidence": {"net_count": 3}}, defect_type="unrecognized_symbol", render_components=unknown),
    ]


def build_circuit_dataset(output_root: Path) -> None:
    if output_root.exists():
        shutil.rmtree(output_root)
    for case in dataset_cases():
        case_dir = output_root / case["kind"] / case["case_id"]
        case_dir.mkdir(parents=True, exist_ok=True)
        (case_dir / "visual_spec.json").write_text(json.dumps(_spec(case["case_id"]), indent=2), encoding="utf-8")
        (case_dir / "metadata.json").write_text(json.dumps({"case_id": case["case_id"], "title": case["title"], "kind": case["kind"], "defect_type": case["defect_type"], "scenario": "circuit", "dataset_track": "controlled", "diagram_version": "circuit-v1a", "renderer": "pillow"}, indent=2), encoding="utf-8")
        (case_dir / "expected_report.json").write_text(json.dumps(case["expected"], indent=2), encoding="utf-8")
        render_circuit_probe(case_dir / "image.png", case["render_components"], case["render_nets"])
