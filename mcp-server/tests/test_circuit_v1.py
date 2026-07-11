from __future__ import annotations

import json
from pathlib import Path

from visual_qa_mcp.circuit_extractor import extract_circuit_evidence
from visual_qa_mcp.circuit_dataset import build_circuit_dataset
from visual_qa_mcp.circuit_generator import component_terminals, render_circuit_probe
from visual_qa_mcp.circuit_rules import run_circuit_claims
from visual_qa_mcp.claim_graph import build_circuit_claim_graph
from visual_qa_mcp.validation import summarize_circuit_validation_results
from visual_qa_mcp.cli import main


COMPONENTS = [
    {"id": "battery", "symbol_type": "battery", "rgb": [220, 50, 50], "center_px": [100, 190]},
    {"id": "resistor", "symbol_type": "resistor", "rgb": [45, 155, 65], "center_px": [260, 80]},
    {"id": "lamp", "symbol_type": "lamp", "rgb": [45, 90, 220], "center_px": [420, 190]},
]


def _nets() -> list[dict]:
    terminals = {component["id"]: component_terminals(component) for component in COMPONENTS}
    return [
        {"points": [terminals["battery"]["a"], (100, 80), terminals["resistor"]["a"]]},
        {"points": [terminals["resistor"]["b"], (420, 80), terminals["lamp"]["a"]]},
        {"points": [terminals["lamp"]["b"], (420, 300), (100, 300), terminals["battery"]["b"]]},
    ]


def _spec(path: Path) -> Path:
    payload = {
        "id": "circuit-v1a-test",
        "domain": "physics",
        "risk_level": "medium",
        "learning_objective": "Verify a controlled series DC circuit.",
        "source_reference": {
            "topology": "series_loop",
            "components": [{key: component[key] for key in ("id", "symbol_type", "rgb")} for component in COMPONENTS],
            "nets": [
                {"terminals": ["battery.a", "resistor.a"]},
                {"terminals": ["resistor.b", "lamp.a"]},
                {"terminals": ["lamp.b", "battery.b"]},
            ],
        },
        "checks": [
            {"id": "component-count-matches", "type": "component_count_matches", "severity": "high"},
            {"id": "required-components-present", "type": "required_components_present", "severity": "critical"},
            {"id": "component-type-correct", "type": "component_type_correct", "severity": "critical"},
            {"id": "terminal-netlist-correct", "type": "terminal_netlist_correct", "severity": "critical"},
            {"id": "series-topology-correct", "type": "series_topology_correct", "severity": "critical"},
        ],
    }
    path.write_text(json.dumps(payload), encoding="utf-8")
    return path


def test_circuit_v1a_golden_series_loop_passes(tmp_path: Path) -> None:
    spec_path = _spec(tmp_path / "spec.json")
    image_path = tmp_path / "golden.png"
    render_circuit_probe(image_path, COMPONENTS, _nets())

    report = run_circuit_claims(build_circuit_claim_graph(spec_path), extract_circuit_evidence(image_path))

    assert report.verdict == "pass"
    assert report.findings == []
    assert set(report.checks_run) == {
        "component-count-matches",
        "required-components-present",
        "component-type-correct",
        "terminal-netlist-correct",
        "series-topology-correct",
    }


def test_circuit_v1a_missing_wire_evidence_needs_review(tmp_path: Path) -> None:
    spec_path = _spec(tmp_path / "spec.json")
    image_path = tmp_path / "missing-wires.png"
    render_circuit_probe(image_path, COMPONENTS, [])

    report = run_circuit_claims(build_circuit_claim_graph(spec_path), extract_circuit_evidence(image_path))

    assert report.verdict == "needs_review"
    assert report.findings == []
    assert len(report.checks_skipped) == 5


def test_circuit_v1a_controlled_dataset_validation_gate(tmp_path: Path) -> None:
    dataset_root = tmp_path / "circuit-v1a"
    build_circuit_dataset(dataset_root)

    summary = summarize_circuit_validation_results(dataset_root)

    assert summary["total_cases"] == 11
    assert summary["typed_mutated_hits"] == 4
    assert summary["typed_mutated_cases"] == 4
    assert summary["ambiguous_guard_rate"] == 1.0
    assert summary["false_unsupported_passes"] == 0
    assert summary["golden_non_passes"] == 0
    assert summary["verdict_mismatches"] == 0
    assert summary["evidence_metrics"]["terminal_netlist_cases"] == 6
    assert summary["evidence_metrics"]["terminal_netlist_hits"] == 6
    assert summary["evidence_metrics"]["terminal_netlist_accuracy"] == 1.0


def test_circuit_v1a_cli_surfaces_execute_end_to_end(tmp_path: Path, capsys) -> None:
    dataset_root = tmp_path / "circuit-v1a"
    assert main(["generate-circuit-dataset", "--output", str(dataset_root)]) == 0
    assert "Circuit dataset generated at" in capsys.readouterr().out

    case_dir = dataset_root / "golden" / "golden-01"
    output_dir = tmp_path / "artifacts"
    assert main(["verify-circuit", str(case_dir / "image.png"), str(case_dir / "visual_spec.json"), "--output-dir", str(output_dir)]) == 0
    verified = json.loads(capsys.readouterr().out)
    assert verified["report"]["verdict"] == "pass"
    assert (output_dir / "report.json").exists()

    assert main(["run-circuit-validation", "--dataset", str(dataset_root)]) == 0
    summary = json.loads(capsys.readouterr().out)
    assert summary["typed_mutated_hits"] == 4
    assert summary["evidence_metrics"]["terminal_netlist_accuracy"] == 1.0
