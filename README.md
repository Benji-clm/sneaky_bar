# sneaky_bar

Hyprland utility for answering questions from screenshots with a multimodal LLM and showing the result in Waybar and optionally as a desktop notification.

## What It Does

`sneaky_bar` lets you bind a key to:

1. capture the full screen or a selected region
2. send the screenshot to an LLM
3. save the latest result to local JSON state
4. refresh Waybar
5. optionally show a notification

The project also keeps a short local session history so follow-up questions can reuse recent context without turning the whole tool into a chat UI.

## Current Model Profiles

The persistent model/profile selection is stored in `state/model_selection.json`.

- `M`: `gpt-5.4` via Chat Completions
- `S`: `gpt-5.4-mini` via Chat Completions
- `R`: `gpt-5.4` via Responses API with higher reasoning effort

One-off override is also supported:

- `-m gpt-5.4`
- `-m gpt-5.4-mini`

## Current Behavior

- Default capture mode is full screen.
- `crop` uses `slurp` for visible region selection.
- `ghostcrop` is a two-step invisible crop using the current cursor position.
- Waybar state is always updated.
- Notifications are opt-in with `notify`.
- Local session context is reused until you reset it.

## CLI

```bash
scripts/capture_and_answer.sh
scripts/capture_and_answer.sh crop
scripts/capture_and_answer.sh ghostcrop
scripts/capture_and_answer.sh notify
scripts/capture_and_answer.sh crop notify
scripts/capture_and_answer.sh ghostcrop notify
scripts/capture_and_answer.sh -m gpt-5.4-mini
scripts/capture_and_answer.sh --switch-model
scripts/capture_and_answer.sh --reset
```

## Flags

- `notify`: also show a desktop notification
- `-m MODEL`: one-off model override for `gpt-5.4` or `gpt-5.4-mini`
- `--switch-model`: cycle the persistent profile through `M`, `S`, and `R`
- `--reset` or `-r`: clear the saved session context and reset the displayed turn count

## Waybar Integration

The project exposes two Waybar-oriented helpers:

- [scripts/waybar_status.py](scripts/waybar_status.py): renders the latest answer state
- [scripts/model_status.py](scripts/model_status.py): renders the current model indicator (`M`, `S`, or `R`)

The answer display uses `state/latest.json`. The model indicator uses `state/model_selection.json`.

Current answer display behavior:

- the turn count is shown to the left of the answer text
- loading/error states are reflected in the emitted Waybar JSON
- clicking can copy the full answer if your Waybar config is wired to [scripts/copy_latest_answer.py](scripts/copy_latest_answer.py)

## Session Memory

Local session history is stored in `state/session.json`.

The app keeps the last 5 turns and feeds them back in as text context for future requests. The current screenshot is still the primary input; the saved session only exists to help with follow-up questions that depend on earlier context.

Resetting the session does not remove the persistent model selection.

## State Files

- `state/latest.json`: latest answer / UI state
- `state/session.json`: recent local context
- `state/model_selection.json`: current profile (`M`, `S`, `R`)
- `state/crop_armed.json`: temporary state for `ghostcrop`

## Environment

- `OPENAI_API_KEY`: primary API key source
- `SNEAKY_BAR_API_KEY`: optional override for `OPENAI_API_KEY`
- `SNEAKY_BAR_BASE_URL`: optional Chat Completions endpoint override
- `SNEAKY_BAR_RESPONSES_BASE_URL`: optional Responses endpoint override

## File Layout

- [scripts/capture_and_answer.sh](scripts/capture_and_answer.sh): shell entrypoint
- [src/sneaky_bar/main.py](src/sneaky_bar/main.py): orchestration, state, resets, profile switching
- [src/sneaky_bar/client.py](src/sneaky_bar/client.py): API request logic for Chat Completions and Responses
- [src/sneaky_bar/session.py](src/sneaky_bar/session.py): local turn memory
- [src/sneaky_bar/model_selection.py](src/sneaky_bar/model_selection.py): persistent profile state

## Notes

- `R` mode has the best reasoning path in this project, but it is expected to be slower than `M` and `S`.
- `ghostcrop` depends on `hyprctl`, `jq`, and `grim`.
- The project assumes a Wayland/Hyprland setup with `grim`, `slurp`, `wl-copy`, and `notify-send` available.
