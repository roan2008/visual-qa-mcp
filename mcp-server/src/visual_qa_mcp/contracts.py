from __future__ import annotations

from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any


@dataclass
class ClaimCheck:
    claim_id: str
    rule_id: str
    check_id: str
    check_type: str
    severity: str
    target: str
    expected: dict[str, Any]
    tolerance: dict[str, Any] = field(default_factory=dict)
    evidence_requirements: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class ClaimGap:
    check_id: str
    code: str
    message: str
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class ClaimGraph:
    spec_id: str
    domain: str
    risk_level: str
    claims: list[ClaimCheck]
    gaps: list[ClaimGap] = field(default_factory=list)
    source_reference: dict[str, Any] = field(default_factory=dict)
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "spec_id": self.spec_id,
            "domain": self.domain,
            "risk_level": self.risk_level,
            "claims": [claim.to_dict() for claim in self.claims],
            "gaps": [gap.to_dict() for gap in self.gaps],
            "source_reference": self.source_reference,
            "metadata": self.metadata,
        }


@dataclass
class TickLabel:
    text: str | None
    parsed_value: float | None
    bbox: list[int]
    confidence: float
    primitive_ids: list[str] = field(default_factory=list)


@dataclass
class ExtractionProvenance:
    extractor_id: str
    extractor_version: str
    backend: str
    metadata_source: str
    dependency_versions: dict[str, str] = field(default_factory=dict)
    environment: dict[str, Any] = field(default_factory=dict)


@dataclass
class AxisMapping:
    min_value: float
    max_value: float
    pixels_per_unit: float
    scale_mode: str
    value_direction: str
    readable: bool


@dataclass
class ExtractedBar:
    bar_id: str
    category: str | None
    value: float | None
    bbox: list[int]
    confidence: float
    matched_label: str | None = None
    top_y: int | None = None
    bottom_y: int | None = None
    value_source: str = "axis_mapping"
    primitive_ids: list[str] = field(default_factory=list)


@dataclass
class ExtractedAxis:
    label_text: str | None
    unit_text: str | None
    label_bbox: list[int]
    confidence: float
    tick_labels: list[TickLabel] = field(default_factory=list)
    axis_line_x: int | None = None
    baseline_y: int | None = None
    top_y: int | None = None
    zero_line_y: int | None = None
    mapping: AxisMapping | None = None
    backend: str = "template"
    primitive_ids: list[str] = field(default_factory=list)


@dataclass
class EvidenceGap:
    code: str
    message: str
    check_ids: list[str]


@dataclass
class EvidenceGraph:
    image_id: str
    chart_type: str
    bars: list[ExtractedBar]
    x_axis_labels: list[str | None]
    y_axis: ExtractedAxis
    extraction_confidence: float
    provenance: ExtractionProvenance
    gaps: list[EvidenceGap] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class BarGeometryDelta:
    bar_id: str
    original_bbox: list[int]
    round_trip_bbox: list[int] | None
    top_y_delta_px: float | None
    bottom_y_delta_px: float | None
    height_delta_px: float | None
    width_delta_px: float | None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class RoundTripComparison:
    status: str
    bar_deltas: list[BarGeometryDelta] = field(default_factory=list)
    max_top_y_delta_px: float | None = None
    mean_top_y_delta_px: float | None = None
    max_height_delta_px: float | None = None
    mean_height_delta_px: float | None = None
    round_trip_image_path: str | None = None
    notes: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class ExtractedArrow:
    arrow_id: str
    rgb: list[int]
    bbox: list[int]
    tail_xy: list[int]
    head_xy: list[int]
    angle_degrees: float
    length_px: float
    tail_spread_px: float
    head_spread_px: float
    confidence: float
    label_text: str | None = None
    label_confidence: float = 0.0
    primitive_ids: list[str] = field(default_factory=list)


@dataclass
class ExtractedRegion:
    region_id: str
    kind: str
    bbox: list[int]
    pixel_count: int
    confidence: float
    primitive_ids: list[str] = field(default_factory=list)


@dataclass
class ArrowEvidenceGraph:
    image_id: str
    diagram_type: str
    arrows: list[ExtractedArrow]
    regions: list[ExtractedRegion]
    extraction_confidence: float
    provenance: ExtractionProvenance
    gaps: list[EvidenceGap] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class ExtractedHole:
    hole_id: str
    center_xy: list[int]
    diameter_px: float
    circularity: float
    bbox: list[int]
    pixel_count: int
    confidence: float
    label_text: str | None = None
    label_confidence: float = 0.0
    primitive_ids: list[str] = field(default_factory=list)


