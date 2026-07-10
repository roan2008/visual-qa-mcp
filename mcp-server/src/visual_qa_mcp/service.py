from __future__ import annotations

import json
from pathlib import Path

from .arrow_extractor import extract_arrow_evidence
from .arrow_rules import run_arrow_claims
from .claim_graph import (
    build_arrow_claim_graph,
    build_chart_claim_graph,
    build_coordinate_claim_graph,
    build_geometry_claim_graph,
)
from .chart_extractor import extract_chart_evidence
from .chart_rules import run_chart_claims
from .coordinate_extractor import extract_coordinate_evidence
from .coordinate_rules import run_coordinate_claims
from .geometry_extractor import extract_geometry_evidence
from .geometry_rules import run_geometry_claims
from .contracts import (
    ArrowEvidenceGraph,
    CoordinateEvidenceGraph,
    GeometryEvidenceGraph,
    ArtifactPaths,
    AxisMapping,
    ClaimCheck,
    ClaimGap,
    ClaimGraph,
    EvidenceGap,
    EvidenceGraph,
    ExtractedAxis,
    ExtractedBar,
    ExtractionProvenance,
    TickLabel,
    VerificationResult,
)
from .overlay import make_overlay
from .primitive_evidence import (
    extract_primitive_evidence,
    primitive_graph_from_arrows,
    primitive_graph_from_chart,
    primitive_graph_from_coordinates,
    primitive_graph_from_geometry,
)


def build_claim_graph_from_spec(spec_path: Path) -> ClaimGraph:
    return build_chart_claim_graph(spec_path)


def load_claim_graph(payload_or_path: dict | str | Path) -> ClaimGraph:
    payload = _load_payload(payload_or_path)
    return ClaimGraph(
        spec_id=payload["spec_id"],
        domain=payload["domain"],
        risk_level=payload["risk_level"],
        claims=[ClaimCheck(**claim) for claim in payload["claims"]],
        gaps=[ClaimGap(**gap) for gap in payload.get("gaps", [])],
        source_reference=payload.get("source_reference", {}),
        metadata=payload.get("metadata", {}),
    )


def load_evidence_graph(payload_or_path: dict | str | Path) -> EvidenceGraph:
    payload = _load_payload(payload_or_path)
    axis = payload["y_axis"]
    mapping = axis.get("mapping")
    return EvidenceGraph(
        image_id=payload["image_id"],
        chart_type=payload["chart_type"],
        bars=[ExtractedBar(**bar) for bar in payload["bars"]],
        x_axis_labels=payload["x_axis_labels"],
        y_axis=ExtractedAxis(
            label_text=axis["label_text"],
            unit_text=axis["unit_text"],
            label_bbox=axis["label_bbox"],
            confidence=axis["confidence"],
            tick_labels=[TickLabel(**tick) for tick in axis["tick_labels"]],
            axis_line_x=axis["axis_line_x"],
            baseline_y=axis["baseline_y"],
            top_y=axis["top_y"],
            zero_line_y=axis["zero_line_y"],
            mapping=AxisMapping(**mapping) if mapping is not None else None,
            backend=axis["backend"],
            primitive_ids=axis.get("primitive_ids", []),
        ),
        extraction_confidence=payload["extraction_confidence"],
        provenance=ExtractionProvenance(**payload["provenance"]),
        gaps=[EvidenceGap(**gap) for gap in payload.get("gaps", [])],
        metadata=payload.get("metadata", {}),
    )


def extract_chart_evidence_from_inputs(
    image_path: Path,
    spec_path: Path,
    metadata_path: Path | None = None,
    backend: str | None = None,
) -> EvidenceGraph:
    evidence = extract_chart_evidence(
        image_path=image_path,
        spec_path=spec_path,
        metadata_path=metadata_path,
        backend=backend,
    )
    primitive_graph_from_chart(evidence, image_path)
    return evidence


def extract_primitive_evidence_from_inputs(image_path: Path, profile: str):
    return extract_primitive_evidence(image_path, profile)


def run_chart_verification(
    image_path: Path,
    spec_path: Path,
    metadata_path: Path | None = None,
    backend: str | None = None,
) -> VerificationResult:
    claim_graph = build_claim_graph_from_spec(spec_path)
    evidence_graph = extract_chart_evidence_from_inputs(
        image_path=image_path,
        spec_path=spec_path,
        metadata_path=metadata_path,
        backend=backend,
    )
    report = run_chart_claims(claim_graph, evidence_graph)
    primitive_graph = primitive_graph_from_chart(evidence_graph, image_path)
    return VerificationResult(
        image_path=image_path,
        spec_path=spec_path,
        metadata_path=metadata_path,
        backend=backend or evidence_graph.y_axis.backend,
        claim_graph=claim_graph,
        evidence_graph=evidence_graph,
        report=report,
        primitive_graph=primitive_graph,
    )


