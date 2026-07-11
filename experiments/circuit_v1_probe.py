"""Run the circuit-v1 feasibility gate without committing to a public API."""

from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "mcp-server" / "src"))

from visual_qa_mcp.circuit_extractor import extract_circuit_probe
from visual_qa_mcp.circuit_generator import component_terminals, render_circuit_probe


ROOT = Path(__file__).resolve().parents[1] / "experiments" / "_circuit_v1_probe"


def _components(symbol_mutation: str | None = None):
    return [
        {"id": "battery", "symbol_type": "battery", "rgb": [220, 50, 50], "center_px": [100, 190]},
        {"id": "resistor", "symbol_type": symbol_mutation or "resistor", "rgb": [45, 155, 65], "center_px": [260, 80]},
        {"id": "lamp", "symbol_type": "lamp", "rgb": [45, 90, 220], "center_px": [420, 190]},
    ]


def _nets(components, broken: bool = False, near_miss: bool = False, missing_all: bool = False, extra_fragment: bool = False, spurious_bridge: bool = False, duplicate_attachment: bool = False):
    ports = {component["id"]: component_terminals(component) for component in components}
    if missing_all:
        return []
    lower_left = (100, 300)
    lower_right = (420, 300)
    top_left = (100, 80)
    top_right = (420, 80)
    # A true near miss stays right of the lamp terminal and never traverses its
    # tolerance disk; it must not simply end beyond a vertical segment that
    # already passed through the terminal.
    lamp_top = ports["lamp"]["a"]
    nets = [
        {"points": [ports["battery"]["a"], top_left, ports["resistor"]["a"]]},
        {"points": [ports["resistor"]["b"], top_right, lamp_top]} if not near_miss else {"points": [ports["resistor"]["b"], top_right, (434, 80), (434, 142)]},
        {"points": [ports["lamp"]["b"], lower_right, lower_left, ports["battery"]["b"]]},
    ]
    if broken:
        # Replace the lower return net with two visibly separated wire fragments.
        nets.pop()
        nets.extend([
            {"points": [ports["lamp"]["b"], lower_right, (180, 300)]},
            {"points": [(150, 300), lower_left, ports["battery"]["b"]]},
        ])
    if extra_fragment:
        nets.append({"points": [(30, 340), (70, 340)]})
    if spurious_bridge:
        # A spurious route crosses the lower return path in this controlled
        # renderer. It is rejected as an unattached extra net; duplicate
        # terminal attachment is covered by its own separate case.
        nets.append({"points": [ports["battery"]["a"], (100, 250), (420, 250), ports["lamp"]["b"]]})
    if duplicate_attachment:
        # Thin and physically separate from the existing lead, but still inside
        # terminal attachment tolerance: tests duplicate evidence rather than
        # an obvious connected bridge.
        nets.append({"points": [(30, 153), (95, 153)], "width": 1})
    return nets


def main() -> None:
    ROOT.mkdir(parents=True, exist_ok=True)
    results = {}
    for name, kwargs in {
        "golden": {},
        "wrong_symbol": {"symbol_mutation": "lamp"},
        "broken_wire": {"broken": True},
        "near_miss": {"near_miss": True},
        "missing_all_wires": {"missing_all": True},
        "extra_fragment": {"extra_fragment": True},
        "spurious_bridge": {"spurious_bridge": True},
        "duplicate_attachment": {"duplicate_attachment": True},
        "unrecognized_symbol": {"symbol_mutation": "unknown"},
    }.items():
        # Keep routes anchored to the canonical resistor layout even when the
        # rendered glyph changes; this prevents mutation construction from
        # silently repairing topology.
        components = _components(kwargs.get("symbol_mutation"))
        canonical_components = _components()
        path = ROOT / f"{name}.png"
        render_circuit_probe(path, components, _nets(canonical_components, kwargs.get("broken", False), kwargs.get("near_miss", False), kwargs.get("missing_all", False), kwargs.get("extra_fragment", False), kwargs.get("spurious_bridge", False), kwargs.get("duplicate_attachment", False)))
        results[name] = extract_circuit_probe(path)
    assert len(results["golden"]["symbols"]) == 3 and len(results["golden"]["nets"]) == 3 and not results["golden"]["gaps"]
    assert results["wrong_symbol"]["symbols"][0]["symbol_type"] == "lamp"
    assert "unresolved_wire_attachment" in results["broken_wire"]["gaps"]
    assert "unresolved_wire_attachment" in results["near_miss"]["gaps"]
    assert "missing_wire_evidence" in results["missing_all_wires"]["gaps"]
    assert "incomplete_net_evidence" in results["extra_fragment"]["gaps"]
    assert "incomplete_net_evidence" in results["spurious_bridge"]["gaps"]
    assert "duplicate_terminal_attachment" in results["duplicate_attachment"]["gaps"]
    assert "unrecognized_symbol_geometry" in results["unrecognized_symbol"]["gaps"]
    print(json.dumps(results, indent=2))


if __name__ == "__main__":
    main()
