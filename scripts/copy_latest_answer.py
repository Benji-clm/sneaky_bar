#!/usr/bin/env python3
from __future__ import annotations

import json
import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
STATE_PATH = ROOT / "state" / "latest.json"


def main() -> int:
    if not STATE_PATH.exists():
        return 1

    state = json.loads(STATE_PATH.read_text(encoding="utf-8"))
    text = state.get("full_answer") or state.get("short_answer")
    if not text:
        return 1

    subprocess.run(["wl-copy"], input=text, text=True, check=False)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
