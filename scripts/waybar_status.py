#!/usr/bin/env python3
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
STATE_PATH = ROOT / "state" / "latest.json"
ARM_STATE_PATH = ROOT / "state" / "crop_armed.json"


def truncate(text: str, limit: int = 100) -> str:
    text = " ".join(text.split())
    if len(text) <= limit:
        return text
    return text[: limit - 1] + "…"


def emit(payload: dict) -> None:
    print(json.dumps(payload, ensure_ascii=False))


def main() -> int:
    if ARM_STATE_PATH.exists():
        turn_count = 0
        if STATE_PATH.exists():
            try:
                turn_count = int(
                    json.loads(STATE_PATH.read_text(encoding="utf-8")).get("turn_count", 0)
                )
            except (json.JSONDecodeError, ValueError, TypeError):
                turn_count = 0
        emit(
            {
                "text": f"{turn_count} ● crop",
                "tooltip": "Invisible crop armed. Move to the opposite corner and trigger again.",
                "class": "armed",
            }
        )
        return 0

    if not STATE_PATH.exists():
        emit(
            {
                "text": "0",
                "tooltip": "No answer yet",
                "class": "idle",
            }
        )
        return 0

    state = json.loads(STATE_PATH.read_text(encoding="utf-8"))
    status = state.get("status", "unknown")

    if status == "requesting":
        turn_count = state.get("turn_count", 0)
        emit(
            {
                "text": f"{turn_count} …",
                "tooltip": "Waiting for model response",
                "class": "loading",
            }
        )
        return 0

    if status == "error":
        turn_count = state.get("turn_count", 0)
        emit(
            {
                "text": f"{turn_count} err",
                "tooltip": state.get("error", "Unknown error"),
                "class": "error",
            }
        )
        return 0

    short_answer = state.get("short_answer", "AI")
    full_answer = state.get("full_answer", short_answer)
    confidence = state.get("confidence", "unknown")
    timestamp = state.get("timestamp", "")
    turn_count = state.get("turn_count", 0)

    emit(
        {
            "text": f"{turn_count} {truncate(short_answer)}",
            "tooltip": f"{full_answer}\nconfidence: {confidence}\n{timestamp}",
            "class": confidence if confidence in {"low", "medium", "high"} else "ok",
        }
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
