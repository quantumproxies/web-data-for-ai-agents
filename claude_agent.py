"""A Claude tool loop with live web access.

    pip install anthropic requests
    export ANTHROPIC_API_KEY=sk-ant-...  QUANTICDATA_API_KEY=qd_live_...
    python3 claude_agent.py "What changed in the EU AI Act timeline this month?"
"""
from __future__ import annotations

import os
import sys

from anthropic import Anthropic

from tools import TOOL_SCHEMAS, dispatch

MODEL = os.environ.get("ANTHROPIC_MODEL", "claude-sonnet-5")
MAX_TURNS = 8

SYSTEM = """You have live web access through four tools.

Work like a researcher, not a search box:
- search to find candidates, then scrape the two or three that look authoritative.
- Prefer primary sources (the vendor's own docs, the regulator's own text) over summaries.
- Never state a fact you did not read in a tool result. If the tools did not answer, say so.
- Cite every claim with the URL you read it on."""

# Anthropic wants {name, description, input_schema}; our schemas use "parameters".
CLAUDE_TOOLS = [{"name": t["name"], "description": t["description"], "input_schema": t["parameters"]}
                for t in TOOL_SCHEMAS]


def main() -> None:
    if len(sys.argv) < 2:
        raise SystemExit('usage: python3 claude_agent.py "your question"')

    client = Anthropic()
    messages = [{"role": "user", "content": " ".join(sys.argv[1:])}]

    for turn in range(MAX_TURNS):
        response = client.messages.create(
            model=MODEL, max_tokens=4096, system=SYSTEM,
            tools=CLAUDE_TOOLS, messages=messages,
        )
        messages.append({"role": "assistant", "content": response.content})

        calls = [block for block in response.content if block.type == "tool_use"]
        for block in response.content:
            if block.type == "text" and block.text.strip():
                print(block.text)

        if not calls:
            return

        results = []
        for call in calls:
            print(f"  → {call.name}({', '.join(f'{k}={v!r}' for k, v in call.input.items())})",
                  file=sys.stderr)
            output = dispatch(call.name, call.input)
            results.append({"type": "tool_result", "tool_use_id": call.id, "content": output})
        messages.append({"role": "user", "content": results})

    print(f"\n[stopped after {MAX_TURNS} turns]", file=sys.stderr)


if __name__ == "__main__":
    main()
