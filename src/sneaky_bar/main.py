from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

from sneaky_bar.client import ClientError, load_config, request_answer
from sneaky_bar.model_selection import (
    load_selection,
    save_selection,
    toggle_selection,
)
from sneaky_bar.session import (
    append_turn,
    build_context_text,
    load_session,
    reset_session,
    save_session,
)


ROOT = Path(__file__).resolve().parents[2]
STATE_DIR = ROOT / "state"
STATE_PATH = STATE_DIR / "latest.json"
SESSION_PATH = STATE_DIR / "session.json"
MODEL_STATE_PATH = STATE_DIR / "model_selection.json"
WAYBAR_SIGNAL = "8"


def write_state(payload: dict) -> None:
    STATE_DIR.mkdir(parents=True, exist_ok=True)
    STATE_PATH.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


def notify(summary: str, body: str) -> None:
    subprocess.run(["notify-send", "-a", "sneaky_bar", summary, body], check=False)


def copy_to_clipboard(text: str) -> None:
    subprocess.run(["wl-copy"], input=text, text=True, check=False)


def refresh_waybar() -> None:
    subprocess.run(["pkill", f"-RTMIN+{WAYBAR_SIGNAL}", "waybar"], check=False)


def now_iso() -> str:
    return datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("image_path", nargs="?")
    parser.add_argument(
        "-m",
        "--model",
        choices=("gpt-5.4", "gpt-5.4-mini"),
        help="Override the model for this request",
    )
    parser.add_argument(
        "--notify",
        action="store_true",
        help="Also show a desktop notification after updating state/latest.json",
    )
    parser.add_argument(
        "-r",
        "--reset",
        action="store_true",
        help="Reset local conversation context and clear the latest state",
    )
    parser.add_argument(
        "--switch-model",
        action="store_true",
        help="Cycle the persistent default profile through M, S, and R",
    )
    return parser.parse_args(argv[1:])


def main(argv: list[str]) -> int:
    args = parse_args(argv)
    current_selection = load_selection(MODEL_STATE_PATH)
    save_selection(MODEL_STATE_PATH, current_selection)

    if args.switch_model:
        next_selection = toggle_selection(MODEL_STATE_PATH)
        write_state(
            {
                "status": "idle",
                "turn_count": load_session(SESSION_PATH).turn_count,
                "model": next_selection.model,
                "model_indicator": next_selection.indicator,
                "timestamp": now_iso(),
            }
        )
        refresh_waybar()
        if args.notify:
            notify("sneaky_bar", f"Model switched to {next_selection.model}")
        return 0

    if args.reset:
        reset_session(SESSION_PATH)
        selection = load_selection(MODEL_STATE_PATH)
        write_state(
            {
                "status": "idle",
                "turn_count": 0,
                "model": selection.model,
                "model_indicator": selection.indicator,
                "timestamp": now_iso(),
            }
        )
        refresh_waybar()
        if args.notify:
            notify("sneaky_bar", "Context reset")
        return 0

    if not args.image_path:
        print(
            "usage: python -m sneaky_bar.main [--reset] [--notify] [-m MODEL] [image_path]",
            file=sys.stderr,
        )
        return 2

    session = load_session(SESSION_PATH)
    resolved_model = args.model or current_selection.model
    resolved_api_mode = "chat" if args.model else current_selection.api_mode
    image_path = Path(args.image_path).resolve()
    write_state(
        {
            "status": "requesting",
            "question_source": str(image_path),
            "notify": args.notify,
            "model": resolved_model,
            "model_indicator": "M" if args.model == "gpt-5.4" else ("S" if args.model == "gpt-5.4-mini" else current_selection.indicator),
            "api_mode": resolved_api_mode,
            "turn_count": session.turn_count + 1,
            "timestamp": now_iso(),
        }
    )

    try:
        result = request_answer(
            load_config(resolved_model),
            image_path,
            build_context_text(session),
            resolved_api_mode,
        )
    except ClientError as exc:
        payload = {
            "status": "error",
            "question_source": str(image_path),
            "notify": args.notify,
            "model": resolved_model,
            "model_indicator": "M" if args.model == "gpt-5.4" else ("S" if args.model == "gpt-5.4-mini" else current_selection.indicator),
            "api_mode": resolved_api_mode,
            "turn_count": session.turn_count,
            "error": str(exc),
            "timestamp": now_iso(),
        }
        write_state(payload)
        if args.notify:
            notify("sneaky_bar error", str(exc))
        refresh_waybar()
        return 1

    timestamp = now_iso()
    updated_session = append_turn(
        session,
        question_summary=result["question_summary"],
        short_answer=result["short_answer"],
        full_answer=result["full_answer"],
        timestamp=timestamp,
    )
    save_session(SESSION_PATH, updated_session)

    payload = {
        "status": "ok",
        "question_source": str(image_path),
        "notify": args.notify,
        "model": resolved_model,
        "model_indicator": "M" if args.model == "gpt-5.4" else ("S" if args.model == "gpt-5.4-mini" else current_selection.indicator),
        "api_mode": resolved_api_mode,
        "turn_count": updated_session.turn_count,
        "question_summary": result["question_summary"],
        "short_answer": result["short_answer"],
        "full_answer": result["full_answer"],
        "confidence": result["confidence"],
        "timestamp": timestamp,
    }
    write_state(payload)
    copy_to_clipboard(payload["full_answer"])
    if args.notify:
        notify(payload["short_answer"], payload["full_answer"])
    refresh_waybar()
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
