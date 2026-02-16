"""LLM wrapper.

Primary: Groq (OpenAI-compatible) if GROQ_API_KEY is set.
Fallback: local transformers pipeline if installed.

No paid OpenAI/GPT required.
"""

from __future__ import annotations

import os
import json
import requests



def openrouter_chat(messages: list[dict], *, model: str | None = None, max_tokens: int = 350) -> str | None:
    key = os.getenv("OPENROUTER_API_KEY")
    if not key:
        return None
    url = "https://openrouter.ai/api/v1/chat/completions"
    payload = {
        "model": model or os.getenv("OPENROUTER_MODEL", "google/gemma-2-9b-it"),
        "messages": messages,
        "temperature": 0.2,
        "max_tokens": max_tokens,
    }
    headers = {
        "Authorization": f"Bearer {key}",
        "Content-Type": "application/json",
        # optional but recommended by OpenRouter
        "HTTP-Referer": os.getenv("OPENROUTER_SITE", "http://localhost"),
        "X-Title": os.getenv("OPENROUTER_APP", "NutriVision"),
    }
    try:
        r = requests.post(url, headers=headers, data=json.dumps(payload), timeout=25)
        r.raise_for_status()
        data = r.json() or {}
        return (((data.get("choices") or [{}])[0]).get("message") or {}).get("content")
    except Exception:
        return None


def groq_chat(messages: list[dict], *, model: str = "llama-3.1-8b-instant", max_tokens: int = 350) -> str | None:
    key = os.getenv("GROQ_API_KEY")
    if not key:
        return None
    url = "https://api.groq.com/openai/v1/chat/completions"
    payload = {
        "model": model,
        "messages": messages,
        "temperature": 0.2,
        "max_tokens": max_tokens,
    }
    try:
        r = requests.post(url, headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"}, data=json.dumps(payload), timeout=20)
        r.raise_for_status()
        data = r.json() or {}
        return (((data.get("choices") or [{}])[0]).get("message") or {}).get("content")
    except Exception:
        return None


_local_pipe = None


def local_text2text(prompt: str) -> str | None:
    global _local_pipe
    try:
        if _local_pipe is None:
            from transformers import pipeline

            _local_pipe = pipeline("text2text-generation", model="google/flan-t5-base")
        out = _local_pipe(prompt, max_length=220)
        return (out[0] or {}).get("generated_text")
    except Exception:
        return None


def answer(prompt: str, *, system: str = "You are a careful, health-focused nutrition assistant.") -> str:
    msg = [
        {"role": "system", "content": system},
        {"role": "user", "content": prompt},
    ]
    g = groq_chat(msg)
    if g:
        return g.strip()
    o = openrouter_chat(msg)
    if o:
        return o.strip()
    l = local_text2text(prompt)
    if l:
        return l.strip()
    # final fallback: still provide helpful, non-AI guidance
    return "Tell me your age, weight, height, goal, and any conditions (e.g., diabetes, hypertension). Then ask your question again and I’ll answer using rules even without an AI key."
