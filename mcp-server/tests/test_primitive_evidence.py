from __future__ import annotations

import math
from copy import deepcopy
from pathlib import Path

import pytest

from visual_qa_mcp.primitive_evidence import (
    extract_primitive_evidence,
    validate_domain_primitive_links,
    validate_primitive_graph_semantics,
)
from visual_qa_mcp.service import (
    run_arrow_verification,
    run_chart_verification,
    run_geometry_verification,
    write_verification_artifacts,
)
from visual_qa_mcp.validation import load_schema, validate_json


ROOT = Path(__file__).resolve().parents[2]
SAMPLES = {
    "chart-v2": ROOT / "datasets" / "charts" / "chart-v2" / "golden" / "golden-01" / "image.png",
    "arrow-v1": ROOT / "datasets" / "physics" / "arrow-v1" / "golden" / "golden-01" / "image.png",
    "geometry-v1": ROOT / "datasets" / "mechanical" / "geometry-v1" / "golden" / "golden-01" / "image.png",
}


@pytest.mark.parametrize("profile", sorted(SAMPLES))
def test_primitive_profiles_are_spec_blind_schema_valid_and_deterministic(profile: str) -> None:
    schema = load_schema(ROOT / "specs" / "primitive-evidence-graph.schema.json")
    first = extract_primitive_evidence(SAMPLES[profile], profile)
    second = extract_primitive_evidence(SAMPLES[profile], profile)
    assert first.to_dict() == second.to_dict()
    assert validate_json(schema, first.to_dict()) == []
    assert validate_primitive_graph_semantics(first) == []
    assert first.primitives


def test_primitive_semantic_validator_rejects_duplicate_dangling_and_invalid_data() -> None:
    graph = extract_primitive_evidence(SAMPLES["geometry-v1"], "geometry-v1")
    duplicate = deepcopy(graph.primitives[0])
    graph.primitives.append(duplicate)
    graph.relationships[0].target_primitive_id = "missing"
    graph.primitives[0].bbox["right"] = graph.coordinate_system["image_width"]
    graph.primitives[0].attributes["bad"] = math.inf
    graph.primitives[0].confidence = 1.5
    graph.primitives[0].geometry["bounds"]["right"] = graph.coordinate_system["image_width"]
    errors = validate_primitive_graph_semantics(graph)
    assert "duplicate_primitive_id" in errors
    assert any(item.endswith(":dangling_target") for item in errors)
    assert any(item.endswith(":bbox_out_of_bounds") for item in errors)
    assert any(item.endswith(":non_finite_value") for item in errors)
    assert any(item.endswith(":confidence_out_of_range") for item in errors)
    assert any(item.endswith(":geometry_out_of_bounds") for item in errors)


def test_unknown_primitive_profile_is_rejected() -> None:
    with pytest.raises(ValueError, match="Unsupported primitive profile"):
        extract_primitive_evidence(SAMPLES["geometry-v1"], "unknown")


def test_verification_writes_primitive_artifact_and_domain_links(tmp_path: Path) -> None:
    case_dir = ROOT / "datasets" / "mechanical" / "geometry-v1" / "golden" / "golden-01"
    result = run_geometry_verification(case_dir / "image.png", case_dir / "visual_spec.json")
    assert result.primitive_graph is not None
    assert all(hole.primitive_ids for hole in result.evidence_graph.holes)
    paths = write_verification_artifacts(result, tmp_path)
    assert paths.primitive_evidence_graph_path is not None
    assert paths.primitive_evidence_graph_path.exists()
    assert result.report.primitive_evidence_graph_path == str(paths.primitive_evidence_graph_path)


def test_cross_graph_links_resolve_for_all_domain_profiles() -> None:
    chart_dir = ROOT / "datasets" / "charts" / "chart-v2" / "golden" / "golden-01"
    arrow_dir = ROOT / "datasets" / "physics" / "arrow-v1" / "golden" / "golden-01"
    geometry_dir = ROOT / "datasets" / "mechanical" / "geometry-v1" / "golden" / "golden-01"
    results = [
        run_chart_verification(
            chart_dir / "image.png",
            chart_dir / "visual_spec.json",
            chart_dir / "metadata.json",
        ),
        run_arrow_verification(arrow_dir / "image.png", arrow_dir / "visual_spec.json"),
        run_geometry_verification(geometry_dir / "image.png", geometry_dir / "visual_spec.json"),
    ]
    for result in results:
        assert result.primitive_graph is not None
        assert validate_domain_primitive_links(result.evidence_graph, result.primitive_graph) == []

    results[0].evidence_graph.bars[0].primitive_ids = ["missing"]
    assert any(
        "dangling_primitive_link" in item
        for item in validate_domain_primitive_links(
            results[0].evidence_graph,
            results[0].primitive_graph,
        )
    )


def test_finding_traces_through_detected_domain_object_to_primitive() -> None:
    case_dir = ROOT / "datasets" / "mechanical" / "geometry-v1" / "mutated" / "mutated-03"
    result = run_geometry_verification(case_dir / "image.png", case_dir / "visual_spec.json")
    finding = next(
        item for item in result.report.findings if item.type == "hole_diameter_ratio_violation"
    )
    detected_id = finding.evidence["detected_hole_id"]
    domain_hole = next(item for item in result.evidence_graph.holes if item.hole_id == detected_id)
    graph_ids = {item.primitive_id for item in result.primitive_graph.primitives}
    assert domain_hole.primitive_ids
    assert set(domain_hole.primitive_ids).issubset(graph_ids)
