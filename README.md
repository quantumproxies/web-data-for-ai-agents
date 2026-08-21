# Web data for AI agents — QuanticData as tool calls for Claude and OpenAI

An LLM with no web access answers from a frozen snapshot. Give it four tools —
`search`, `scrape`, `map`, `crawl` — and it can go and check.

This repo wires the [QuanticData Web Data API for AI](https://quanticdata.io/web-data-api-for-ai/)
into both major tool-calling formats, plus the search-then-read loop that produces answers with
real citations instead of confident guesses.

```bash
pip install requests anthropic          # or: pip install requests openai
export QUANTICDATA_API_KEY=qd_live_your_key_here
export ANTHROPIC_API_KEY=sk-ant-...

python3 claude_agent.py "What changed in the EU AI Act timeline this month?"
python3 openai_agent.py "Compare the pricing pages of three SERP API vendors."
python3 research_loop.py "residential proxy pricing 2026" --pages 6 --out brief.md
```

Prefer not to write the plumbing at all? The
[MCP server](https://github.com/quantumproxies/quanticdata-mcp-server) exposes the same tools to
any MCP client with no code on your side.

## Files

| File | What it does |
|---|---|
| [`tools.py`](tools.py) | the four tools: JSON schemas + a dispatcher, framework-agnostic |
| [`claude_agent.py`](claude_agent.py) | Anthropic Messages API tool loop |
| [`openai_agent.py`](openai_agent.py) | OpenAI chat completions tool loop |
| [`research_loop.py`](research_loop.py) | search → read top N → numbered citations → Markdown brief (no LLM required) |
| [`token_budget.py`](token_budget.py) | keep a page under a token cap before it reaches the model |

## Why Markdown, not HTML

A rendered product page is 300 KB of HTML and maybe 4 KB of meaning. Feeding the HTML to a model
costs you fifty times the tokens for a *worse* answer, because the signal is buried in markup.
`/v1/scrape` returns Markdown with navigation, footers and cookie chrome already stripped
(`contentMode: "smart"`), or the article body alone (`contentMode: "article"`).

The API also shapes output for exactly this use case:

| Parameter | Effect |
|---|---|
| `max_tokens` | hard cap on the returned Markdown |
| `query` + `highlights` | return the passages most relevant to a question |
| `chunk` | split into `payload.chunks[]`, each with its heading path and token count |
| `links_mode` | trim the link soup that wastes tokens and tempts a model to hallucinate URLs |
| `frontmatter` | YAML header with title, canonical and fetch time — provenance for free |

## The one rule for agent-grade web data

**Every claim carries its source.** `research_loop.py` numbers each fetched page, quotes only
from the numbered set, and emits a reference list. That is the difference between an answer a
reader can verify and an answer they have to trust.

## Costs

A search is $0.0005 and a page is $0.0002, so a six-source research turn costs about **$0.002** —
roughly a thousandth of what the model tokens for the same turn will cost you. Failed fetches are
not billed, so a blocked page costs nothing but a retry.

## Related

- [Web Data API for AI](https://quanticdata.io/web-data-api-for-ai/) · [MCP server](https://quanticdata.io/mcp-server/) · [Documentation](https://quanticdata.io/docs/)
- [How to feed data to an LLM](https://quanticdata.io/blog/how-to-feed-data-to-an-llm/) · [How to use data for AI](https://quanticdata.io/blog/how-to-use-data-for-ai/)
- [Can AI work without data?](https://quanticdata.io/blog/can-ai-work-without-data/) · [How to use the Claude API](https://quanticdata.io/blog/how-to-use-claude-api/)

MIT licensed.
