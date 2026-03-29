# Architecture

## Problem

You want to answer questions visible in the browser with one keybind and show the result in a compact, non-intrusive UI on Hyprland.

## MVP Decision

Use a file-backed pipeline.

```text
Hyprland keybind
  -> capture script
  -> screenshot file
  -> Python app
  -> multimodal LLM API
  -> state/latest.json
  -> notification / Waybar / overlay
```

This is the simplest design that stays debuggable and extensible.

## Components

### 1. Capture

Tools already available on your machine:

- `grim` for screenshots
- `slurp` for optional region selection

Why full-screen default plus optional crop:

- full-screen is the fastest UX when you want one keypress
- crop is safer and often more accurate when the screen is busy
- both modes should exist because they optimize for different use cases

### 2. Orchestrator

A small Python program should:

- read config from environment variables
- base64-encode the screenshot
- send text + image to the model
- parse a structured JSON response
- write the latest result to disk

### 3. Model Interface

Required capability:

- one request containing prompt text and image attachment

Recommended output contract:

```json
{
  "short_answer": "B",
  "full_answer": "The answer is B because ...",
  "confidence": "high"
}
```

This is better than appending a short answer to the end of free-form reasoning because:

- parsing is deterministic
- you can separately store/display short and long outputs
- it works with any frontend

### 4. UI Surface

Three viable display modes:

#### A. Notification

Pros:

- trivial to implement
- no Waybar changes required

Cons:

- transient
- limited space

#### B. Waybar module

Pros:

- integrated with your existing bar
- ideal for `short_answer`

Cons:

- needs polling or signal-based refresh
- not a good place for long text

Recommendation:

- Start with notifications
- copy `full_answer` to clipboard
- add Waybar only after the end-to-end loop feels good

#### C. Overlay window

Pros:

- more room than Waybar
- can behave like a bar-sized answer panel

Cons:

- more implementation work
- focus/layer-shell behavior needs care on Wayland

Recommendation:

- defer until after the file/state and Waybar path works

## Data Model

Persist one JSON file, for example:

```json
{
  "status": "ok",
  "question_source": "/tmp/sneaky_bar/capture.png",
  "short_answer": "Paris",
  "full_answer": "The question asks for the capital of France. The answer is Paris.",
  "confidence": "high",
  "timestamp": "2026-03-13T01:21:18+00:00"
}
```

Possible statuses:

- `ok`
- `error`
- `capturing`
- `requesting`

This lets the UI show progress and failure states.

## Prompt Design

Do not ask for chain-of-thought or "reasoning". Ask for the final answer and a brief explanation only.

Better instruction:

```text
Analyze the screenshot and answer the visible question.
Return strict JSON with:
- short_answer: <= 80 characters
- full_answer: brief explanation
- confidence: low|medium|high
If the image is ambiguous or unreadable, say that clearly.
```

Reasons:

- easier parsing
- lower latency
- better aligned with production use
- avoids depending on hidden reasoning behavior

## Security and Privacy

This project will send screenshots off-device unless you use a local model.

Implications:

- region capture is safer than full-screen capture
- avoid sensitive tabs or personal data
- optionally add a local-model backend later

## Recommended Milestone Order

1. Notification-based MVP
2. Structured JSON response handling
3. Waybar integration
4. Retry/error UX
5. Overlay window if still needed
