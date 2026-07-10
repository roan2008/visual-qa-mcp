from __future__ import annotations

import math
from pathlib import Path
from typing import Any

import numpy as np
from PIL import Image

from .arrow_extractor import extract_arrow_evidence
from .chart_extractor import _find_bar_regions, _to_np, detect_plot_area
from .contracts import (
    ArrowEvidenceGraph,
    CoordinateEvidenceGraph,
    EvidenceGap,
    EvidenceGraph,
    ExtractionProvenance,
    GeometryEvidenceGraph,
    Primitive,
    PrimitiveEvidenceGraph,
    PrimitiveRelationship,
    PrimitiveSourceRef,
)
from .coordinate_extractor import extract_coordinate_evidence
from .geometry_extractor import extract_geometry_evidence
from .geometry_labels import dimension_label_box

SUPPORTED_PRIMITIVE_PROFILES = ("chart-v2", "arrow-v1", "geometry-v1", "coordinate-graph-v1")
RELATIONSHIP_TYPES = {
    "inside",
    "touches",
    "connected_to",
    "aligned_with",
    "parallel_to",
    "perpendicular_to",
    "above",
    "below",
    "left_of",
    "right_of",
    "approximately_equal",
}


def _bbox(values: list[int], width: int, height: int) -> dict[str, int]:
    left, top, right, bottom = (int(value) for value in values)
    return {
        "left": max(0, min(left, width - 1)),
        "top": max(0, min(top, height - 1)),
        "right": max(0, min(right, width - 1)),
        "bottom": max(0, min(bottom, height - 1)),
    }


def _coordinate_system(width: int, height: int) -> dict[str, Any]:
    return {
        "origin": "top_left",
        "x_direction": "right",
        "y_direction": "down",
        "unit": "pixel",
        "image_width": width,
        "image_height": height,
        "bbox_format": "left_top_right_bottom_inclusive",
    }


def _source(collection: str, object_id: str, graph: str = "domain_evidence") -> list[PrimitiveSourceRef]:
    return [PrimitiveSourceRef(graph=graph, collection=collection, object_id=object_id)]


def _adapter_provenance(profile: str, source_backend: str) -> ExtractionProvenance:
    return ExtractionProvenance(
        extractor_id="primitive-evidence-adapter",
        extractor_version="1.0.0",
        backend=f"{profile}:{source_backend}",
        metadata_source="domain_evidence_or_image_detection",
    )


def _deduplicate_gaps(gaps: list[EvidenceGap]) -> list[EvidenceGap]:
    seen: set[tuple[str, tuple[str, ...]]] = set()
    result: list[EvidenceGap] = []
    for gap in gaps:
        key = (gap.code, tuple(sorted(gap.check_ids)))
        if key not in seen:
            seen.add(key)
            result.append(gap)
    return result


