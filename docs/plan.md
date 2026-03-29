# Implementation Plan

## Milestone 1: Working End-to-End MVP

Target: one keybind, one screenshot, one answer, one notification.

Tasks:

1. Add shell entrypoint that:
   - creates a temp image path
   - captures the full screen by default with `grim`
   - supports crop mode via `slurp`
   - invokes Python app with the image path
2. Implement Python config loading:
   - `OPENAI_API_KEY` or `SNEAKY_BAR_API_KEY`
   - `SNEAKY_BAR_MODEL`
   - `SNEAKY_BAR_BASE_URL`
3. Implement model call with prompt + image
4. Parse structured JSON result
5. Write `state/latest.json`
6. Show `short_answer` through `notify-send`
7. Copy `full_answer` to clipboard

Definition of done:

- pressing the keybind produces a correct answer for a simple visible question

## Milestone 2: Harden Response Handling

Tasks:

1. Add timeout handling
2. Add clear error states to `state/latest.json`
3. Clamp `short_answer` length
4. Log raw model response for debugging
5. Add fallback parsing if the model returns extra text

Definition of done:

- failures are visible and recoverable instead of silent

## Milestone 3: Waybar Integration

Tasks:

1. Add a custom Waybar module that reads `state/latest.json`
2. Display:
   - loading state
   - error state
   - truncated short answer
3. Add click action to copy the full answer
4. Add refresh trigger after each request

Definition of done:

- the latest answer appears in Waybar without opening another window

## Milestone 4: Optional Overlay

Tasks:

1. Choose toolkit:
   - GTK with layer-shell
   - Qt with layer-shell
   - any lightweight Wayland-compatible layer surface
2. Build a top/bottom dock-like answer strip
3. Render short answer prominently and full answer on demand

Definition of done:

- you can show a persistent answer panel independent of Waybar

## Technical Decisions

Recommended language:

- Python for the orchestrator

Reasons:

- fast to prototype
- strong HTTP and JSON support
- simple subprocess integration with Hyprland tools

Recommended first display:

- notification + clipboard

Reasons:

- lowest complexity
- enough to validate the core loop

Recommended first backend:

- a hosted multimodal model with OpenAI-compatible API

Reasons:

- fastest path to a real result
- easy to swap later

## Risks

1. OCR quality may drop on dense or blurry screenshots.
2. Multiple-choice screenshots may need explicit prompt instructions.
3. Waybar is suitable for short text only.
4. Remote API use may leak sensitive screenshot contents.

## Next Build Step

Implement Milestone 1 completely before attempting Waybar or overlay work.