@dataclass
class PrimitiveSourceRef:
    graph: str
    collection: str
    object_id: str


@dataclass
class Primitive:
    primitive_id: str
    type: str
    bbox: dict[str, int]
    geometry: dict[str, Any]
    confidence: float
    attributes: dict[str, Any] = field(default_factory=dict)
    source_refs: list[PrimitiveSourceRef] = field(default_factory=list)


@dataclass
class PrimitiveRelationship:
    relationship_id: str
    type: str
    source_primitive_id: str
    target_primitive_id: str
    confidence: float
    measurements: dict[str, Any] = field(default_factory=dict)
    supporting_primitive_ids: list[str] = field(default_factory=list)


@dataclass
class PrimitiveEvidenceGraph:
    schema_version: str
    image_id: str
    profile: str
    coordinate_system: dict[str, Any]
    primitives: list[Primitive]
    relationships: list[PrimitiveRelationship]
    gaps: list[EvidenceGap]
    provenance: ExtractionProvenance
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class GeometryEvidenceGraph:
    image_id: str
    diagram_type: str
    holes: list[ExtractedHole]
    regions: list[ExtractedRegion]
    extraction_confidence: float
    provenance: ExtractionProvenance
    gaps: list[EvidenceGap] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class ExtractedCoordinateAxis:
    orientation: str
    tick_labels: list[TickLabel]
    axis_pixel_position: int | None
    reference_pixel: int | None
    fit_slope: float | None
    fit_intercept: float | None
    mapping: AxisMapping | None
    confidence: float
    backend: str = "template"
    primitive_ids: list[str] = field(default_factory=list)


@dataclass
class ExtractedPoint:
    point_id: str
    rgb: list[int]
    pixel_xy: list[int]
    data_xy: list[float] | None
    bbox: list[int]
    pixel_count: int
    confidence: float
    label_text: str | None = None
    label_confidence: float = 0.0
    primitive_ids: list[str] = field(default_factory=list)


@dataclass
class DetectedPolylineEdge:
    from_point_id: str
    to_point_id: str
    coverage: float


@dataclass
class CoordinateEvidenceGraph:
    image_id: str
    diagram_type: str
    x_axis: ExtractedCoordinateAxis
    y_axis: ExtractedCoordinateAxis
    points: list[ExtractedPoint]
    polyline_edges: list[DetectedPolylineEdge]
    extraction_confidence: float
    provenance: ExtractionProvenance
    gaps: list[EvidenceGap] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class ExtractedNode:
    node_id: str
    shape: str
    rgb: list[int]
    bbox: list[int]
    center_xy: list[int]
    pixel_count: int
    fill_ratio: float
    confidence: float
    label_text: str | None = None
    label_confidence: float = 0.0
    primitive_ids: list[str] = field(default_factory=list)


@dataclass
class ExtractedConnector:
    connector_id: str
    tail_xy: list[int]
    head_xy: list[int]
    from_node_id: str | None
    to_node_id: str | None
    length_px: float
    confidence: float
    primitive_ids: list[str] = field(default_factory=list)


@dataclass
class FlowchartEvidenceGraph:
    image_id: str
    diagram_type: str
    nodes: list[ExtractedNode]
    connectors: list[ExtractedConnector]
    extraction_confidence: float
    provenance: ExtractionProvenance
    gaps: list[EvidenceGap] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class FlowchartDatasetCase:
    case_id: str
    title: str
    kind: str
    defect_type: str | None
    scenario: str
    image_path: Path
    spec_path: Path
    metadata_path: Path
    expected_report_path: Path
    dataset_track: str = "controlled"


@dataclass
class Finding:
    id: str
    rule_id: str
    type: str
    severity: str
    message: str
    evidence: dict[str, Any]
    recommendation: str | None = None

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        if self.recommendation is None:
            data.pop("recommendation")
        return data


