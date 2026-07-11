"""Controlled circuit-v1b dataset with explicit junction dots and bounded branches."""

from __future__ import annotations

import json
import shutil
from pathlib import Path
from typing import Any

from .circuit_generator import component_terminals, render_circuit_probe


PARALLEL_COMPONENTS = [
    {"id": "battery", "symbol_type": "battery", "rgb": [220, 50, 50], "center_px": [100, 190]},
    {"id": "resistor", "symbol_type": "resistor", "rgb": [45, 155, 65], "center_px": [260, 190], "orientation": "vertical"},
    {"id": "lamp", "symbol_type": "lamp", "rgb": [45, 90, 220], "center_px": [420, 190]},
]

MIXED_COMPONENTS = [
    {"id": "battery", "symbol_type": "battery", "rgb": [220, 50, 50], "center_px": [80, 80]},
    {"id": "resistor", "symbol_type": "resistor", "rgb": [45, 155, 65], "center_px": [200, 80], "orientation": "vertical"},
    {"id": "lamp_a", "symbol_type": "lamp", "rgb": [45, 90, 220], "center_px": [320, 200]},
    {"id": "lamp_b", "symbol_type": "lamp", "rgb": [190, 105, 35], "center_px": [440, 200]},
]

PARALLEL_VARIANT_COMPONENTS = [
    {**PARALLEL_COMPONENTS[0], "center_px": [80, 190]},
    {**PARALLEL_COMPONENTS[1], "center_px": [280, 190]},
    {**PARALLEL_COMPONENTS[2], "center_px": [460, 190]},
]

MIXED_VARIANT_COMPONENTS = [
    {**MIXED_COMPONENTS[0], "center_px": [100, 90]},
    {**MIXED_COMPONENTS[1], "center_px": [220, 90]},
    {**MIXED_COMPONENTS[2], "center_px": [330, 210]},
    {**MIXED_COMPONENTS[3], "center_px": [460, 210]},
]


def _parallel_graph(components: list[dict[str, Any]], top_y: int = 100, bottom_y: int = 280) -> tuple[list[dict[str, Any]], list[tuple[int, int]], list[list[str]]]:
    p = {component["id"]: component_terminals(component) for component in components}
    x = {component["id"]: component["center_px"][0] for component in components}
    nets = [
        {"points": [p["battery"]["a"], (x["battery"], top_y), (x["resistor"], top_y), p["resistor"]["a"], (x["resistor"], top_y), (x["lamp"], top_y), p["lamp"]["a"]]},
        {"points": [p["battery"]["b"], (x["battery"], bottom_y), (x["resistor"], bottom_y), p["resistor"]["b"], (x["resistor"], bottom_y), (x["lamp"], bottom_y), p["lamp"]["b"]]},
    ]
    return nets, [(x["resistor"], top_y), (x["resistor"], bottom_y)], [["battery.a", "resistor.a", "lamp.a"], ["battery.b", "resistor.b", "lamp.b"]]


def _mixed_graph(components: list[dict[str, Any]], top_y: int = 20, branch_y: int = 145, return_y: int = 260, bottom_y: int = 330, left_x: int = 40) -> tuple[list[dict[str, Any]], list[tuple[int, int]], list[list[str]]]:
    p = {component["id"]: component_terminals(component) for component in components}
    x = {component["id"]: component["center_px"][0] for component in components}
    nets = [
        {"points": [p["battery"]["a"], (x["battery"], top_y), (x["resistor"], top_y), p["resistor"]["a"]]},
        {"points": [p["resistor"]["b"], (x["resistor"], branch_y), (x["lamp_a"], branch_y), p["lamp_a"]["a"], (x["lamp_a"], branch_y), (x["lamp_b"], branch_y), p["lamp_b"]["a"]]},
        {"points": [p["battery"]["b"], (left_x, p["battery"]["b"][1]), (left_x, bottom_y), (x["lamp_a"], bottom_y), (x["lamp_a"], return_y), p["lamp_a"]["b"], (x["lamp_a"], return_y), (x["lamp_b"], return_y), p["lamp_b"]["b"]]},
    ]
    return nets, [(x["lamp_a"], branch_y), (x["lamp_a"], return_y)], [["battery.a", "resistor.a"], ["resistor.b", "lamp_a.a", "lamp_b.a"], ["battery.b", "lamp_a.b", "lamp_b.b"]]


