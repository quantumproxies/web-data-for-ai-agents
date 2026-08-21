"""Four QuanticData tools, described once and reused by every agent here.

The schemas below are plain JSON Schema, which is what both Anthropic and OpenAI
want — only the wrapper shape differs, and that is handled in the agent files.
"""
from __future__ import annotations

import json
import os
from typing import Any

import requests

BASE = "https://api.quanticdata.io/v1"
_s = requests.Session()

TOOL_SCHEMAS = [
    {
        "name": "search",
        "description": (
            "Search the live web (Google by default; also Bing, DuckDuckGo, Yandex) and get "
            "organic results with title, link and snippet. Use this to FIND pages. It does not "
            "return page content — follow up with scrape on the links that look right."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "The search query."},
                "country": {"type": "string", "description": "ISO country code, e.g. us, de, it."},
                "num": {"type": "integer", "description": "How many results, 1-20. Default 10."},
            },
            "required": ["query"],
        },
    },
    {
        "name": "scrape",
        "description": (
            "Fetch one URL and return it as clean Markdown, with navigation and boilerplate "
            "removed. Use this to READ a page you already have the URL for. Pass `query` to get "
            "only the passages relevant to a question, which keeps the response small."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "url": {"type": "string", "description": "The page to read."},
                "query": {"type": "string", "description": "Return the passages relevant to this question."},
                "max_tokens": {"type": "integer", "description": "Cap the Markdown at this many tokens."},
            },
            "required": ["url"],
        },
    },
    {
        "name": "map_site",
        "description": (
            "List every URL of a website, from its sitemaps and homepage links, without fetching "
            "the pages. Use this when you need to know what a site contains before deciding what "
            "to read. One flat call, whatever the site's size."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "url": {"type": "string", "description": "Any URL on the site."},
                "search": {"type": "string", "description": "Only URLs containing this substring."},
                "limit": {"type": "integer", "description": "Max URLs to return. Default 100."},
            },
            "required": ["url"],
        },
    },
    {
        "name": "seo_audit",
        "description": (
            "Fetch a URL as a no-JavaScript bot and as a rendered browser, and return both views "
            "plus the differences. Use this to answer questions about how a page appears to search "
            "engines, not to read its content."
        ),
        "parameters": {
            "type": "object",
            "properties": {"url": {"type": "string", "description": "The page to audit."}},
            "required": ["url"],
        },
    },
]


def _call(path: str, body: dict[str, Any]) -> dict:
    key = os.environ.get("QUANTICDATA_API_KEY")
    if not key:
        raise SystemExit("set QUANTICDATA_API_KEY — https://app.quanticdata.io/register")
    r = _s.post(f"{BASE}{path}", json=body,
                headers={"Authorization": f"Bearer {key}"}, timeout=180)
    data = r.json()
    if data.get("type") == "error" or not r.ok:
        raise RuntimeError(data.get("message") or f"HTTP {r.status_code}")
    return data.get("payload", {})


def dispatch(name: str, args: dict[str, Any]) -> str:
    """Run a tool and return a compact string for the model. Errors come back as text."""
    try:
        if name == "search":
            payload = _call("/serp", {"query": args["query"],
                                      "country": args.get("country"),
                                      "num": min(int(args.get("num", 10)), 20)})
            rows = payload.get("organic") or []
            return json.dumps([{k: r.get(k) for k in ("position", "title", "link", "snippet")}
                               for r in rows], ensure_ascii=False)

        if name == "scrape":
            body = {"url": args["url"], "format": "markdown", "contentMode": "article"}
            if args.get("query"):
                body |= {"query": args["query"], "highlights": True}
            if args.get("max_tokens"):
                body["max_tokens"] = int(args["max_tokens"])
            payload = _call("/scrape", body)
            highlights = payload.get("highlights")
            text = "\n\n".join(h.get("text", "") for h in highlights) if highlights \
                else payload.get("markdown", "")
            title = (payload.get("metadata") or {}).get("title") or ""
            return f"# {title}\nsource: {args['url']}\n\n{text}"

        if name == "map_site":
            payload = _call("/map", {"url": args["url"], "search": args.get("search"),
                                     "limit": int(args.get("limit", 100))})
            return json.dumps({"total": payload.get("total"),
                               "sections": payload.get("summary"),
                               "urls": (payload.get("links") or [])[:200]}, ensure_ascii=False)

        if name == "seo_audit":
            payload = _call("/seo-audit", {"url": args["url"]})
            return json.dumps({k: payload.get(k) for k in ("noJs", "render", "diff", "meta")},
                              ensure_ascii=False)

        return f"unknown tool: {name}"
    except (RuntimeError, KeyError) as exc:
        return f"tool error: {exc}"