@dataclass
class OverlayAnnotation:
    finding_id: str
    kind: str
    bbox: list[int]
    label: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class VisualQaReport:
    image_id: str
    spec_id: str
    verdict: str
    findings: list[Finding]
    checks_run: list[str]
    checks_skipped: list[dict[str, str]]
    confidence: float | None = None
    extraction_confidence: float | None = None
    rule_confidence: float | None = None
    overlay_path: str | None = None
    evidence_graph_path: str | None = None
    claim_graph_path: str | None = None
    primitive_evidence_graph_path: str | None = None
    overlay_annotations: list[OverlayAnnotation] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        data: dict[str, Any] = {
            "image_id": self.image_id,
            "spec_id": self.spec_id,
            "verdict": self.verdict,
            "findings": [finding.to_dict() for finding in self.findings],
            "checks_run": self.checks_run,
            "checks_skipped": self.checks_skipped,
        }
        if self.confidence is not None:
            data["confidence"] = self.confidence
        if self.extraction_confidence is not None:
            data["extraction_confidence"] = self.extraction_confidence
        if self.rule_confidence is not None:
            data["rule_confidence"] = self.rule_confidence
        if self.overlay_path is not None:
            data["overlay_path"] = self.overlay_path
        if self.evidence_graph_path is not None:
            data["evidence_graph_path"] = self.evidence_graph_path
        if self.claim_graph_path is not None:
            data["claim_graph_path"] = self.claim_graph_path
        if self.primitive_evidence_graph_path is not None:
            data["primitive_evidence_graph_path"] = self.primitive_evidence_graph_path
        if self.overlay_annotations:
            data["overlay_annotations"] = [
                annotation.to_dict() for annotation in self.overlay_annotations
            ]
        return data


@dataclass
class ChartDatasetCase:
    case_id: str
    title: str
    kind: str
    defect_type: str | None
    axis_mode: str
    backend: str
    image_path: Path
    spec_path: Path
    metadata_path: Path
    expected_report_path: Path
    dataset_track: str = "controlled"


@dataclass
class ArrowDatasetCase:
    case_id: str
    title: str
    kind: str
    defect_type: str | None
    scenario: str
    image_path: Path
    spec_path: Path
    metadata_path: Path
    expected_report_path: Path
    dataset_track: str = "controlled"


@dataclass
class GeometryDatasetCase:
    case_id: str
    title: str
    kind: str
    defect_type: str | None
    scenario: str
    image_path: Path
    spec_path: Path
    metadata_path: Path
    expected_report_path: Path
    dataset_track: str = "controlled"
    transform_family: str = "controlled"


@dataclass
class CoordinateDatasetCase:
    case_id: str
    title: str
    kind: str
    defect_type: str | None
    scenario: str
    image_path: Path
    spec_path: Path
    metadata_path: Path
    expected_report_path: Path
    dataset_track: str = "controlled"


@dataclass
class ArtifactPaths:
    output_dir: Path
    overlay_path: Path
    evidence_graph_path: Path
    claim_graph_path: Path
    report_path: Path
    primitive_evidence_graph_path: Path | None = None
    round_trip_path: Path | None = None
    round_trip_image_path: Path | None = None

    def to_dict(self) -> dict[str, str]:
        return {
            "output_dir": str(self.output_dir),
            "overlay_path": str(self.overlay_path),
            "evidence_graph_path": str(self.evidence_graph_path),
            "claim_graph_path": str(self.claim_graph_path),
            "report_path": str(self.report_path),
            **(
                {"primitive_evidence_graph_path": str(self.primitive_evidence_graph_path)}
                if self.primitive_evidence_graph_path is not None
                else {}
            ),
            **(
                {"round_trip_path": str(self.round_trip_path)}
                if self.round_trip_path is not None
                else {}
            ),
            **(
                {"round_trip_image_path": str(self.round_trip_image_path)}
                if self.round_trip_image_path is not None
                else {}
            ),
        }


@dataclass
class VerificationResult:
    image_path: Path
    spec_path: Path
    metadata_path: Path | None
    backend: str
    claim_graph: ClaimGraph
    evidence_graph: (
        EvidenceGraph
        | ArrowEvidenceGraph
        | GeometryEvidenceGraph
        | CoordinateEvidenceGraph
        | FlowchartEvidenceGraph
    )
    report: VisualQaReport
    primitive_graph: PrimitiveEvidenceGraph | None = None
    round_trip: RoundTripComparison | None = None

    def to_dict(self) -> dict[str, Any]:
        payload = {
            "image_path": str(self.image_path),
            "spec_path": str(self.spec_path),
            "metadata_path": str(self.metadata_path) if self.metadata_path is not None else None,
            "backend": self.backend,
            "claim_graph": self.claim_graph.to_dict(),
            "evidence_graph": self.evidence_graph.to_dict(),
            "report": self.report.to_dict(),
        }
        if self.primitive_graph is not None:
            payload["primitive_graph"] = self.primitive_graph.to_dict()
        if self.round_trip is not None:
            payload["round_trip"] = self.round_trip.to_dict()
        return payload
