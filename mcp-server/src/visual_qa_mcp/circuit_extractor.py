"""Spec-blind extractor for the controlled circuit-v1a evidence family."""

from __future__ import annotations

from pathlib import Path

import numpy as np
from PIL import Image

from .contracts import (
    CircuitEvidenceGraph,
    EvidenceGap,
    ExtractedCircuitComponent,
    ExtractedCircuitJunction,
    ExtractedCircuitNet,
    ExtractionProvenance,
)
from .spatial import bbox_from_points, centroid_from_points, connected_components


MIN_SYMBOL_PIXELS = 80
WIRE_VALUE_MIN = 70
WIRE_VALUE_MAX = 140
WIRE_SPREAD_MAX = 12
TERMINAL_ATTACH_TOLERANCE_PX = 10.0

CIRCUIT_CHECK_IDS = [
    "component-count-matches",
    "required-components-present",
    "component-type-correct",
    "terminal-netlist-correct",
    "series-topology-correct",
    "junction-count-correct",
    "declared-topology-correct",
]


def _symbol_mask(pixels: np.ndarray) -> np.ndarray:
    channels = pixels.astype(np.int16)
    return (channels.max(axis=2) - channels.min(axis=2) >= 45) & (channels.max(axis=2) >= 130)


def _wire_mask(pixels: np.ndarray) -> np.ndarray:
    channels = pixels.astype(np.int16)
    spread = channels.max(axis=2) - channels.min(axis=2)
    value = channels.mean(axis=2)
    return (spread <= WIRE_SPREAD_MAX) & (value >= WIRE_VALUE_MIN) & (value <= WIRE_VALUE_MAX)


def _classify_symbol(pixel_count: int, bbox: list[int]) -> str | None:
    width = bbox[2] - bbox[0] + 1
    height = bbox[3] - bbox[1] + 1
    ratio = width / max(height, 1)
    if ratio >= 1.7:
        return "resistor"
    if ratio <= 0.62:
        return "battery" if width <= 26 else "resistor"
    fill_ratio = pixel_count / max(width * height, 1)
    if 0.75 <= ratio <= 1.35 and fill_ratio < 0.72:
        return "lamp"
    return None


def _terminals(symbol_type: str, center: tuple[float, float], bbox: list[int]) -> dict[str, tuple[float, float]]:
    x, y = center
    if symbol_type == "resistor":
        if bbox[3] - bbox[1] > bbox[2] - bbox[0]:
            return {"a": (x, y - 36), "b": (x, y + 36)}
        return {"a": (x - 36, y), "b": (x + 36, y)}
    if symbol_type == "battery":
        return {"a": (x, y - 33), "b": (x, y + 33)}
    return {"a": (x, y - 24), "b": (x, y + 24)}


def _point_distance_to_component(points_yx: np.ndarray, point_xy: tuple[float, float]) -> float:
    if len(points_yx) == 0:
        return float("inf")
    x, y = point_xy
    dx = points_yx[:, 1].astype(float) - x
    dy = points_yx[:, 0].astype(float) - y
    return float(np.sqrt(dx * dx + dy * dy).min())


def _junction_regions(points_yx: np.ndarray) -> list[np.ndarray]:
    """Find explicit thick junction dots; ordinary thin bends/T-lines stay below the density gate."""
    if len(points_yx) == 0:
        return []
    height = int(points_yx[:, 0].max()) + 8
    width = int(points_yx[:, 1].max()) + 8
    mask = np.zeros((height, width), dtype=np.uint8)
    mask[points_yx[:, 0], points_yx[:, 1]] = 1
    integral = np.pad(mask.astype(np.int64), ((1, 0), (1, 0))).cumsum(0).cumsum(1)
    radius = 7
    dense = np.zeros_like(mask, dtype=bool)
    for y, x in points_yx:
        y0, y1 = max(0, y - radius), min(height, y + radius + 1)
        x0, x1 = max(0, x - radius), min(width, x + radius + 1)
        support = integral[y1, x1] - integral[y0, x1] - integral[y1, x0] + integral[y0, x0]
        if support >= 140:
            dense[y, x] = True
    return [region for region in connected_components(dense) if len(region) >= 4]