def primitive_graph_from_geometry(
    evidence: GeometryEvidenceGraph,
    image_path: Path,
) -> PrimitiveEvidenceGraph:
    with Image.open(image_path) as image:
        width, height = image.size
    primitives: list[Primitive] = []
    relationships: list[PrimitiveRelationship] = []
    plate_id: str | None = None

    for region in evidence.regions:
        primitive_id = f"geometry.rectangle.{region.region_id}"
        bounds = _bbox(region.bbox, width, height)
        region.primitive_ids = [primitive_id]
        primitives.append(
            Primitive(
                primitive_id=primitive_id,
                type="rectangle",
                bbox=bounds,
                geometry={"bounds": bounds},
                confidence=region.confidence,
                attributes={"kind": region.kind, "pixel_count": region.pixel_count},
                source_refs=_source("regions", region.region_id),
            )
        )
        if region.kind == "plate":
            plate_id = primitive_id

    for hole in evidence.holes:
        circle_id = f"geometry.circle.{hole.hole_id}"
        circle_bounds = _bbox(hole.bbox, width, height)
        hole.primitive_ids = [circle_id]
        primitives.append(
            Primitive(
                primitive_id=circle_id,
                type="circle",
                bbox=circle_bounds,
                geometry={"center": list(hole.center_xy), "radius": hole.diameter_px / 2.0},
                confidence=hole.confidence,
                attributes={
                    "diameter_px": hole.diameter_px,
                    "circularity": hole.circularity,
                    "pixel_count": hole.pixel_count,
                },
                source_refs=_source("holes", hole.hole_id),
            )
        )
        if plate_id is not None:
            relationships.append(
                PrimitiveRelationship(
                    relationship_id=f"geometry.inside.{hole.hole_id}.plate",
                    type="inside",
                    source_primitive_id=circle_id,
                    target_primitive_id=plate_id,
                    confidence=min(hole.confidence, 0.95),
                    measurements={},
                )
            )
        if hole.label_text is not None:
            label_id = f"geometry.text.{hole.hole_id}"
            label_bounds = _bbox(
                dimension_label_box(tuple(hole.center_xy), hole.diameter_px / 2.0),
                width,
                height,
            )
            hole.primitive_ids.append(label_id)
            primitives.append(
                Primitive(
                    primitive_id=label_id,
                    type="text_region",
                    bbox=label_bounds,
                    geometry={"bounds": label_bounds},
                    confidence=hole.label_confidence,
                    attributes={"text": hole.label_text},
                    source_refs=_source("holes", hole.hole_id),
                )
            )
            relationships.append(
                PrimitiveRelationship(
                    relationship_id=f"geometry.connected_to.{hole.hole_id}.label",
                    type="connected_to",
                    source_primitive_id=label_id,
                    target_primitive_id=circle_id,
                    confidence=hole.label_confidence,
                    measurements={"role": "dimension_label"},
                )
            )

    for left, right in zip(evidence.holes, evidence.holes[1:]):
        deviation = abs(left.center_xy[1] - right.center_xy[1])
        if deviation <= 6:
            relationships.append(
                PrimitiveRelationship(
                    relationship_id=f"geometry.aligned.{left.hole_id}.{right.hole_id}",
                    type="aligned_with",
                    source_primitive_id=f"geometry.circle.{left.hole_id}",
                    target_primitive_id=f"geometry.circle.{right.hole_id}",
                    confidence=round(max(0.0, 1.0 - deviation / 7.0), 2),
                    measurements={"axis": "horizontal", "deviation_px": deviation},
                )
            )

    graph = PrimitiveEvidenceGraph(
        schema_version="1.0",
        image_id=evidence.image_id,
        profile="geometry-v1",
        coordinate_system=_coordinate_system(width, height),
        primitives=primitives,
        relationships=relationships,
        gaps=_deduplicate_gaps(list(evidence.gaps)),
        provenance=_adapter_provenance("geometry-v1", evidence.provenance.backend),
        metadata={"source_extractor": evidence.provenance.extractor_id},
    )
    _raise_if_invalid(graph)
    _raise_if_domain_links_invalid(evidence, graph)
    return graph


