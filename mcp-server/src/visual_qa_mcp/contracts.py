from __future__ import annotations

from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any


@dataclass
class TickLabel:
    text: str | None
    parsed_value: float | None
    bbox: list[int]
    confidence: float


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
    gaps: list[EvidenceGap] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class Finding:
    id: str
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
    overlay_path: str | None = None
    evidence_graph_path: str | None = None
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
        if self.overlay_path is not None:
            data["overlay_path"] = self.overlay_path
        if self.evidence_graph_path is not None:
            data["evidence_graph_path"] = self.evidence_graph_path
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
