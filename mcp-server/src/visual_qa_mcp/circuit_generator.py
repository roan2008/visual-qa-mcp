"""Controlled renderer used by the circuit-v1 feasibility gate.

This is deliberately not a general schematic renderer.  It makes a small,
inspectable family of orthogonal single-loop DC diagrams whose symbol pixels and
wire pixels are separable by construction.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from PIL import Image, ImageDraw


BACKGROUND = (255, 255, 255)
WIRE = (100, 100, 100)
DEFAULT_SIZE = (520, 380)


def component_terminals(component: dict[str, Any]) -> dict[str, tuple[int, int]]:
    """Return the two fixed, image-space ports for a controlled symbol."""
    x, y = component["center_px"]
    symbol_type = component["symbol_type"]
    if symbol_type == "resistor":
        if component.get("orientation") == "vertical":
            return {"a": (x, y - 36), "b": (x, y + 36)}
        return {"a": (x - 36, y), "b": (x + 36, y)}
    if symbol_type == "battery":
        return {"a": (x, y - 33), "b": (x, y + 33)}
    # Lamp is vertical in this first family.
    return {"a": (x, y - 24), "b": (x, y + 24)}


def _draw_component(draw: ImageDraw.ImageDraw, component: dict[str, Any]) -> None:
    x, y = component["center_px"]
    color = tuple(component["rgb"])
    symbol_type = component["symbol_type"]
    width = 6
    if symbol_type == "battery":
        # A connected H-shaped colored component; the unequal centre bars retain
        # the battery teaching glyph while remaining easy to segment.
        draw.line([(x - 9, y - 30), (x - 9, y + 30)], fill=color, width=width)
        draw.line([(x + 9, y - 20), (x + 9, y + 20)], fill=color, width=width)
        draw.line([(x - 9, y - 30), (x + 9, y - 20)], fill=color, width=width)
        draw.line([(x - 9, y + 30), (x + 9, y + 20)], fill=color, width=width)
    elif symbol_type == "resistor":
        if component.get("orientation") == "vertical":
            points = [(x, y - 34), (x - 13, y - 24), (x + 13, y - 12), (x - 13, y),
                      (x + 13, y + 12), (x - 13, y + 24), (x, y + 34)]
        else:
            points = [(x - 34, y), (x - 24, y - 13), (x - 12, y + 13), (x, y - 13),
                      (x + 12, y + 13), (x + 24, y - 13), (x + 34, y)]
        draw.line(points, fill=color, width=width, joint="curve")
    elif symbol_type == "lamp":
        draw.ellipse((x - 22, y - 22, x + 22, y + 22), outline=color, width=width)
        draw.line([(x - 14, y - 14), (x + 14, y + 14)], fill=color, width=width)
        draw.line([(x - 14, y + 14), (x + 14, y - 14)], fill=color, width=width)
    elif symbol_type == "unknown":
        # Deliberately outside the v1 catalog; used only by the ambiguity gate.
        draw.rectangle((x - 18, y - 18, x + 18, y + 18), fill=color)
    else:
        raise ValueError(f"Unsupported circuit-v1 symbol: {symbol_type}")


def render_circuit_probe(
    image_path: Path,
    components: list[dict[str, Any]],
    nets: list[dict[str, Any]],
    size: tuple[int, int] = DEFAULT_SIZE,
    junctions: list[tuple[int, int]] | None = None,
) -> None:
    """Render components and declared orthogonal wire paths.

    Each net has a ``points`` list.  Endpoints are required to coincide with a
    component terminal; this renderer does not infer or repair routes.
    """
    image = Image.new("RGB", size, BACKGROUND)
    draw = ImageDraw.Draw(image)
    for net in nets:
        draw.line([tuple(point) for point in net["points"]], fill=WIRE, width=net.get("width", 4), joint="curve")
    for x, y in junctions or []:
        draw.ellipse((x - 7, y - 7, x + 7, y + 7), fill=WIRE)
    for component in components:
        _draw_component(draw, component)
    image.save(image_path)
