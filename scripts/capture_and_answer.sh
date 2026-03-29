#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
TMP_DIR="${XDG_RUNTIME_DIR:-/tmp}/sneaky_bar"
mkdir -p "$TMP_DIR"

IMAGE_PATH="$TMP_DIR/capture-$(date +%s).png"
MODE="screen"
ENABLE_NOTIFY="0"
MODEL_OVERRIDE=""
ARM_STATE_PATH="$ROOT_DIR/state/crop_armed.json"
WAYBAR_SIGNAL="8"
RESET_ONLY="0"
SWITCH_MODEL_ONLY="0"

usage() {
  cat <<'EOF'
Usage: capture_and_answer.sh [screen|crop|ghostcrop|--screen|--crop|--ghostcrop] [notify|--notify] [-m MODEL] [--reset] [--switch-model]

Modes:
  screen   Capture the full screen/output layout (default)
  crop     Select a region interactively with slurp
  ghostcrop
           Invisible two-step crop using current cursor position

Options:
  notify   Also show a desktop notification
  -m MODEL
           Override the model for this request only
           Allowed: gpt-5.4, gpt-5.4-mini
  -r, --reset
           Reset local context and clear the latest state
  --switch-model
           Cycle the persistent default profile through M, S, and R

Waybar state is always updated on every run.
EOF
}

refresh_waybar() {
  pkill "-RTMIN+${WAYBAR_SIGNAL}" waybar 2>/dev/null || true
}

arm_ghostcrop() {
  mkdir -p "$(dirname "$ARM_STATE_PATH")"
  hyprctl -j cursorpos | jq '{x: (.x | floor), y: (.y | floor)}' > "$ARM_STATE_PATH"
  refresh_waybar
}

finish_ghostcrop() {
  local cursor_json start_x start_y end_x end_y left top width height

  cursor_json="$(hyprctl -j cursorpos)"
  start_x="$(jq -r '.x' "$ARM_STATE_PATH")"
  start_y="$(jq -r '.y' "$ARM_STATE_PATH")"
  end_x="$(printf '%s' "$cursor_json" | jq -r '.x | floor')"
  end_y="$(printf '%s' "$cursor_json" | jq -r '.y | floor')"

  if (( start_x < end_x )); then
    left="$start_x"
    width=$((end_x - start_x))
  else
    left="$end_x"
    width=$((start_x - end_x))
  fi

  if (( start_y < end_y )); then
    top="$start_y"
    height=$((end_y - start_y))
  else
    top="$end_y"
    height=$((start_y - end_y))
  fi

  rm -f "$ARM_STATE_PATH"
  refresh_waybar

  if (( width == 0 || height == 0 )); then
    notify-send -a "sneaky_bar" "sneaky_bar" "Ghost crop cancelled"
    exit 1
  fi

  grim -g "${left},${top} ${width}x${height}" "$IMAGE_PATH"
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    screen|--screen)
      MODE="screen"
      shift
      ;;
    crop|--crop)
      MODE="crop"
      shift
      ;;
    ghostcrop|--ghostcrop)
      MODE="ghostcrop"
      shift
      ;;
    notify|--notify)
      ENABLE_NOTIFY="1"
      shift
      ;;
    -m|--model)
      if [[ $# -lt 2 ]]; then
        notify-send -a "sneaky_bar" "sneaky_bar" "Missing value for $1"
        usage >&2
        exit 2
      fi
      if [[ "$2" != "gpt-5.4" && "$2" != "gpt-5.4-mini" ]]; then
        notify-send -a "sneaky_bar" "sneaky_bar" "Unsupported model: $2"
        usage >&2
        exit 2
      fi
      MODEL_OVERRIDE="$2"
      shift 2
      ;;
    -r|--reset)
      RESET_ONLY="1"
      shift
      ;;
    --switch-model)
      SWITCH_MODEL_ONLY="1"
      shift
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    *)
      notify-send -a "sneaky_bar" "sneaky_bar" "Unknown argument: $1"
      usage >&2
      exit 2
      ;;
  esac
done

if [[ "$SWITCH_MODEL_ONLY" == "1" ]]; then
  MAIN_ARGS=(--switch-model)
  if [[ "$ENABLE_NOTIFY" == "1" ]]; then
    MAIN_ARGS=(--notify "${MAIN_ARGS[@]}")
  fi
  PYTHONPATH="$ROOT_DIR/src" python3 -m sneaky_bar.main "${MAIN_ARGS[@]}"
  exit 0
fi

if [[ "$RESET_ONLY" == "1" ]]; then
  rm -f "$ARM_STATE_PATH"
  MAIN_ARGS=(--reset)
  if [[ "$ENABLE_NOTIFY" == "1" ]]; then
    MAIN_ARGS=(--notify "${MAIN_ARGS[@]}")
  fi
  if [[ -n "$MODEL_OVERRIDE" ]]; then
    MAIN_ARGS=(--model "$MODEL_OVERRIDE" "${MAIN_ARGS[@]}")
  fi
  PYTHONPATH="$ROOT_DIR/src" python3 -m sneaky_bar.main "${MAIN_ARGS[@]}"
  exit 0
fi

if [[ "$MODE" == "crop" ]]; then
  GEOMETRY="$(slurp)"

  if [[ -z "$GEOMETRY" ]]; then
    notify-send -a "sneaky_bar" "sneaky_bar" "Capture cancelled"
    exit 1
  fi

  grim -g "$GEOMETRY" "$IMAGE_PATH"
elif [[ "$MODE" == "ghostcrop" ]]; then
  if [[ -f "$ARM_STATE_PATH" ]]; then
    finish_ghostcrop
  else
    arm_ghostcrop
    exit 0
  fi
else
  grim "$IMAGE_PATH"
fi

MAIN_ARGS=("$IMAGE_PATH")
if [[ "$ENABLE_NOTIFY" == "1" ]]; then
  MAIN_ARGS=(--notify "${MAIN_ARGS[@]}")
fi
if [[ -n "$MODEL_OVERRIDE" ]]; then
  MAIN_ARGS=(--model "$MODEL_OVERRIDE" "${MAIN_ARGS[@]}")
fi

PYTHONPATH="$ROOT_DIR/src" python3 -m sneaky_bar.main "${MAIN_ARGS[@]}"
