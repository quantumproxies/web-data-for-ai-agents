"""Trim a page to a token budget before it reaches the model — server-side.

Doing this in the API means you never pay to transfer, or to tokenise, the 40 KB
of boilerplate you were going to throw away anyway.

    python3 token_budget.py https://quanticdata.io/collectors/ --tokens 800
"""
from __future__ import annotations

import argparse

from tools import _call


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("url")
    ap.add_argument("--tokens", type=int, default=1000)
    ap.add_argument("--query", default=None, help="keep only the passages about this")
    args = ap.parse_args()

    full = _call("/scrape", {"url": args.url, "format": "markdown", "contentMode": "full"})
    smart = _call("/scrape", {"url": args.url, "format": "markdown", "contentMode": "smart"})

    body = {"url": args.url, "format": "markdown", "contentMode": "article",
            "max_tokens": args.tokens, "links_mode": "minimal", "toc": True}
    if args.query:
        body |= {"query": args.query, "highlights": True}
    shaped = _call("/scrape", body)

    def size(payload: dict) -> int:
        return len(payload.get("markdown") or "")

    print(f"{args.url}\n")
    print(f"  contentMode=full            {size(full):>8,} chars")
    print(f"  contentMode=smart           {size(smart):>8,} chars"
          f"  ({100 - 100 * size(smart) // max(size(full), 1)}% smaller)")
    print(f"  article + {args.tokens}-token cap  {size(shaped):>8,} chars"
          f"  ({100 - 100 * size(shaped) // max(size(full), 1)}% smaller)")

    chunks = shaped.get("chunks") or []
    if chunks:
        print(f"\n  {len(chunks)} chunks, each carrying its heading path:")
        for chunk in chunks[:5]:
            print(f"    {chunk.get('tokens', '?'):>5} tok  {chunk.get('heading_path') or chunk.get('heading')}")

    print("\n--- what the model would actually see ---")
    print((shaped.get("markdown") or "")[:800])


if __name__ == "__main__":
    main()
