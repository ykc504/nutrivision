"""Enrich additive concerns using Tavily + Groq (optional).

Flow:
1) Look in SQLite additive_cache.
2) If missing and keys exist, Tavily search for reputable sources.
3) Use Groq (or local fallback) to summarize concerns in short bullets.
"""

from __future__ import annotations

import json

from database import get_cached_additive, cache_additive
from services.tavily_search import tavily_search
from services.llm import answer


def enrich_additive(code: str, *, name: str = "", risk: str = "unknown") -> dict:
    code_u = (code or "").upper()
    if not code_u:
        return {"concerns": "Information not available", "sources": []}

    cached = get_cached_additive(code_u)
    if cached and cached.get("concerns"):
        try:
            sources = json.loads(cached.get("sources_json") or "[]")
        except Exception:
            sources = []
        return {"concerns": cached.get("concerns"), "sources": sources}

    # Query
    q = f"{code_u} {name} food additive health concerns EFSA FDA"
    results = tavily_search(q, max_results=5)

    # If Tavily isn't configured, return minimal.
    if not results:
        return {"concerns": "Information not available (configure TAVILY_API_KEY for sourced concerns).", "sources": []}

    snippets = []
    sources = []
    for r in results[:5]:
        title = r.get("title") or ""
        url = r.get("url") or ""
        content = r.get("content") or r.get("snippet") or ""
        if content:
            snippets.append(f"- {title}: {content[:240]}")
        if url:
            sources.append({"title": title[:120], "url": url})

    prompt = f"""
Summarize the health concerns for the food additive {code_u} ({name}).

Use ONLY the sources below. Be cautious. No medical diagnosis.

Sources:
{chr(10).join(snippets)}

Output format:
- 3–6 bullet concerns (short)
- 1 bullet: who should be careful (e.g., children/asthma/allergies)
"""
    concerns = answer(prompt)

    # Cache
    try:
        cache_additive(code_u, name, risk, concerns, json.dumps(sources))
    except Exception:
        pass

    return {"concerns": concerns, "sources": sources}