def write_verification_artifacts(result: VerificationResult, output_dir: Path) -> ArtifactPaths:
    output_dir.mkdir(parents=True, exist_ok=True)
    paths = ArtifactPaths(
        output_dir=output_dir,
        overlay_path=output_dir / "overlay.png",
        evidence_graph_path=output_dir / "evidence_graph.json",
        claim_graph_path=output_dir / "claim_graph.json",
        report_path=output_dir / "report.json",
        primitive_evidence_graph_path=(
            output_dir / "primitive_evidence_graph.json"
            if result.primitive_graph is not None
            else None
        ),
    )

    make_overlay(result.image_path, result.report, paths.overlay_path)
    result.report.evidence_graph_path = str(paths.evidence_graph_path)
    result.report.claim_graph_path = str(paths.claim_graph_path)
    if paths.primitive_evidence_graph_path is not None:
        result.report.primitive_evidence_graph_path = str(paths.primitive_evidence_graph_path)
    paths.evidence_graph_path.write_text(
        json.dumps(result.evidence_graph.to_dict(), indent=2),
        encoding="utf-8",
    )
    paths.claim_graph_path.write_text(
        json.dumps(result.claim_graph.to_dict(), indent=2),
        encoding="utf-8",
    )
    if paths.primitive_evidence_graph_path is not None and result.primitive_graph is not None:
        paths.primitive_evidence_graph_path.write_text(
            json.dumps(result.primitive_graph.to_dict(), indent=2),
            encoding="utf-8",
        )
    paths.report_path.write_text(
        json.dumps(result.report.to_dict(), indent=2),
        encoding="utf-8",
    )
    return paths


def build_arrow_claim_graph_from_spec(spec_path: Path) -> ClaimGraph:
    return build_arrow_claim_graph(spec_path)


def extract_arrow_evidence_from_inputs(image_path: Path) -> ArrowEvidenceGraph:
    evidence = extract_arrow_evidence(image_path)
    primitive_graph_from_arrows(evidence, image_path)
    return evidence


def run_arrow_verification(
    image_path: Path,
    spec_path: Path,
    metadata_path: Path | None = None,
) -> VerificationResult:
    claim_graph = build_arrow_claim_graph(spec_path)
    evidence_graph = extract_arrow_evidence(image_path)
    report = run_arrow_claims(claim_graph, evidence_graph)
    primitive_graph = primitive_graph_from_arrows(evidence_graph, image_path)
    return VerificationResult(
        image_path=image_path,
        spec_path=spec_path,
        metadata_path=metadata_path,
        backend=evidence_graph.provenance.backend,
        claim_graph=claim_graph,
        evidence_graph=evidence_graph,
        report=report,
        primitive_graph=primitive_graph,
    )


def build_geometry_claim_graph_from_spec(spec_path: Path) -> ClaimGraph:
    return build_geometry_claim_graph(spec_path)


def extract_geometry_evidence_from_inputs(image_path: Path) -> GeometryEvidenceGraph:
    evidence = extract_geometry_evidence(image_path)
    primitive_graph_from_geometry(evidence, image_path)
    return evidence


def run_geometry_verification(
    image_path: Path,
    spec_path: Path,
    metadata_path: Path | None = None,
) -> VerificationResult:
    claim_graph = build_geometry_claim_graph(spec_path)
    evidence_graph = extract_geometry_evidence(image_path)
    report = run_geometry_claims(claim_graph, evidence_graph)
    primitive_graph = primitive_graph_from_geometry(evidence_graph, image_path)
    return VerificationResult(
        image_path=image_path,
        spec_path=spec_path,
        metadata_path=metadata_path,
        backend=evidence_graph.provenance.backend,
        claim_graph=claim_graph,
        evidence_graph=evidence_graph,
        report=report,
        primitive_graph=primitive_graph,
    )


def build_coordinate_claim_graph_from_spec(spec_path: Path) -> ClaimGraph:
    return build_coordinate_claim_graph(spec_path)


def extract_coordinate_evidence_from_inputs(image_path: Path) -> CoordinateEvidenceGraph:
    evidence = extract_coordinate_evidence(image_path)
    primitive_graph_from_coordinates(evidence, image_path)
    return evidence


def run_coordinate_verification(
    image_path: Path,
    spec_path: Path,
    metadata_path: Path | None = None,
) -> VerificationResult:
    claim_graph = build_coordinate_claim_graph(spec_path)
    evidence_graph = extract_coordinate_evidence(image_path)
    report = run_coordinate_claims(claim_graph, evidence_graph)
    primitive_graph = primitive_graph_from_coordinates(evidence_graph, image_path)
    return VerificationResult(
        image_path=image_path,
        spec_path=spec_path,
        metadata_path=metadata_path,
        backend=evidence_graph.provenance.backend,
        claim_graph=claim_graph,
        evidence_graph=evidence_graph,
        report=report,
        primitive_graph=primitive_graph,
    )


def run_chart_rules_from_graphs(
    claim_graph_input: dict | str | Path,
    evidence_graph_input: dict | str | Path,
):
    claim_graph = load_claim_graph(claim_graph_input)
    evidence_graph = load_evidence_graph(evidence_graph_input)
    return run_chart_claims(claim_graph, evidence_graph)


def _load_payload(payload_or_path: dict | str | Path) -> dict:
    if isinstance(payload_or_path, dict):
        return payload_or_path
    if isinstance(payload_or_path, Path):
        return json.loads(payload_or_path.read_text(encoding="utf-8"))
    return json.loads(Path(payload_or_path).read_text(encoding="utf-8"))
