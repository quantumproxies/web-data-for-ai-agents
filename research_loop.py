"""Search, read the top results, emit a Markdown brief with numbered citations.

No model in the loop — this is the deterministic half of "AI research": the
gathering. Feed the output to whichever LLM you like, or read it yourself.

    python3 research_loop.py "residential proxy pricing 2026" --pages 6 --out brief.md
"""
from __future__ import annotations

import argparse
from concurrent.futures import ThreadPoolExecutor
from urllib.parse import urlparse

from tools import _call


def host(url: str) -> str:
    return urlparse(url).netloc.removeprefix("www.")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("query")
    ap.add_argument("--country", default="us")
    ap.add_argument("--pages", type=int, default=5, help="how many results to actually read")
    ap.add_argument("--tokens", type=int, default=1200, help="token cap per source")
    ap.add_argument("--out", default="brief.md")
    args = ap.parse_args()

    serp = _call("/serp", {"query": args.query, "country": args.country, "num": 10})
    organic = (serp.get("organic") or [])[: args.pages]
    if not organic:
        raise SystemExit("no results — try a different query or country")

    def read(row: dict) -> dict:
        try:
            payload = _call("/scrape", {
                "url": row["link"], "format": "markdown", "contentMode": "article",
                "query": args.query, "highlights": True, "max_tokens": args.tokens,
            })
        except RuntimeError as exc:
            return {**row, "error": str(exc)}
        highlights = payload.get("highlights") or []
        text = "\n\n".join(h.get("text", "") for h in highlights) or payload.get("markdown", "")
        return {**row, "text": text, "title_read": (payload.get("metadata") or {}).get("title")}

    with ThreadPoolExecutor(max_workers=5) as pool:
        sources = list(pool.map(read, organic))

    lines = [f"# {args.query}", "",
             f"*{len(sources)} sources read from a live {args.country.upper()} Google SERP.*", ""]

    for n, source in enumerate(sources, 1):
        title = source.get("title_read") or source.get("title") or source["link"]
        lines += [f"## [{n}] {title}", f"<{source['link']}> · {host(source['link'])}", ""]
        if source.get("error"):
            lines += [f"> could not be read: {source['error']}", ""]
            continue
        lines += [source["text"].strip(), ""]

    lines += ["---", "", "## Sources", ""]
    lines += [f"{n}. [{host(s['link'])}]({s['link']}) — {s.get('title', '')}"
              for n, s in enumerate(sources, 1)]

    with open(args.out, "w", encoding="utf-8") as fh:
        fh.write("\n".join(lines))

    read_ok = sum(1 for s in sources if not s.get("error"))
    print(f"{read_ok}/{len(sources)} sources read → {args.out}")
    print(f"cost about ${0.0005 + 0.0002 * len(sources):.4f}")


if __name__ == "__main__":
    main()
