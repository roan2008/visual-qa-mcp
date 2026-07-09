from __future__ import annotations

import json
from pathlib import Path

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
