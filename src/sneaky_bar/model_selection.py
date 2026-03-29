from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path


PROFILE_SEQUENCE = ["gpt-5.4", "gpt-5.4-mini", "gpt-5.4-reasoning"]
DEFAULT_PROFILE = "gpt-5.4"
PROFILES = {
    "gpt-5.4": {
        "model": "gpt-5.4",
        "indicator": "M",
        "api_mode": "chat",
        "tooltip": "gpt-5.4",
    },
    "gpt-5.4-mini": {
        "model": "gpt-5.4-mini",
        "indicator": "S",
        "api_mode": "chat",
        "tooltip": "gpt-5.4-mini",
    },
    "gpt-5.4-reasoning": {
        "model": "gpt-5.4",
        "indicator": "R",
        "api_mode": "responses",
        "tooltip": "gpt-5.4 reasoning",
    },
}


@dataclass
class ModelSelection:
    profile: str
    model: str
    indicator: str
    api_mode: str
    tooltip: str


def normalize_profile(profile: str | None) -> str:
    if profile in PROFILE_SEQUENCE:
        return profile
    return DEFAULT_PROFILE


def make_selection(profile: str | None) -> ModelSelection:
    normalized = normalize_profile(profile)
    definition = PROFILES[normalized]
    return ModelSelection(
        profile=normalized,
        model=definition["model"],
        indicator=definition["indicator"],
        api_mode=definition["api_mode"],
        tooltip=definition["tooltip"],
    )


def load_selection(path: Path) -> ModelSelection:
    if not path.exists():
        return make_selection(None)

    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return make_selection(None)

    return make_selection(raw.get("profile") or raw.get("model"))


def save_selection(path: Path, selection: ModelSelection) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "profile": selection.profile,
        "model": selection.model,
        "indicator": selection.indicator,
        "api_mode": selection.api_mode,
        "tooltip": selection.tooltip,
    }
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


def toggle_selection(path: Path) -> ModelSelection:
    current = load_selection(path)
    next_index = (PROFILE_SEQUENCE.index(current.profile) + 1) % len(PROFILE_SEQUENCE)
    selection = make_selection(PROFILE_SEQUENCE[next_index])
    save_selection(path, selection)
    return selection
