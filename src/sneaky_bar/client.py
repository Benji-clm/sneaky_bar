from __future__ import annotations

import base64
import json
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

DEFAULT_SYSTEM_PROMPT = """You answer questions shown in screenshots.
Return strict JSON with keys:
- question_summary: a brief summary of the current question or task, at most 120 characters
- short_answer: a concise answer with at most 80 characters
- full_answer: a plain-language answer
- confidence: low, medium, or high
If the screenshot is unreadable, say so briefly.
If visible answer choices are present, treat the task as multiple choice.
When it is multiple choice, choose only from the options visible in the screenshot.
Do not invent a new answer if choices are shown.
If option labels like A, B, C, D are visible, include the label in short_answer.
If both label and option text are visible, prefer a short_answer like "B: Mitochondria".
In full_answer, mention which visible option you selected.
Do not include markdown fences.
"""

DEFAULT_USER_PROMPT = (
    "Read the screenshot and answer the question shown there. "
    "First determine whether visible answer choices are present. "
    "If choices are present, answer by selecting the best visible option rather than "
    "answering from general knowledge alone. "
    "If no choices are present, answer normally."
)


@dataclass
class ClientConfig:
    api_key: str
    model: str
    chat_base_url: str = "https://api.openai.com/v1/chat/completions"
    responses_base_url: str = "https://api.openai.com/v1/responses"
    system_prompt: str = DEFAULT_SYSTEM_PROMPT
    user_prompt: str = DEFAULT_USER_PROMPT
    timeout_seconds: int = 45


class ClientError(RuntimeError):
    pass


def load_config(model_override: str | None = None) -> ClientConfig:
    api_key = os.environ.get("SNEAKY_BAR_API_KEY") or os.environ.get("OPENAI_API_KEY")
    model = model_override or os.environ.get("SNEAKY_BAR_MODEL", "gpt-5.4")
    chat_base_url = os.environ.get(
        "SNEAKY_BAR_BASE_URL", "https://api.openai.com/v1/chat/completions"
    )
    responses_base_url = os.environ.get(
        "SNEAKY_BAR_RESPONSES_BASE_URL", "https://api.openai.com/v1/responses"
    )

    if not api_key:
        raise ClientError("Missing SNEAKY_BAR_API_KEY or OPENAI_API_KEY")

    return ClientConfig(
        api_key=api_key,
        model=model,
        chat_base_url=chat_base_url,
        responses_base_url=responses_base_url,
    )


def encode_image(image_path: Path) -> str:
    return base64.b64encode(image_path.read_bytes()).decode("ascii")


def build_chat_payload(
    config: ClientConfig, image_b64: str, context_text: str = ""
) -> dict[str, Any]:
    prompt_parts = []
    if context_text:
        prompt_parts.append(context_text)
    prompt_parts.append(config.user_prompt)
    user_text = "\n\n".join(prompt_parts)

    return {
        "model": config.model,
        "response_format": {"type": "json_object"},
        "messages": [
            {"role": "system", "content": config.system_prompt},
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": user_text},
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": f"data:image/png;base64,{image_b64}",
                        },
                    },
                ],
            },
        ],
    }


def build_responses_payload(
    config: ClientConfig, image_b64: str, context_text: str = ""
) -> dict[str, Any]:
    prompt_parts = []
    if context_text:
        prompt_parts.append(context_text)
    prompt_parts.append(config.user_prompt)
    user_text = "\n\n".join(prompt_parts)

    return {
        "model": config.model,
        "instructions": config.system_prompt,
        "reasoning": {"effort": "high"},
        "text": {
            "format": {
                "type": "json_schema",
                "name": "sneaky_bar_answer",
                "strict": True,
                "schema": {
                    "type": "object",
                    "additionalProperties": False,
                    "properties": {
                        "question_summary": {"type": "string"},
                        "short_answer": {"type": "string"},
                        "full_answer": {"type": "string"},
                        "confidence": {
                            "type": "string",
                            "enum": ["low", "medium", "high"],
                        },
                    },
                    "required": [
                        "question_summary",
                        "short_answer",
                        "full_answer",
                        "confidence",
                    ],
                },
            }
        },
        "input": [
            {
                "role": "user",
                "content": [
                    {"type": "input_text", "text": user_text},
                    {
                        "type": "input_image",
                        "image_url": f"data:image/png;base64,{image_b64}",
                    },
                ],
            }
        ],
    }


def request_answer(
    config: ClientConfig,
    image_path: Path,
    context_text: str = "",
    api_mode: str = "chat",
) -> dict[str, Any]:
    image_b64 = encode_image(image_path)
    if api_mode == "responses":
        payload = build_responses_payload(config, image_b64, context_text)
        url = config.responses_base_url
    else:
        payload = build_chat_payload(config, image_b64, context_text)
        url = config.chat_base_url

    request = Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Authorization": f"Bearer {config.api_key}",
            "Content-Type": "application/json",
        },
        method="POST",
    )

    try:
        with urlopen(request, timeout=config.timeout_seconds) as response:
            body = json.loads(response.read().decode("utf-8"))
    except HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        raise ClientError(f"API error {exc.code}: {detail}") from exc
    except URLError as exc:
        raise ClientError(f"Network error: {exc}") from exc

    if api_mode == "responses":
        return extract_responses_result(body)
    return extract_chat_result(body)


def parse_result_text(content: str) -> dict[str, Any]:
    try:
        parsed = json.loads(content)
    except json.JSONDecodeError as exc:
        raise ClientError(f"Model did not return valid JSON: {content}") from exc

    question_summary = str(parsed.get("question_summary", "")).strip()[:120]
    short_answer = str(parsed.get("short_answer", "")).strip()[:80]
    full_answer = str(parsed.get("full_answer", "")).strip()
    confidence = str(parsed.get("confidence", "unknown")).strip().lower()

    if not short_answer:
        raise ClientError("Model response missing short_answer")

    return {
        "question_summary": question_summary or short_answer,
        "short_answer": short_answer,
        "full_answer": full_answer or short_answer,
        "confidence": confidence or "unknown",
    }


def extract_chat_result(body: dict[str, Any]) -> dict[str, Any]:
    try:
        content = body["choices"][0]["message"]["content"]
    except (KeyError, IndexError, TypeError) as exc:
        raise ClientError(f"Unexpected API response shape: {body}") from exc

    if not isinstance(content, str):
        raise ClientError(f"Expected string content, got: {content!r}")

    result = parse_result_text(content)
    result["raw"] = body
    return result


def extract_responses_result(body: dict[str, Any]) -> dict[str, Any]:
    content = body.get("output_text")
    if not isinstance(content, str) or not content.strip():
        output = body.get("output", [])
        for item in output if isinstance(output, list) else []:
            if item.get("type") != "message":
                continue
            for part in item.get("content", []):
                if part.get("type") == "output_text" and isinstance(part.get("text"), str):
                    content = part["text"]
                    break
            if isinstance(content, str) and content.strip():
                break

    if not isinstance(content, str) or not content.strip():
        raise ClientError(f"Unexpected Responses API response shape: {body}")

    result = parse_result_text(content)
    result["raw"] = body
    return result
