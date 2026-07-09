from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageDraw

from .contracts import VisualQaReport


def make_overlay(image_path: Path, report: VisualQaReport, output_path: Path) -> Path:
    image = Image.open(image_path).convert("RGB")
    draw = ImageDraw.Draw(image)
    for annotation in report.overlay_annotations:
        draw.rectangle(annotation.bbox, outline=(214, 48, 49), width=3)
        label_y = max(0, annotation.bbox[1] - 18)
        draw.rectangle(
            [annotation.bbox[0], label_y, annotation.bbox[0] + 180, label_y + 16],
            fill=(255, 244, 244),
            outline=(214, 48, 49),
        )
        draw.text((annotation.bbox[0] + 4, label_y + 2), annotation.label, fill=(120, 0, 0))
    output_path.parent.mkdir(parents=True, exist_ok=True)
    image.save(output_path)
    report.overlay_path = str(output_path)
    return output_path
