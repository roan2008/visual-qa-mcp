from __future__ import annotations

import json
from pathlib import Path

import anyio
from mcp import types

from visual_qa_mcp.generate_dataset import build_dataset
from visual_qa_mcp.arrow_dataset import build_arrow_dataset
from visual_qa_mcp.geometry_dataset import build_geometry_dataset
from visual_qa_mcp.server import create_server
from visual_qa_mcp.validation import (
    discover_cases,
    discover_arrow_cases,
    discover_geometry_cases,
    load_schema,
    validate_json,
)


ROOT = Path(__file__).resolve().parents[2]


def test_mcp_server_lists_expected_tools() -> None:
    server = create_server()

    async def run() -> dict:
        handler = server.request_handlers[types.ListToolsRequest]
        result = await handler(types.ListToolsRequest(method="tools/list"))
        return result.model_dump()

    payload = anyio.run(run)
    assert [tool["name"] for tool in payload["tools"]] == [
        "build_claim_graph",
        "parse_chart",
        "run_rules",
        "verify_chart",
        "build_arrow_claim_graph",
        "parse_arrow",
        "verify_arrow",
        "build_geometry_claim_graph",
        "parse_geometry",
        "verify_geometry",
    ]


def test_mcp_verify_chart_returns_schema_valid_payload(tmp_path: Path) -> None:
    dataset_root = tmp_path / "chart-v2"
    build_dataset(dataset_root)
    case = next(case for case in discover_cases(dataset_root) if case.case_id == "mutated-01")
    claim_schema = load_schema(ROOT / "specs" / "claim-graph.schema.json")
    evidence_schema = load_schema(ROOT / "specs" / "evidence-graph.schema.json")
    findings_schema = load_schema(ROOT / "specs" / "findings.schema.json")
    server = create_server()

    async def run() -> dict:
        handler = server.request_handlers[types.CallToolRequest]
        result = await handler(
            types.CallToolRequest(
                method="tools/call",
                params=types.CallToolRequestParams(
                    name="verify_chart",
                    arguments={
                        "image_path": str(case.image_path),
                        "spec_path": str(case.spec_path),
                        "metadata_path": str(case.metadata_path),
                    },
                ),
            )
        )
        return json.loads(result.model_dump()["content"][0]["text"])

    payload = anyio.run(run)
    assert validate_json(claim_schema, payload["claim_graph"]) == []
    assert validate_json(evidence_schema, payload["evidence_graph"]) == []
    assert validate_json(findings_schema, payload["report"]) == []
    assert payload["report"]["verdict"] == "fail"


def test_mcp_verify_arrow_returns_schema_valid_payload(tmp_path: Path) -> None:
    dataset_root = tmp_path / "arrow-v1"
    build_arrow_dataset(dataset_root)
    case = next(case for case in discover_arrow_cases(dataset_root) if case.case_id == "mutated-01")
    claim_schema = load_schema(ROOT / "specs" / "claim-graph.schema.json")
    evidence_schema = load_schema(ROOT / "specs" / "arrow-evidence-graph.schema.json")
    findings_schema = load_schema(ROOT / "specs" / "findings.schema.json")
    server = create_server()

    async def run() -> dict:
        handler = server.request_handlers[types.CallToolRequest]
        result = await handler(
            types.CallToolRequest(
                method="tools/call",
                params=types.CallToolRequestParams(
                    name="verify_arrow",
                    arguments={
                        "image_path": str(case.image_path),
                        "spec_path": str(case.spec_path),
                        "metadata_path": str(case.metadata_path),
                    },
                ),
            )
        )
        return json.loads(result.model_dump()["content"][0]["text"])

    payload = anyio.run(run)
    assert validate_json(claim_schema, payload["claim_graph"]) == []
    assert validate_json(evidence_schema, payload["evidence_graph"]) == []
    assert validate_json(findings_schema, payload["report"]) == []
    assert payload["report"]["verdict"] == "fail"


def test_mcp_verify_geometry_returns_schema_valid_payload(tmp_path: Path) -> None:
    dataset_root = tmp_path / "geometry-v1"
    build_geometry_dataset(dataset_root)
    case = next(
        case for case in discover_geometry_cases(dataset_root) if case.case_id == "mutated-03"
    )
    claim_schema = load_schema(ROOT / "specs" / "claim-graph.schema.json")
    evidence_schema = load_schema(ROOT / "specs" / "geometry-evidence-graph.schema.json")
    findings_schema = load_schema(ROOT / "specs" / "findings.schema.json")
    server = create_server()

    async def run() -> dict:
        handler = server.request_handlers[types.CallToolRequest]
        result = await handler(
            types.CallToolRequest(
                method="tools/call",
                params=types.CallToolRequestParams(
                    name="verify_geometry",
                    arguments={
                        "image_path": str(case.image_path),
                        "spec_path": str(case.spec_path),
                        "metadata_path": str(case.metadata_path),
                    },
                ),
            )
        )
        return json.loads(result.model_dump()["content"][0]["text"])

    payload = anyio.run(run)
    assert validate_json(claim_schema, payload["claim_graph"]) == []
    assert validate_json(evidence_schema, payload["evidence_graph"]) == []
    assert validate_json(findings_schema, payload["report"]) == []
    assert payload["report"]["verdict"] == "fail"
