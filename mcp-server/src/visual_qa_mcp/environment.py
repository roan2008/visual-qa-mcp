from __future__ import annotations

import importlib.metadata
import importlib.util
import shutil
import sys


def capture_ocr_environment() -> dict[str, object]:
    pytesseract_available = importlib.util.find_spec("pytesseract") is not None
    tesseract_path = shutil.which("tesseract")
    return {
        "pytesseract_available": pytesseract_available,
        "tesseract_binary_path": tesseract_path,
        "tesseract_available": tesseract_path is not None,
        "dependency_versions": {
            "python": sys.version.split()[0],
            "pytesseract": _safe_version("pytesseract"),
        },
    }


def capture_runtime_dependencies() -> dict[str, str]:
    return {
        "mcp": _safe_version("mcp"),
        "jsonschema": _safe_version("jsonschema"),
        "numpy": _safe_version("numpy"),
        "pillow": _safe_version("Pillow"),
    }


def _safe_version(package: str) -> str:
    try:
        return importlib.metadata.version(package)
    except importlib.metadata.PackageNotFoundError:
        return "unavailable"
