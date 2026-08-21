"""The same loop against the OpenAI chat completions API.

    pip install openai requests
    export OPENAI_API_KEY=sk-...  QUANTICDATA_API_KEY=qd_live_...
    python3 openai_agent.py "Compare the pricing pages of three SERP API vendors."
"""
from __future__ import annotations

import json
import os
import sys

from openai import OpenAI

from tools import TOOL_SCHEMAS, dispatch

MODEL = os.environ.get("OPENAI_MODEL", "gpt-4o")
MAX_TURNS = 8

SYSTEM = ("You have live web access. Search to find sources, scrape to read them, and cite "
          "the URL for every factual claim. If the tools do not answer the question, say so "
          "instead of guessing.")

# OpenAI wants each tool wrapped as {"type": "function", "function": {...}}.
OPENAI_TOOLS = [{"type": "function", "function": t} for t in TOOL_SCHEMAS]


def main() -> None:
    if len(sys.argv) < 2:
        raise SystemExit('usage: python3 openai_agent.py "your question"')

    client = OpenAI()
    messages = [{"role": "system", "content": SYSTEM},
                {"role": "user", "content": " ".join(sys.argv[1:])}]

    for _ in range(MAX_TURNS):
        response = client.chat.completions.create(
            model=MODEL, messages=messages, tools=OPENAI_TOOLS,
        )
        message = response.choices[0].message
        messages.append(message.model_dump(exclude_none=True))

        if message.content:
            print(message.content)
        if not message.tool_calls:
            return

        for call in message.tool_calls:
            args = json.loads(call.function.arguments or "{}")
            print(f"  → {call.function.name}({args})", file=sys.stderr)
            messages.append({
                "role": "tool",
                "tool_call_id": call.id,
                "content": dispatch(call.function.name, args),
            })

    print(f"\n[stopped after {MAX_TURNS} turns]", file=sys.stderr)


if __name__ == "__main__":
    main()