def primitive_graph_from_arrows(
    evidence: ArrowEvidenceGraph,
    image_path: Path,
) -> PrimitiveEvidenceGraph:
    with Image.open(image_path) as image:
        width, height = image.size
    primitives: list[Primitive] = []
    relationships: list[PrimitiveRelationship] = []

    region_ids: dict[str, str] = {}
    for region in evidence.regions:
        primitive_id = f"arrow.rectangle.{region.region_id}"
        bounds = _bbox(region.bbox, width, height)
        region.primitive_ids = [primitive_id]
        region_ids[region.region_id] = primitive_id
        primitives.append(
            Primitive(
                primitive_id=primitive_id,
                type="rectangle",
                bbox=bounds,
                geometry={"bounds": bounds},
                confidence=region.confidence,
                attributes={"kind": region.kind, "pixel_count": region.pixel_count},
                source_refs=_source("regions", region.region_id),
            )
        )

    object_region = evidence.regions[0] if evidence.regions else None
    for arrow in evidence.arrows:
        primitive_id = f"arrow.arrow.{arrow.arrow_id}"
        bounds = _bbox(arrow.bbox, width, height)
        arrow.primitive_ids = [primitive_id]
        primitives.append(
            Primitive(
                primitive_id=primitive_id,
                type="arrow",
                bbox=bounds,
                geometry={"tail": list(arrow.tail_xy), "head": list(arrow.head_xy)},
                confidence=arrow.confidence,
                attributes={
                    "rgb": list(arrow.rgb),
                    "angle_degrees": arrow.angle_degrees,
                    "length_px": arrow.length_px,
                },
                source_refs=_source("arrows", arrow.arrow_id),
            )
        )
        if arrow.label_text is not None:
            # The current domain evidence records decoded label semantics but not
            # its crop box, so the arrow primitive carries that semantic attribute.
            primitives[-1].attributes["label_text"] = arrow.label_text
            primitives[-1].attributes["label_confidence"] = arrow.label_confidence
        if object_region is not None:
            left, top, right, bottom = object_region.bbox
            tail_x, tail_y = arrow.tail_xy
            dx = max(left - tail_x, 0, tail_x - right)
            dy = max(top - tail_y, 0, tail_y - bottom)
            distance = math.hypot(dx, dy)
            if distance <= 14:
                relationships.append(
                    PrimitiveRelationship(
                        relationship_id=f"arrow.touches.{arrow.arrow_id}.{object_region.region_id}",
                        type="touches",
                        source_primitive_id=primitive_id,
                        target_primitive_id=region_ids[object_region.region_id],
                        confidence=round(max(0.0, 1.0 - distance / 15.0), 2),
                        measurements={"tail_distance_px": round(distance, 2)},
                    )
                )

    graph = PrimitiveEvidenceGraph(
        schema_version="1.0",
        image_id=evidence.image_id,
        profile="arrow-v1",
        coordinate_system=_coordinate_system(width, height),
        primitives=primitives,
        relationships=relationships,
        gaps=_deduplicate_gaps(list(evidence.gaps)),
        provenance=_adapter_provenance("arrow-v1", evidence.provenance.backend),
        metadata={"source_extractor": evidence.provenance.extractor_id},
    )
    _raise_if_invalid(graph)
    _raise_if_domain_links_invalid(evidence, graph)
    return graph