def extract_circuit_evidence(image_path: Path) -> CircuitEvidenceGraph:
    """Extract v1a component-terminal-net evidence without reading a spec."""
    pixels = np.asarray(Image.open(image_path).convert("RGB"))
    gap_codes: list[str] = []
    components: list[ExtractedCircuitComponent] = []
    for points_yx in connected_components(_symbol_mask(pixels)):
        if len(points_yx) < MIN_SYMBOL_PIXELS:
            continue
        bbox = bbox_from_points(points_yx)
        symbol_type = _classify_symbol(len(points_yx), bbox)
        if symbol_type is None:
            gap_codes.append("unrecognized_symbol_geometry")
            continue
        center = centroid_from_points(points_yx)
        rgb = [int(round(v)) for v in pixels[points_yx[:, 0], points_yx[:, 1]].mean(axis=0)]
        terminals = _terminals(symbol_type, center, bbox)
        components.append(
            ExtractedCircuitComponent(
                component_id=f"component-{len(components) + 1:02d}",
                symbol_type=symbol_type,
                bbox=bbox,
                center_xy=[round(center[0], 1), round(center[1], 1)],
                rgb=rgb,
                pixel_count=len(points_yx),
                terminals={terminal_id: [round(x, 1), round(y, 1)] for terminal_id, (x, y) in terminals.items()},
                confidence=0.9,
            )
        )
    nets: list[ExtractedCircuitNet] = []
    junctions: list[ExtractedCircuitJunction] = []
    for points_yx in connected_components(_wire_mask(pixels)):
        if len(points_yx) < 12:
            continue
        attached = []
        for component in components:
            for terminal_id, terminal_xy in component.terminals.items():
                distance = _point_distance_to_component(points_yx, terminal_xy)
                if distance <= TERMINAL_ATTACH_TOLERANCE_PX:
                    attached.append(f"{component.component_id}.{terminal_id}")
        net_id = f"net-{len(nets) + 1:02d}"
        nets.append(
            ExtractedCircuitNet(
                net_id=net_id,
                pixel_count=len(points_yx),
                attached_terminals=attached,
                confidence=0.9 if len(attached) >= 2 else 0.4,
            )
        )
        for region in _junction_regions(points_yx):
            center = centroid_from_points(region)
            junctions.append(ExtractedCircuitJunction(
                junction_id=f"junction-{len(junctions) + 1:02d}", net_id=net_id,
                center_xy=[round(center[0], 1), round(center[1], 1)], bbox=bbox_from_points(region),
                pixel_support=len(region), confidence=0.9,
            ))
    # A recognizably missing or extra component is a complete contradiction for
    # the count/presence rules, not an extraction ambiguity. Unrecognized
    # geometry is separately recorded above and remains a review-only gap.
    all_attachments = [terminal for net in nets for terminal in net.attached_terminals]
    if not nets:
        gap_codes.append("missing_wire_evidence")
    if any(len(net.attached_terminals) < 2 for net in nets):
        gap_codes.append("unresolved_wire_attachment")
    if len(set(all_attachments)) != len(all_attachments):
        gap_codes.append("duplicate_terminal_attachment")
    if any(len(set(net.attached_terminals)) != len(net.attached_terminals) for net in nets):
        gap_codes.append("self_or_duplicate_net_attachment")

    gap_messages = {
        "unrecognized_symbol_geometry": "A colored component does not match the controlled circuit-v1a symbol catalog.",
        "ambiguous_or_missing_symbols": "The controlled three-component circuit family could not be completely resolved.",
        "missing_wire_evidence": "No wire-net evidence was extracted from the image.",
        "unresolved_wire_attachment": "At least one wire component does not attach to exactly two component terminals.",
        "incomplete_net_evidence": "The controlled series-loop net evidence is incomplete or contains an extra net.",
        "duplicate_terminal_attachment": "A component terminal is attached to more than one extracted net.",
        "self_or_duplicate_net_attachment": "A net repeats a terminal attachment and cannot represent a valid v1a wire net.",
    }
    gaps = [
        EvidenceGap(code=code, message=gap_messages[code], check_ids=list(CIRCUIT_CHECK_IDS))
        for code in sorted(set(gap_codes))
    ]
    confidence = 0.9 if not gaps else max(0.25, 0.9 - 0.15 * len(gaps))
    return CircuitEvidenceGraph(
        image_id=image_path.stem,
        diagram_type="circuit",
        components=components,
        nets=nets,
        junctions=junctions,
        extraction_confidence=round(confidence, 2),
        provenance=ExtractionProvenance(
            extractor_id="circuit-v1a",
            extractor_version="0.1.0",
            backend="component_and_wire_components",
            metadata_source="none",
        ),
        gaps=gaps,
        metadata={"image_path": str(image_path), "topology_family": "terminal_net_graph"},
    )


def extract_circuit_probe(image_path: Path) -> dict:
    """Compatibility adapter retained until feasibility cases become dataset tests."""
    evidence = extract_circuit_evidence(image_path)
    return {
        "symbols": [
            {
                "symbol_id": component.component_id,
                "symbol_type": component.symbol_type,
                "bbox": component.bbox,
                "center_xy": component.center_xy,
                "rgb": component.rgb,
                "terminals": component.terminals,
            }
            for component in evidence.components
        ],
        "nets": [
            {"net_id": net.net_id, "pixel_count": net.pixel_count, "attached_terminals": net.attached_terminals}
            for net in evidence.nets
        ],
        "gaps": [gap.code for gap in evidence.gaps],
    }
