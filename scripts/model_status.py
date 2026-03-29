#!/usr/bin/env python3
from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
MODEL_STATE_PATH = ROOT / "state" / "model_selection.json"


def main() -> int:
    if not MODEL_STATE_PATH.exists():
        print(json.dumps({"text": "M", "tooltip": "gpt-5.4"}))
        return 0

    try:
        state = json.loads(MODEL_STATE_PATH.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        print(json.dumps({"text": "M", "tooltip": "gpt-5.4"}))
        return 0

    indicator = state.get("indicator", "M")
    tooltip = state.get("tooltip") or state.get("model", "gpt-5.4")
    print(json.dumps({"text": indicator, "tooltip": tooltip}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