def primitive_graph_from_chart(
    evidence: EvidenceGraph,
    image_path: Path,
) -> PrimitiveEvidenceGraph:
    with Image.open(image_path) as image:
        width, height = image.size
    primitives: list[Primitive] = []
    relationships: list[PrimitiveRelationship] = []
    axis_id: str | None = None

    axis = evidence.y_axis
    if axis.axis_line_x is not None and axis.top_y is not None and axis.baseline_y is not None:
        axis_id = "chart.line.y-axis"
        bounds = _bbox([axis.axis_line_x, axis.top_y, axis.axis_line_x, axis.baseline_y], width, height)
        axis.primitive_ids = [axis_id]
        primitives.append(
            Primitive(
                primitive_id=axis_id,
                type="line",
                bbox=bounds,
                geometry={"start": [axis.axis_line_x, axis.top_y], "end": [axis.axis_line_x, axis.baseline_y]},
                confidence=axis.confidence,
                attributes={"role": "y_axis"},
                source_refs=_source("y_axis", "y-axis"),
            )
        )

    for bar in evidence.bars:
        primitive_id = f"chart.rectangle.{bar.bar_id}"
        bounds = _bbox(bar.bbox, width, height)
        bar.primitive_ids = [primitive_id]
        primitives.append(
            Primitive(
                primitive_id=primitive_id,
                type="rectangle",
                bbox=bounds,
                geometry={"bounds": bounds},
                confidence=bar.confidence,
                attributes={"category": bar.category, "value": bar.value, "role": "bar"},
                source_refs=_source("bars", bar.bar_id),
            )
        )
        if axis_id is not None:
            relationships.append(
                PrimitiveRelationship(
                    relationship_id=f"chart.right_of.{bar.bar_id}.y-axis",
                    type="right_of",
                    source_primitive_id=primitive_id,
                    target_primitive_id=axis_id,
                    confidence=min(bar.confidence, axis.confidence),
                    measurements={"horizontal_gap_px": max(0, bounds["left"] - axis.axis_line_x)},
                )
            )

    for index, tick in enumerate(axis.tick_labels, start=1):
        primitive_id = f"chart.text.tick-{index:02d}"
        bounds = _bbox(tick.bbox, width, height)
        tick.primitive_ids = [primitive_id]
        axis.primitive_ids.append(primitive_id)
        primitives.append(
            Primitive(
                primitive_id=primitive_id,
                type="text_region",
                bbox=bounds,
                geometry={"bounds": bounds},
                confidence=tick.confidence,
                attributes={"text": tick.text, "parsed_value": tick.parsed_value, "role": "tick_label"},
                source_refs=_source("y_axis.tick_labels", f"tick-{index:02d}"),
            )
        )

    graph = PrimitiveEvidenceGraph(
        schema_version="1.0",
        image_id=evidence.image_id,
        profile="chart-v2",
        coordinate_system=_coordinate_system(width, height),
        primitives=primitives,
        relationships=relationships,
        gaps=_deduplicate_gaps(list(evidence.gaps)),
        provenance=_adapter_provenance("chart-v2", evidence.provenance.backend),
        metadata={"source_extractor": evidence.provenance.extractor_id},
    )
    _raise_if_invalid(graph)
    _raise_if_domain_links_invalid(evidence, graph)
    return graph


def primitive_graph_from_coordinates(
    evidence: CoordinateEvidenceGraph,
    image_path: Path,
) -> PrimitiveEvidenceGraph:
    with Image.open(image_path) as image:
        width, height = image.size
    primitives: list[Primitive] = []
    relationships: list[PrimitiveRelationship] = []

    for axis_evidence in (evidence.x_axis, evidence.y_axis):
        readable_ticks = [tick for tick in axis_evidence.tick_labels if tick.parsed_value is not None]
        if axis_evidence.axis_pixel_position is None or len(readable_ticks) < 2:
            continue
        axis_id = f"coordinate.line.{axis_evidence.orientation}-axis"
        centers = sorted(
            int(round((tick.bbox[1] + tick.bbox[3]) / 2))
            if axis_evidence.orientation == "y"
            else int(round((tick.bbox[0] + tick.bbox[2]) / 2))
            for tick in readable_ticks
        )
        if axis_evidence.orientation == "y":
            start = [axis_evidence.axis_pixel_position, centers[0]]
            end = [axis_evidence.axis_pixel_position, centers[-1]]
        else:
            start = [centers[0], axis_evidence.axis_pixel_position]
            end = [centers[-1], axis_evidence.axis_pixel_position]
        bounds = _bbox([start[0], start[1], end[0], end[1]], width, height)
        axis_evidence.primitive_ids = [axis_id]
        primitives.append(
            Primitive(
                primitive_id=axis_id,
                type="line",
                bbox=bounds,
                geometry={"start": start, "end": end},
                confidence=axis_evidence.confidence,
                attributes={"role": f"{axis_evidence.orientation}_axis"},
                source_refs=_source(f"{axis_evidence.orientation}_axis", f"{axis_evidence.orientation}-axis"),
            )
        )

    point_primitive_ids: dict[str, str] = {}
    for point in evidence.points:
        primitive_id = f"coordinate.point.{point.point_id}"
        bounds = _bbox(point.bbox, width, height)
        point.primitive_ids = [primitive_id]
        point_primitive_ids[point.point_id] = primitive_id
        primitives.append(
            Primitive(
                primitive_id=primitive_id,
                type="point",
                bbox=bounds,
                geometry={"point": list(point.pixel_xy)},
                confidence=point.confidence,
                attributes={"rgb": list(point.rgb), "data_xy": point.data_xy},
                source_refs=_source("points", point.point_id),
            )
        )

    for edge in evidence.polyline_edges:
        first_id = point_primitive_ids.get(edge.from_point_id)
        second_id = point_primitive_ids.get(edge.to_point_id)
        if first_id is None or second_id is None:
            continue
        relationships.append(
            PrimitiveRelationship(
                relationship_id=f"coordinate.connected_to.{edge.from_point_id}.{edge.to_point_id}",
                type="connected_to",
                source_primitive_id=first_id,
                target_primitive_id=second_id,
                confidence=edge.coverage,
                measurements={"coverage": edge.coverage},
            )
        )

    graph = PrimitiveEvidenceGraph(
        schema_version="1.0",
        image_id=evidence.image_id,
        profile="coordinate-graph-v1",
        coordinate_system=_coordinate_system(width, height),
        primitives=primitives,
        relationships=relationships,
        gaps=_deduplicate_gaps(list(evidence.gaps)),
        provenance=_adapter_provenance("coordinate-graph-v1", evidence.provenance.backend),
        metadata={"source_extractor": evidence.provenance.extractor_id},
    )
    _raise_if_invalid(graph)
    _raise_if_domain_links_invalid(evidence, graph)
    return graph


