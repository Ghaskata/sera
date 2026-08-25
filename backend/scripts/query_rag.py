#!/usr/bin/env python3
"""Query Sera's local/admin multi-source Gemini RAG endpoint."""

import argparse
import json
import os
import sys
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


def main() -> int:
    parser = argparse.ArgumentParser(description="Query Sera connected sources")
    parser.add_argument("question")
    parser.add_argument("--workspace-id", required=True)
    parser.add_argument("--base-url", default="http://127.0.0.1:8000")
    parser.add_argument("--source", action="append", dest="source_types", help="Exact source label, repeatable")
    args = parser.parse_args()

    token = os.environ.get("RAG_QUERY_TOKEN")
    if not token:
        parser.error("RAG_QUERY_TOKEN environment variable is required")

    payload = {
        "workspace_id": args.workspace_id,
        "question": args.question,
    }
    if args.source_types:
        payload["source_types"] = args.source_types

    request = Request(
        f"{args.base_url.rstrip('/')}/rag/query",
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Content-Type": "application/json",
            "X-RAG-Token": token,
        },
        method="POST",
    )
    try:
        with urlopen(request, timeout=60) as response:
            result = json.loads(response.read().decode("utf-8"))
    except (HTTPError, URLError) as exc:
        print(f"RAG request failed: {exc}", file=sys.stderr)
        return 1

    print(result["answer"])
    if result.get("sources"):
        print("\nSources:")
        for source in result["sources"]:
            label = source.get("title", "source")
            if source.get("source"):
                label = f"{source['source']} — {label}"
            if source.get("date"):
                label += f" ({source['date']})"
            print(f"- {label}: {source.get('url') or source.get('drive_link') or 'no link'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
