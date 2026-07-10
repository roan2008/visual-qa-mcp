from __future__ import annotations

import json
from pathlib import Path

from visual_qa_mcp.claim_graph import build_chart_claim_graph, build_geometry_claim_graph
from visual_qa_mcp.geometry_dataset import build_geometry_dataset
from visual_qa_mcp.geometry_extractor import extract_geometry_evidence
from visual_qa_mcp.validation import discover_geometry_cases
from visual_qa_mcp.validation import load_schema, validate_json


ROOT = Path(__file__).resolve().parents[2]


def test_existing_example_specs_validate() -> None:
    validator = load_schema(ROOT / "specs" / "visual-spec.schema.json")
    for spec_path in sorted((ROOT / "specs" / "examples").glob("*.json")):
        payload = json.loads(spec_path.read_text(encoding="utf-8"))
        errors = validate_json(validator, payload)
        assert errors == [], f"{spec_path.name}: {errors}"


def test_report_fixtures_validate() -> None:
    validator = load_schema(ROOT / "specs" / "findings.schema.json")
    fixture_dir = ROOT / "mcp-server" / "tests" / "fixtures" / "reports"
    for report_path in sorted(fixture_dir.glob("*.json")):
        payload = json.loads(report_path.read_text(encoding="utf-8"))
        errors = validate_json(validator, payload)
        assert errors == [], f"{report_path.name}: {errors}"


def test_evidence_graph_schema_accepts_sample_payload() -> None:
    validator = load_schema(ROOT / "specs" / "evidence-graph.schema.json")
    sample_path = ROOT / "mcp-server" / "tests" / "fixtures" / "evidence-graph.sample.json"
    payload = json.loads(sample_path.read_text(encoding="utf-8"))
    errors = validate_json(validator, payload)
    assert errors == []


def test_chart_claim_graph_schema_accepts_generated_example() -> None:
    validator = load_schema(ROOT / "specs" / "claim-graph.schema.json")
    payload = build_chart_claim_graph(ROOT / "specs" / "examples" / "chart-bar.visual-spec.json").to_dict()
    errors = validate_json(validator, payload)
    assert errors == []


def test_geometry_schemas_accept_generated_case(tmp_path: Path) -> None:
    dataset_root = tmp_path / "geometry-v1"
    build_geometry_dataset(dataset_root)
    case = discover_geometry_cases(dataset_root)[0]
    claim_errors = validate_json(
        load_schema(ROOT / "specs" / "claim-graph.schema.json"),
        build_geometry_claim_graph(case.spec_path).to_dict(),
    )
    evidence_errors = validate_json(
        load_schema(ROOT / "specs" / "geometry-evidence-graph.schema.json"),
        extract_geometry_evidence(case.image_path).to_dict(),
    )
    assert claim_errors == []
    assert evidence_errors == []