def extract_primitive_evidence(image_path: Path, profile: str) -> PrimitiveEvidenceGraph:
    if profile not in SUPPORTED_PRIMITIVE_PROFILES:
        raise ValueError(
            f"Unsupported primitive profile '{profile}'. Expected one of: "
            + ", ".join(SUPPORTED_PRIMITIVE_PROFILES)
        )
    if profile == "geometry-v1":
        evidence = extract_geometry_evidence(image_path)
        return primitive_graph_from_geometry(evidence, image_path)
    if profile == "arrow-v1":
        evidence = extract_arrow_evidence(image_path)
        return primitive_graph_from_arrows(evidence, image_path)
    if profile == "coordinate-graph-v1":
        evidence = extract_coordinate_evidence(image_path)
        return primitive_graph_from_coordinates(evidence, image_path)
    return _extract_spec_blind_chart_primitives(image_path)


def _extract_spec_blind_chart_primitives(image_path: Path) -> PrimitiveEvidenceGraph:
    image = Image.open(image_path).convert("RGB")
    width, height = image.size
    rgb = _to_np(image)
    plot = detect_plot_area(rgb)
    axis_x = int(plot["axis_line_x"])
    plot_top = int(plot["plot_top"])
    plot_bottom = int(plot["plot_bottom"])
    primitives: list[Primitive] = []
    gaps: list[EvidenceGap] = []

    axis_id = "chart.line.y-axis"
    axis_bounds = _bbox([axis_x, plot_top, axis_x, plot_bottom], width, height)
    primitives.append(
        Primitive(
            primitive_id=axis_id,
            type="line",
            bbox=axis_bounds,
            geometry={"start": [axis_x, plot_top], "end": [axis_x, plot_bottom]},
            confidence=0.75,
            attributes={"role": "candidate_y_axis"},
            source_refs=_source("low_level", "candidate-y-axis", graph="image_detection"),
        )
    )
    for index, region in enumerate(_find_bar_regions(rgb, plot), start=1):
        bounds = _bbox(region, width, height)
        primitives.append(
            Primitive(
                primitive_id=f"chart.rectangle.candidate-bar-{index:02d}",
                type="rectangle",
                bbox=bounds,
                geometry={"bounds": bounds},
                confidence=0.75,
                attributes={"role": "candidate_bar"},
                source_refs=_source("low_level", f"candidate-bar-{index:02d}", graph="image_detection"),
            )
        )
    if len(plot.get("tick_rows", [])) < 2:
        gaps.append(
            EvidenceGap(
                code="chart_scale_semantics_unavailable",
                message="Spec-blind primitive extraction could not establish a readable chart scale.",
                check_ids=["axis-scale-readable", "axis-scale-monotonic", "chart-values-match-source"],
            )
        )
    graph = PrimitiveEvidenceGraph(
        schema_version="1.0",
        image_id=image_path.stem,
        profile="chart-v2",
        coordinate_system=_coordinate_system(width, height),
        primitives=primitives,
        relationships=[],
        gaps=gaps,
        provenance=_adapter_provenance("chart-v2", "spec_blind_low_level"),
        metadata={"image_path": str(image_path), "semantic_scope": "spec_blind_candidates"},
    )
    _raise_if_invalid(graph)
    return graph


