"""Verify that both configured LLM providers respond independently."""

import asyncio
import sys

from loanlens.config import get_settings
from loanlens.llm.gateway import build_gateway


async def main() -> int:
    settings = get_settings()
    gateway = build_gateway(settings)

    expected = {"gemini", "groq"}
    failed = False

    try:
        for name in sorted(expected):
            provider = next(
                (p for p in gateway.providers if p.name == name),
                None,
            )

            if provider is None:
                print(f"FAIL {name}: API key not configured")
                failed = True
                continue

            try:
                reply = await provider.generate(
                    [{"role": "user", "content": "Reply with exactly: OK"}],
                    temperature=0,
                )

                if not reply.text.strip():
                    raise ValueError("Empty response")

                print(f"OK {name}")

            except Exception as exc:
                print(f"FAIL {name}: {type(exc).__name__}")
                failed = True

    finally:
        for provider in gateway.providers:
            await provider._client.aclose()

    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
