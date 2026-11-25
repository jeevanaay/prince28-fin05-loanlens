"""Gemini provider using the Interactions API and server-sent events."""

import json
from collections.abc import AsyncIterator
from dataclasses import dataclass
from typing import Any

import httpx

GEMINI_URL = "https://generativelanguage.googleapis.com/v1beta/interactions"


class GeminiAPIError(RuntimeError):
    """Raised when Gemini returns an API or streaming error."""


@dataclass(frozen=True)
class GeminiEvent:
    """A normalized event from the Gemini stream."""

    event_type: str
    text: str | None = None
    interaction_id: str | None = None
    usage: dict[str, Any] | None = None


class GeminiProvider:
    """Streams text responses from Google's Gemini Interactions API."""

    def __init__(
        self,
        api_key: str,
        model: str,
        client: httpx.AsyncClient,
    ) -> None:
        if not api_key:
            raise ValueError("Gemini API key is required.")

        self.api_key = api_key
        self.model = model
        self.client = client

    async def stream(
        self,
        prompt: str,
        system_instruction: str | None = None,
    ) -> AsyncIterator[GeminiEvent]:
        """Yield normalized events as Gemini generates its response."""
        payload: dict[str, Any] = {
            "model": self.model,
            "input": prompt,
            "stream": True,
        }

        if system_instruction:
            payload["system_instruction"] = system_instruction

        headers = {
            "x-goog-api-key": self.api_key,
            "Content-Type": "application/json",
            "Accept": "text/event-stream",
        }

        async with self.client.stream(
            "POST",
            GEMINI_URL,
            headers=headers,
            json=payload,
            timeout=60.0,
        ) as response:
            if response.is_error:
                body = await response.aread()
                raise GeminiAPIError(
                    f"Gemini HTTP {response.status_code}: {body.decode('utf-8', errors='replace')}"
                )

            interaction_id: str | None = None
            data_lines: list[str] = []

            async for line in response.aiter_lines():
                if line.startswith("data:"):
                    data_lines.append(line[5:].strip())
                    continue

                if line.strip() or not data_lines:
                    continue

                raw_data = "\n".join(data_lines)
                data_lines.clear()

                if raw_data == "[DONE]":
                    break

                try:
                    event = json.loads(raw_data)
                except json.JSONDecodeError as exc:
                    raise GeminiAPIError("Gemini returned invalid SSE JSON.") from exc

                event_type = event.get("event_type", "")

                if event_type == "interaction.created":
                    interaction = event.get("interaction", {})
                    interaction_id = interaction.get("id")

                    yield GeminiEvent(
                        event_type=event_type,
                        interaction_id=interaction_id,
                    )

                elif event_type == "step.delta":
                    delta = event.get("delta", {})

                    if delta.get("type") == "text":
                        text = delta.get("text", "")
                        if text:
                            yield GeminiEvent(
                                event_type=event_type,
                                text=text,
                                interaction_id=interaction_id,
                            )

                elif event_type == "interaction.completed":
                    interaction = event.get("interaction", {})

                    yield GeminiEvent(
                        event_type=event_type,
                        interaction_id=interaction.get("id", interaction_id),
                        usage=interaction.get("usage"),
                    )

                elif event_type == "error":
                    error = event.get("error", {})
                    raise GeminiAPIError(error.get("message", "Gemini streaming failed."))