def _mixed_missing_branch_graph() -> tuple[list[dict[str, Any]], list[tuple[int, int]], list[list[str]]]:
    p = {component["id"]: component_terminals(component) for component in MIXED_COMPONENTS}
    nets = [
        {"points": [p["battery"]["a"], (80, 20), (200, 20), p["resistor"]["a"]]},
        {"points": [p["resistor"]["b"], (200, 145), (320, 145), p["lamp_a"]["a"]]},
        {"points": [p["battery"]["b"], (40, 113), (40, 330), (320, 330), (320, 260), p["lamp_a"]["b"]]},
        {"points": [p["lamp_b"]["a"], (490, 176), (490, 224), p["lamp_b"]["b"]]},
    ]
    actual = [["battery.a", "resistor.a"], ["resistor.b", "lamp_a.a"], ["battery.b", "lamp_a.b"], ["lamp_b.a", "lamp_b.b"]]
    return nets, [], actual


def _mixed_swapped_branch_graph() -> tuple[list[dict[str, Any]], list[tuple[int, int]], list[list[str]]]:
    p = {component["id"]: component_terminals(component) for component in MIXED_COMPONENTS}
    nets = [
        {"points": [p["battery"]["a"], (80, 20), (200, 20), p["resistor"]["a"]]},
        {"points": [p["resistor"]["b"], (200, 145), (370, 145), (370, 224), p["lamp_a"]["b"], (370, 224), (370, 145), (440, 145), p["lamp_b"]["a"]]},
        {"points": [p["battery"]["b"], (40, 113), (40, 330), (270, 330), (270, 176), p["lamp_a"]["a"], (270, 176), (270, 260), (440, 260), p["lamp_b"]["b"]]},
    ]
    actual = [["battery.a", "resistor.a"], ["resistor.b", "lamp_a.b", "lamp_b.a"], ["battery.b", "lamp_a.a", "lamp_b.b"]]
    return nets, [(370, 145), (270, 260)], actual


def _spec(case_id: str, components: list[dict[str, Any]], topology: str, terminal_nets: list[list[str]], junction_count: int = 2) -> dict[str, Any]:
    return {
        "id": f"circuit-v1b-{case_id}", "domain": "physics", "risk_level": "medium",
        "learning_objective": "Verify explicit junctions and a bounded branch circuit topology.",
        "source_reference": {
            "topology": topology, "junction_count": junction_count,
            "components": [{key: component[key] for key in ("id", "symbol_type", "rgb")} for component in components],
            "nets": [{"terminals": terminals} for terminals in terminal_nets],
        },
        "checks": [
            {"id": "component-count-matches", "type": "component_count_matches", "severity": "high"},
            {"id": "required-components-present", "type": "required_components_present", "severity": "critical"},
            {"id": "component-type-correct", "type": "component_type_correct", "severity": "critical"},
            {"id": "terminal-netlist-correct", "type": "terminal_netlist_correct", "severity": "critical"},
            {"id": "junction-count-correct", "type": "junction_count_correct", "severity": "critical"},
            {"id": "declared-topology-correct", "type": "declared_topology_correct", "severity": "critical"},
        ],
    }


