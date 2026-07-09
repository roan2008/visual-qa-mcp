from __future__ import annotations

import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "mcp-server" / "src"

os.environ.setdefault("PYTHONDONTWRITEBYTECODE", "1")
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))