def validate_primitive_graph_semantics(graph: PrimitiveEvidenceGraph) -> list[str]:
    errors: list[str] = []
    width = int(graph.coordinate_system["image_width"])
    height = int(graph.coordinate_system["image_height"])
    primitive_ids = [primitive.primitive_id for primitive in graph.primitives]
    relationship_ids = [relationship.relationship_id for relationship in graph.relationships]
    if len(primitive_ids) != len(set(primitive_ids)):
        errors.append("duplicate_primitive_id")
    if len(relationship_ids) != len(set(relationship_ids)):
        errors.append("duplicate_relationship_id")
    id_set = set(primitive_ids)
    for primitive in graph.primitives:
        box = primitive.bbox
        if box["left"] > box["right"] or box["top"] > box["bottom"]:
            errors.append(f"{primitive.primitive_id}:invalid_bbox_order")
        if box["right"] >= width or box["bottom"] >= height:
            errors.append(f"{primitive.primitive_id}:bbox_out_of_bounds")
        if not primitive.source_refs:
            errors.append(f"{primitive.primitive_id}:source_ref_missing")
        if not 0.0 <= primitive.confidence <= 1.0:
            errors.append(f"{primitive.primitive_id}:confidence_out_of_range")
        if not _finite(primitive.geometry) or not _finite(primitive.attributes):
            errors.append(f"{primitive.primitive_id}:non_finite_value")
        for x, y in _geometry_points(primitive):
            if not (0 <= x < width and 0 <= y < height):
                errors.append(f"{primitive.primitive_id}:geometry_out_of_bounds")
    for relationship in graph.relationships:
        if relationship.type not in RELATIONSHIP_TYPES:
            errors.append(f"{relationship.relationship_id}:unknown_relationship_type")
        if not 0.0 <= relationship.confidence <= 1.0:
            errors.append(f"{relationship.relationship_id}:confidence_out_of_range")
        if relationship.source_primitive_id not in id_set:
            errors.append(f"{relationship.relationship_id}:dangling_source")
        if relationship.target_primitive_id not in id_set:
            errors.append(f"{relationship.relationship_id}:dangling_target")
        for supporting_id in relationship.supporting_primitive_ids:
            if supporting_id not in id_set:
                errors.append(f"{relationship.relationship_id}:dangling_support")
        if relationship.type in {"aligned_with", "approximately_equal"} and not relationship.measurements:
            errors.append(f"{relationship.relationship_id}:measurements_required")
        if not _finite(relationship.measurements):
            errors.append(f"{relationship.relationship_id}:non_finite_value")
    return errors


