from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import anyio
from mcp import types
from mcp.server import Server
from mcp.server.stdio import stdio_server

from .service import (
    build_arrow_claim_graph_from_spec,
    build_claim_graph_from_spec,
    build_coordinate_claim_graph_from_spec,
    build_flowchart_claim_graph_from_spec,
    build_geometry_claim_graph_from_spec,
    extract_arrow_evidence_from_inputs,
    extract_chart_evidence_from_inputs,
    extract_coordinate_evidence_from_inputs,
    extract_flowchart_evidence_from_inputs,
    extract_geometry_evidence_from_inputs,
    extract_primitive_evidence_from_inputs,
    run_arrow_verification,
    run_chart_rules_from_graphs,
    run_chart_verification,
    run_coordinate_verification,
    run_flowchart_verification,
    run_geometry_verification,
    write_verification_artifacts,
)


def create_server() -> Server:
    server = Server("visual-qa-mcp")

    @server.list_tools()
    async def list_tools() -> list[types.Tool]:
        return [
            types.Tool(
                name="parse_primitives",
                description="Extract a spec-blind PrimitiveEvidenceGraph using an explicit bounded profile.",
                inputSchema={
                    "type": "object",
                    "required": ["image_path", "profile"],
                    "properties": {
                        "image_path": {"type": "string"},
                        "profile": {
                            "type": "string",
                            "enum": ["chart-v2", "arrow-v1", "geometry-v1", "coordinate-graph-v1", "flowchart-v1"],
                        },
                    },
                },
            ),
            types.Tool(
                name="build_claim_graph",
                description="Build a chart-v2 ClaimGraph from a visual spec JSON file path.",
                inputSchema={
                    "type": "object",
                    "required": ["spec_path"],
                    "properties": {
                        "spec_path": {"type": "string"},
                    },
                },
            ),
            types.Tool(
                name="parse_chart",
                description="Extract chart-v2 evidence from an image path and visual spec path.",
                inputSchema={
                    "type": "object",
                    "required": ["image_path", "spec_path"],
                    "properties": {
                        "image_path": {"type": "string"},
                        "spec_path": {"type": "string"},
                        "metadata_path": {"type": "string"},
                        "backend": {"type": "string", "enum": ["template", "optional_ocr"]},
                    },
                },
            ),
            types.Tool(
                name="run_rules",
                description="Run chart-v2 rules from ClaimGraph and EvidenceGraph payloads or file paths.",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "claim_graph_path": {"type": "string"},
                        "evidence_graph_path": {"type": "string"},
                        "claim_graph": {"type": "object"},
                        "evidence_graph": {"type": "object"},
                    },
                },
            ),
            types.Tool(
                name="verify_chart",
                description="End-to-end chart-v2 verification from local inputs.",
                inputSchema={
                    "type": "object",
                    "required": ["image_path", "spec_path"],
                    "properties": {
                        "image_path": {"type": "string"},
                        "spec_path": {"type": "string"},
                        "metadata_path": {"type": "string"},
                        "backend": {"type": "string", "enum": ["template", "optional_ocr"]},
                        "output_dir": {"type": "string"},
                    },
                },
            ),
            types.Tool(
                name="build_arrow_claim_graph",
                description="Build an arrow-v1 ClaimGraph from a visual spec JSON file path.",
                inputSchema={
                    "type": "object",
                    "required": ["spec_path"],
                    "properties": {"spec_path": {"type": "string"}},
                },
            ),
            types.Tool(
                name="parse_arrow",
                description="Extract bounded arrow-v1 evidence from an image path.",
                inputSchema={
                    "type": "object",
                    "required": ["image_path"],
                    "properties": {"image_path": {"type": "string"}},
                },
            ),
            types.Tool(
                name="verify_arrow",
                description="End-to-end arrow-v1 verification from local inputs.",
                inputSchema={
                    "type": "object",
                    "required": ["image_path", "spec_path"],
                    "properties": {
                        "image_path": {"type": "string"},
                        "spec_path": {"type": "string"},
                        "metadata_path": {"type": "string"},
                        "output_dir": {"type": "string"},
                    },
                },
            ),
            types.Tool(
                name="build_geometry_claim_graph",
                description="Build a geometry-v1 ClaimGraph from a visual spec JSON file path.",
                inputSchema={
                    "type": "object",
                    "required": ["spec_path"],
                    "properties": {"spec_path": {"type": "string"}},
                },
            ),
            types.Tool(
                name="parse_geometry",
                description="Extract controlled geometry-v1 plate and hole evidence from an image path.",
                inputSchema={
                    "type": "object",
                    "required": ["image_path"],
                    "properties": {"image_path": {"type": "string"}},
                },
            ),
            types.Tool(
                name="verify_geometry",
                description="End-to-end controlled geometry-v1 verification from local inputs.",
                inputSchema={
                    "type": "object",
                    "required": ["image_path", "spec_path"],
                    "properties": {
                        "image_path": {"type": "string"},
                        "spec_path": {"type": "string"},
                        "metadata_path": {"type": "string"},
                        "output_dir": {"type": "string"},
                    },
                },
            ),
            types.Tool(
                name="build_coordinate_claim_graph",
                description="Build a coordinate-graph-v1 ClaimGraph from a visual spec JSON file path.",
                inputSchema={
                    "type": "object",
                    "required": ["spec_path"],
                    "properties": {"spec_path": {"type": "string"}},
                },
            ),
            types.Tool(
                name="parse_coordinate",
                description="Extract controlled coordinate-graph-v1 dual-axis, point, and polyline evidence from an image path.",
                inputSchema={
                    "type": "object",
                    "required": ["image_path"],
                    "properties": {"image_path": {"type": "string"}},
                },
            ),
            types.Tool(
                name="verify_coordinate",
                description="End-to-end controlled coordinate-graph-v1 verification from local inputs.",
                inputSchema={
                    "type": "object",
                    "required": ["image_path", "spec_path"],
                    "properties": {
                        "image_path": {"type": "string"},
                        "spec_path": {"type": "string"},
                        "metadata_path": {"type": "string"},
                        "output_dir": {"type": "string"},
                    },
                },
            ),
            types.Tool(
                name="build_flowchart_claim_graph",
                description="Build a flowchart-v1 ClaimGraph from a visual spec JSON file path.",
                inputSchema={
                    "type": "object",
                    "required": ["spec_path"],
                    "properties": {"spec_path": {"type": "string"}},
                },
            ),
            types.Tool(
                name="parse_flowchart",
                description="Extract controlled flowchart-v1 node and connector evidence from an image path.",
                inputSchema={
                    "type": "object",
                    "required": ["image_path"],
                    "properties": {"image_path": {"type": "string"}},
                },
            ),
            types.Tool(
                name="verify_flowchart",
                description="End-to-end controlled flowchart-v1 verification from local inputs.",
                inputSchema={
                    "type": "object",
                    "required": ["image_path", "spec_path"],
                    "properties": {
                        "image_path": {"type": "string"},
                        "spec_path": {"type": "string"},
                        "metadata_path": {"type": "string"},
                        "output_dir": {"type": "string"},
                    },
                },
            ),
        ]

    @server.call_tool()
    async def call_tool(name: str, arguments: dict[str, Any]) -> list[types.TextContent]:
        if name == "parse_primitives":
            graph = extract_primitive_evidence_from_inputs(
                Path(arguments["image_path"]),
                str(arguments["profile"]),
            )
            return [_json_content(graph.to_dict())]

        if name == "build_claim_graph":
            claim_graph = build_claim_graph_from_spec(Path(arguments["spec_path"]))
            return [_json_content(claim_graph.to_dict())]

        if name == "parse_chart":
            evidence_graph = extract_chart_evidence_from_inputs(
                image_path=Path(arguments["image_path"]),
                spec_path=Path(arguments["spec_path"]),
                metadata_path=Path(arguments["metadata_path"]) if arguments.get("metadata_path") else None,
                backend=arguments.get("backend"),
            )
            return [_json_content(evidence_graph.to_dict())]

        if name == "run_rules":
            claim_input = arguments.get("claim_graph") or arguments.get("claim_graph_path")
            evidence_input = arguments.get("evidence_graph") or arguments.get("evidence_graph_path")
            if claim_input is None or evidence_input is None:
                raise ValueError("run_rules requires claim_graph or claim_graph_path and evidence_graph or evidence_graph_path.")
            report = run_chart_rules_from_graphs(claim_input, evidence_input)
            return [_json_content(report.to_dict())]

        if name == "verify_chart":
            result = run_chart_verification(
                image_path=Path(arguments["image_path"]),
                spec_path=Path(arguments["spec_path"]),
                metadata_path=Path(arguments["metadata_path"]) if arguments.get("metadata_path") else None,
                backend=arguments.get("backend"),
            )
            payload = result.to_dict()
            if arguments.get("output_dir"):
                artifact_paths = write_verification_artifacts(result, Path(arguments["output_dir"]))
                payload["artifact_paths"] = artifact_paths.to_dict()
            return [_json_content(payload)]

        if name == "build_arrow_claim_graph":
            claim_graph = build_arrow_claim_graph_from_spec(Path(arguments["spec_path"]))
            return [_json_content(claim_graph.to_dict())]

        if name == "parse_arrow":
            evidence_graph = extract_arrow_evidence_from_inputs(Path(arguments["image_path"]))
            return [_json_content(evidence_graph.to_dict())]

        if name == "verify_arrow":
            result = run_arrow_verification(
                image_path=Path(arguments["image_path"]),
                spec_path=Path(arguments["spec_path"]),
                metadata_path=Path(arguments["metadata_path"])
                if arguments.get("metadata_path")
                else None,
            )
            payload = result.to_dict()
            if arguments.get("output_dir"):
                payload["artifact_paths"] = write_verification_artifacts(
                    result, Path(arguments["output_dir"])
                ).to_dict()
            return [_json_content(payload)]

        if name == "build_geometry_claim_graph":
            claim_graph = build_geometry_claim_graph_from_spec(Path(arguments["spec_path"]))
            return [_json_content(claim_graph.to_dict())]

        if name == "parse_geometry":
            evidence_graph = extract_geometry_evidence_from_inputs(Path(arguments["image_path"]))
            return [_json_content(evidence_graph.to_dict())]

        if name == "verify_geometry":
            result = run_geometry_verification(
                image_path=Path(arguments["image_path"]),
                spec_path=Path(arguments["spec_path"]),
                metadata_path=Path(arguments["metadata_path"])
                if arguments.get("metadata_path")
                else None,
            )
            payload = result.to_dict()
            if arguments.get("output_dir"):
                payload["artifact_paths"] = write_verification_artifacts(
                    result, Path(arguments["output_dir"])
                ).to_dict()
            return [_json_content(payload)]

        if name == "build_coordinate_claim_graph":
            claim_graph = build_coordinate_claim_graph_from_spec(Path(arguments["spec_path"]))
            return [_json_content(claim_graph.to_dict())]

        if name == "parse_coordinate":
            evidence_graph = extract_coordinate_evidence_from_inputs(Path(arguments["image_path"]))
            return [_json_content(evidence_graph.to_dict())]

        if name == "verify_coordinate":
            result = run_coordinate_verification(
                image_path=Path(arguments["image_path"]),
                spec_path=Path(arguments["spec_path"]),
                metadata_path=Path(arguments["metadata_path"])
                if arguments.get("metadata_path")
                else None,
            )
            payload = result.to_dict()
            if arguments.get("output_dir"):
                payload["artifact_paths"] = write_verification_artifacts(
                    result, Path(arguments["output_dir"])
                ).to_dict()
            return [_json_content(payload)]

        if name == "build_flowchart_claim_graph":
            claim_graph = build_flowchart_claim_graph_from_spec(Path(arguments["spec_path"]))
            return [_json_content(claim_graph.to_dict())]

        if name == "parse_flowchart":
            evidence_graph = extract_flowchart_evidence_from_inputs(Path(arguments["image_path"]))
            return [_json_content(evidence_graph.to_dict())]

        if name == "verify_flowchart":
            result = run_flowchart_verification(
                image_path=Path(arguments["image_path"]),
                spec_path=Path(arguments["spec_path"]),
                metadata_path=Path(arguments["metadata_path"])
                if arguments.get("metadata_path")
                else None,
            )
            payload = result.to_dict()
            if arguments.get("output_dir"):
                payload["artifact_paths"] = write_verification_artifacts(
                    result, Path(arguments["output_dir"])
                ).to_dict()
            return [_json_content(payload)]

        raise ValueError(f"Unknown tool: {name}")

    return server


async def run_stdio_server() -> None:
    server = create_server()
    async with stdio_server() as (read_stream, write_stream):
        await server.run(
            read_stream,
            write_stream,
            server.create_initialization_options(),
        )


def main() -> None:
    anyio.run(run_stdio_server)


def _json_content(payload: dict[str, Any]) -> types.TextContent:
    return types.TextContent(type="text", text=json.dumps(payload, indent=2))


if __name__ == "__main__":
    main()
