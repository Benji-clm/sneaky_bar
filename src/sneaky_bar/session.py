from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any


MAX_TURNS = 5


@dataclass
class SessionState:
    turn_count: int
    turns: list[dict[str, Any]]


def load_session(session_path: Path) -> SessionState:
    if not session_path.exists():
        return SessionState(turn_count=0, turns=[])

    try:
        raw = json.loads(session_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return SessionState(turn_count=0, turns=[])

    turns = raw.get("turns", [])
    if not isinstance(turns, list):
        turns = []

    turn_count = raw.get("turn_count", len(turns))
    if not isinstance(turn_count, int):
        turn_count = len(turns)

    return SessionState(turn_count=turn_count, turns=turns)


def save_session(session_path: Path, session: SessionState) -> None:
    session_path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "turn_count": session.turn_count,
        "turns": session.turns[-MAX_TURNS:],
    }
    session_path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


def reset_session(session_path: Path) -> None:
    save_session(session_path, SessionState(turn_count=0, turns=[]))


def append_turn(
    session: SessionState,
    *,
    question_summary: str,
    short_answer: str,
    full_answer: str,
    timestamp: str,
) -> SessionState:
    turns = session.turns + [
        {
            "question_summary": question_summary,
            "short_answer": short_answer,
            "full_answer": full_answer,
            "timestamp": timestamp,
        }
    ]
    return SessionState(turn_count=session.turn_count + 1, turns=turns[-MAX_TURNS:])


def build_context_text(session: SessionState) -> str:
    if not session.turns:
        return ""

    lines = [
        "Recent local context from previous screenshot queries.",
        "Use it only if it helps interpret the current screenshot.",
        "Always answer the current screenshot, not the previous one.",
    ]

    for idx, turn in enumerate(session.turns, start=1):
        question_summary = str(turn.get("question_summary", "")).strip()
        short_answer = str(turn.get("short_answer", "")).strip()
        full_answer = str(turn.get("full_answer", "")).strip()
        lines.append(
            f"Turn {idx}: question={question_summary or 'unknown'}; "
            f"answer={short_answer or full_answer or 'unknown'}; "
            f"detail={full_answer or short_answer or 'unknown'}"
        )

    return "\n".join(lines)
