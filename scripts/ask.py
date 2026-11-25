"""Small streaming client for the LoanLens chat API."""

import argparse
import json
import time

import httpx


def main():
    parser = argparse.ArgumentParser(description="Ask LoanLens a question.")
    parser.add_argument("message", help="Question to ask LoanLens")
    parser.add_argument("--url", default="http://localhost:8000")
    parser.add_argument(
        "--json",
        action="store_true",
        help="Request a non-streaming JSON response",
    )
    args = parser.parse_args()

    endpoint = f"{args.url.rstrip('/')}/v1/chat"
    payload = {"message": args.message, "stream": not args.json}

    started = time.perf_counter()
    first_word_at = None
    metadata = {}

    try:
        with httpx.Client(timeout=120.0) as client:
            if args.json:
                response = client.post(endpoint, json=payload)
                response.raise_for_status()
                data = response.json()
                print(data.get("answer", ""))
                metadata = data
                first_word_at = time.perf_counter() - started

            else:
                with client.stream("POST", endpoint, json=payload) as response:
                    response.raise_for_status()

                    for line in response.iter_lines():
                        if not line.startswith("data: "):
                            continue

                        data = json.loads(line[6:])

                        if "delta" in data:
                            if first_word_at is None:
                                first_word_at = time.perf_counter() - started
                            print(data["delta"], end="", flush=True)

                        elif "detail" in data:
                            raise RuntimeError(data["detail"])

                        elif "provider" in data:
                            metadata = data

        total = time.perf_counter() - started

        print("\n")
        if metadata:
            print(
                f"--- {metadata.get('provider', '?')} / "
                f"{metadata.get('model', '?')}: "
                f"first words after {first_word_at or 0:.2f} s, "
                f"total {total:.2f} s"
            )
            print(
                f"    tokens in={metadata.get('tokens_in', 0)} "
                f"out={metadata.get('tokens_out', 0)}  "
                f"cost Rs {metadata.get('cost_inr', 0):.6f}  "
                f"attempts={metadata.get('attempts', 0)}  "
                f"fallback={'YES' if metadata.get('fallback_used') else 'no'}"
            )

    except (httpx.HTTPError, RuntimeError, ValueError) as exc:
        raise SystemExit(f"Request failed: {exc}") from exc


if __name__ == "__main__":
    main()