def dataset_cases() -> list[dict[str, Any]]:
    parallel_nets, parallel_junctions, parallel_terminals = _parallel_graph(PARALLEL_COMPONENTS)
    mixed_nets, mixed_junctions, mixed_terminals = _mixed_graph(MIXED_COMPONENTS)
    parallel_variant_nets, parallel_variant_junctions, _ = _parallel_graph(PARALLEL_VARIANT_COMPONENTS, 70, 310)
    mixed_variant_nets, mixed_variant_junctions, _ = _mixed_graph(MIXED_VARIANT_COMPONENTS, 25, 155, 275, 345, 50)
    missing_branch_nets, missing_branch_junctions, missing_branch_actual = _mixed_missing_branch_graph()
    swapped_branch_nets, swapped_branch_junctions, swapped_branch_actual = _mixed_swapped_branch_graph()
    extra_component = {"id": "extra", "symbol_type": "lamp", "rgb": [170, 40, 175], "center_px": [480, 190]}
    extra = PARALLEL_COMPONENTS + [extra_component]
    extra_ports = component_terminals(extra_component)
    extra_branch_nets = [
        {"points": parallel_nets[0]["points"] + [(420, 100), (480, 100), extra_ports["a"]]},
        {"points": parallel_nets[1]["points"] + [(420, 280), (480, 280), extra_ports["b"]]},
    ]
    unknown = [{**c, **({"symbol_type": "unknown"} if c["id"] == "resistor" else {})} for c in PARALLEL_COMPONENTS]
    merged = parallel_nets + [{"points": [(500, 100), (500, 280)]}]
    # Extend both rails to the bridge so the two expected nets become one complete observed net.
    merged[0] = {"points": parallel_nets[0]["points"] + [(500, 100)]}
    merged[1] = {"points": parallel_nets[1]["points"] + [(500, 280)]}
    broken = [parallel_nets[0], {"points": parallel_nets[1]["points"][:-1]}, {"points": [component_terminals(PARALLEL_COMPONENTS[2])["b"], (420, 240)]}]
    near_dot = parallel_junctions + [(350, 88)]
    return [
        {"id": "golden-parallel-01", "kind": "golden", "topology": "simple_parallel", "components": PARALLEL_COMPONENTS, "nets": parallel_nets, "junctions": parallel_junctions, "terminal_nets": parallel_terminals, "verdict": "pass", "types": []},
        {"id": "golden-parallel-02", "kind": "golden", "topology": "simple_parallel", "components": PARALLEL_VARIANT_COMPONENTS, "nets": parallel_variant_nets, "junctions": parallel_variant_junctions, "terminal_nets": parallel_terminals, "verdict": "pass", "types": []},
        {"id": "golden-mixed-01", "kind": "golden", "topology": "series_parallel", "components": MIXED_COMPONENTS, "nets": mixed_nets, "junctions": mixed_junctions, "terminal_nets": mixed_terminals, "verdict": "pass", "types": []},
        {"id": "golden-mixed-02", "kind": "golden", "topology": "series_parallel", "components": MIXED_VARIANT_COMPONENTS, "nets": mixed_variant_nets, "junctions": mixed_variant_junctions, "terminal_nets": mixed_terminals, "verdict": "pass", "types": []},
        {"id": "mutated-01", "kind": "mutated", "defect": "missing_junction", "topology": "simple_parallel", "components": PARALLEL_COMPONENTS, "nets": parallel_nets, "junctions": parallel_junctions[:1], "terminal_nets": parallel_terminals, "verdict": "fail", "types": ["missing_junction"]},
        {"id": "mutated-02", "kind": "mutated", "defect": "extra_junction", "topology": "simple_parallel", "components": PARALLEL_COMPONENTS, "nets": parallel_nets, "junctions": parallel_junctions + [(350, 100)], "terminal_nets": parallel_terminals, "verdict": "fail", "types": ["extra_junction"]},
        {"id": "mutated-03", "kind": "mutated", "defect": "merged_branch_nets", "topology": "simple_parallel", "components": PARALLEL_COMPONENTS, "nets": merged, "junctions": parallel_junctions, "terminal_nets": parallel_terminals, "verdict": "fail", "types": ["missing_net", "extra_net", "branch_topology_wrong"]},
        {"id": "mutated-04", "kind": "mutated", "defect": "wrong_declared_topology", "topology": "series_parallel", "components": PARALLEL_COMPONENTS, "nets": parallel_nets, "junctions": parallel_junctions, "terminal_nets": parallel_terminals, "verdict": "fail", "types": ["branch_topology_wrong"]},
        {"id": "mutated-05", "kind": "mutated", "defect": "complete_extra_branch", "topology": "simple_parallel", "components": extra, "nets": extra_branch_nets, "junctions": parallel_junctions + [(420, 100), (420, 280)], "terminal_nets": parallel_terminals, "spec_components": PARALLEL_COMPONENTS, "verdict": "fail", "types": ["component_count_mismatch", "extra_component", "extra_junction"]},
        {"id": "mutated-06", "kind": "mutated", "defect": "disconnected_branch", "topology": "simple_parallel", "components": PARALLEL_COMPONENTS, "nets": broken, "junctions": parallel_junctions, "terminal_nets": parallel_terminals, "verdict": "needs_review", "types": []},
        {"id": "mutated-07", "kind": "mutated", "defect": "false_near_junction", "topology": "simple_parallel", "components": PARALLEL_COMPONENTS, "nets": parallel_nets, "junctions": near_dot, "terminal_nets": parallel_terminals, "verdict": "needs_review", "types": []},
        {"id": "mutated-08", "kind": "mutated", "defect": "unrecognized_symbol", "topology": "simple_parallel", "components": unknown, "nets": parallel_nets, "junctions": parallel_junctions, "terminal_nets": parallel_terminals, "verdict": "needs_review", "types": []},
        {"id": "mutated-09", "kind": "mutated", "defect": "complete_missing_split_branch", "topology": "series_parallel", "components": MIXED_COMPONENTS, "nets": missing_branch_nets, "junctions": missing_branch_junctions, "terminal_nets": mixed_terminals, "actual_terminal_nets": missing_branch_actual, "verdict": "fail", "types": ["missing_net", "extra_net", "missing_junction", "branch_topology_wrong"]},
        {"id": "mutated-10", "kind": "mutated", "defect": "swapped_branch_attachment", "topology": "series_parallel", "components": MIXED_COMPONENTS, "nets": swapped_branch_nets, "junctions": swapped_branch_junctions, "terminal_nets": mixed_terminals, "actual_terminal_nets": swapped_branch_actual, "verdict": "fail", "types": ["missing_net", "extra_net"]},
    ]


