from __future__ import annotations

from pathlib import Path

from visual_qa_mcp.circuit_v1b_dataset import build_circuit_v1b_dataset
from visual_qa_mcp.cli import main
from visual_qa_mcp.validation import summarize_circuit_validation_results


def test_circuit_v1b_controlled_branch_gate(tmp_path: Path) -> None:
    root = tmp_path / "circuit-v1b"
    build_circuit_v1b_dataset(root)
    summary = summarize_circuit_validation_results(root)
    assert summary["total_cases"] == 14
    assert summary["typed_mutated_hits"] == summary["typed_mutated_cases"] == 7
    assert summary["ambiguous_cases"] == 3
    assert summary["ambiguous_guard_rate"] == 1.0
    assert summary["golden_non_passes"] == 0
    assert summary["false_unsupported_passes"] == 0
    assert summary["verdict_mismatches"] == 0
    assert summary["evidence_metrics"]["terminal_netlist_accuracy"] == 1.0
    assert summary["evidence_metrics"]["junction_count_accuracy"] == 1.0
    assert summary["subset_metrics"]["simple_parallel"]["golden_pass_rate"] == 1.0
    assert summary["subset_metrics"]["series_parallel"]["golden_pass_rate"] == 1.0


def test_circuit_v1b_cli_generation_and_validation(tmp_path: Path, capsys) -> None:
    root = tmp_path / "circuit-v1b"
    assert main(["generate-circuit-v1b-dataset", "--output", str(root)]) == 0
    assert "Circuit v1b dataset generated at" in capsys.readouterr().out
    assert main(["run-circuit-validation", "--dataset", str(root)]) == 0
    assert '"typed_mutated_hits": 7' in capsys.readouterr().out
