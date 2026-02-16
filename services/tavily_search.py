"""Tavily Search integration (optional).

Set env var TAVILY_API_KEY.
Used to fetch reputable snippets for additive concerns / ingredient questions.
"""

from __future__ import annotations

import os
import requests


def tavily_search(query: str, *, max_results: int = 5) -> list[dict]:
    key = os.getenv("TAVILY_API_KEY")
    if not key:
        return []

    url = "https://api.tavily.com/search"
    payload = {
        "api_key": key,
        "query": query,
        "search_depth": "basic",
        "max_results": max_results,
        "include_answer": False,
        "include_raw_content": False,
        "include_images": False,
    }
    try:
        r = requests.post(url, json=payload, timeout=12)
        r.raise_for_status()
        data = r.json() or {}
        return data.get("results", []) or []
    except Exception:
        return []