def build_circuit_v1b_dataset(output_root: Path) -> None:
    if output_root.exists():
        shutil.rmtree(output_root)
    for case in dataset_cases():
        case_dir = output_root / case["kind"] / case["id"]
        case_dir.mkdir(parents=True, exist_ok=True)
        spec_components = case.get("spec_components", case["components"])
        spec = _spec(case["id"], spec_components, case["topology"], case["terminal_nets"])
        expected_evidence: dict[str, Any] = {}
        if case.get("defect") != "unrecognized_symbol":
            expected_evidence["component_count"] = len(case["components"])
        if case.get("defect") not in {"disconnected_branch", "false_near_junction", "unrecognized_symbol"}:
            if case.get("actual_terminal_nets") is not None:
                expected_evidence["terminal_nets"] = case["actual_terminal_nets"]
            elif case.get("defect") == "merged_branch_nets":
                expected_evidence["terminal_nets"] = [[terminal for net in case["terminal_nets"] for terminal in net]]
            else:
                expected_evidence["terminal_nets"] = case["terminal_nets"]
        if case.get("defect") not in {"disconnected_branch", "false_near_junction", "unrecognized_symbol"}:
            expected_evidence["junction_count"] = len(case["junctions"])
        expected = {"verdict": case["verdict"], "expected_finding_types": case["types"], "expected_evidence": expected_evidence}
        metadata = {"case_id": case["id"], "title": case["id"].replace("-", " "), "kind": case["kind"], "defect_type": case.get("defect"), "scenario": case["topology"], "dataset_track": "controlled", "diagram_version": "circuit-v1b", "renderer": "pillow"}
        (case_dir / "visual_spec.json").write_text(json.dumps(spec, indent=2), encoding="utf-8")
        (case_dir / "expected_report.json").write_text(json.dumps(expected, indent=2), encoding="utf-8")
        (case_dir / "metadata.json").write_text(json.dumps(metadata, indent=2), encoding="utf-8")
        render_circuit_probe(case_dir / "image.png", case["components"], case["nets"], junctions=case["junctions"])