def validate_domain_primitive_links(
    evidence: EvidenceGraph | ArrowEvidenceGraph | GeometryEvidenceGraph | CoordinateEvidenceGraph,
    graph: PrimitiveEvidenceGraph,
) -> list[str]:
    errors: list[str] = []
    primitive_ids = {primitive.primitive_id for primitive in graph.primitives}
    domain_objects: dict[tuple[str, str], list[str]] = {}

    if isinstance(evidence, GeometryEvidenceGraph):
        for item in evidence.holes:
            domain_objects[("holes", item.hole_id)] = item.primitive_ids
        for item in evidence.regions:
            domain_objects[("regions", item.region_id)] = item.primitive_ids
    elif isinstance(evidence, ArrowEvidenceGraph):
        for item in evidence.arrows:
            domain_objects[("arrows", item.arrow_id)] = item.primitive_ids
        for item in evidence.regions:
            domain_objects[("regions", item.region_id)] = item.primitive_ids
    elif isinstance(evidence, CoordinateEvidenceGraph):
        for item in evidence.points:
            domain_objects[("points", item.point_id)] = item.primitive_ids
        for axis_evidence in (evidence.x_axis, evidence.y_axis):
            if axis_evidence.primitive_ids:
                domain_objects[
                    (f"{axis_evidence.orientation}_axis", f"{axis_evidence.orientation}-axis")
                ] = axis_evidence.primitive_ids
    else:
        for item in evidence.bars:
            domain_objects[("bars", item.bar_id)] = item.primitive_ids
        if (
            evidence.y_axis.axis_line_x is not None
            and evidence.y_axis.top_y is not None
            and evidence.y_axis.baseline_y is not None
        ):
            domain_objects[("y_axis", "y-axis")] = evidence.y_axis.primitive_ids
        for index, tick in enumerate(evidence.y_axis.tick_labels, start=1):
            domain_objects[("y_axis.tick_labels", f"tick-{index:02d}")] = tick.primitive_ids

    for (collection, object_id), linked_ids in domain_objects.items():
        if not linked_ids:
            errors.append(f"{collection}:{object_id}:primitive_links_missing")
        for primitive_id in linked_ids:
            if primitive_id not in primitive_ids:
                errors.append(f"{collection}:{object_id}:dangling_primitive_link:{primitive_id}")

    for primitive in graph.primitives:
        for source_ref in primitive.source_refs:
            if source_ref.graph != "domain_evidence":
                continue
            key = (source_ref.collection, source_ref.object_id)
            if key not in domain_objects:
                errors.append(f"{primitive.primitive_id}:dangling_domain_source")
            elif primitive.primitive_id not in domain_objects[key]:
                errors.append(f"{primitive.primitive_id}:domain_source_not_reciprocal")
    return errors


def _finite(value: Any) -> bool:
    if isinstance(value, float):
        return math.isfinite(value)
    if isinstance(value, dict):
        return all(_finite(item) for item in value.values())
    if isinstance(value, (list, tuple)):
        return all(_finite(item) for item in value)
    return True


def _geometry_points(primitive: Primitive) -> list[tuple[float, float]]:
    geometry = primitive.geometry
    if primitive.type == "point":
        return [tuple(geometry["point"])]
    if primitive.type == "line":
        return [tuple(geometry["start"]), tuple(geometry["end"])]
    if primitive.type == "polyline":
        return [tuple(point) for point in geometry["points"]]
    if primitive.type == "arrow":
        return [tuple(geometry["tail"]), tuple(geometry["head"])]
    if primitive.type == "circle":
        return [tuple(geometry["center"])]
    bounds = geometry.get("bounds")
    if bounds is not None:
        return [
            (float(bounds["left"]), float(bounds["top"])),
            (float(bounds["right"]), float(bounds["bottom"])),
        ]
    return []


def _raise_if_invalid(graph: PrimitiveEvidenceGraph) -> None:
    errors = validate_primitive_graph_semantics(graph)
    if errors:
        raise ValueError(f"Primitive graph semantic validation failed: {errors}")


def _raise_if_domain_links_invalid(
    evidence: EvidenceGraph | ArrowEvidenceGraph | GeometryEvidenceGraph | CoordinateEvidenceGraph,
    graph: PrimitiveEvidenceGraph,
) -> None:
    errors = validate_domain_primitive_links(evidence, graph)
    if errors:
        raise ValueError(f"Domain primitive link validation failed: {errors}")
