"""Photo meal scan (fast).

Uses HuggingFace Inference API if HF_TOKEN is set.
Fallback: returns a fast 'unknown' label without blocking.

This keeps demo responsive even without torch/transformers.
"""

from __future__ import annotations
import os, json, requests
from services.usda_api import search_food

HF_MODEL = os.getenv("HF_FOOD_MODEL", "nateraw/food")
HF_TOKEN = os.getenv("HF_TOKEN")  # optional

def _hf_classify(image_bytes: bytes):
    if not HF_TOKEN:
        return None
    url = f"https://api-inference.huggingface.co/models/{HF_MODEL}"
    headers = {"Authorization": f"Bearer {HF_TOKEN}"}
    try:
        r = requests.post(url, headers=headers, data=image_bytes, timeout=25)
        r.raise_for_status()
        data = r.json()
        if isinstance(data, list) and data:
            top = data[0]
            label = top.get("label")
            score = top.get("score", 0.0)
            return label, int(score * 100)
    except Exception:
        return None
    return None

def analyze_photo(image_bytes: bytes):
    pred = _hf_classify(image_bytes)
    if not pred:
        # non-blocking fallback
        return {"label": "Unknown food", "confidence": 0, "usda": None}

    label, conf = pred
    # USDA keyword search (best-effort)
    usda = None
    try:
        usda = search_food(label)
    except Exception:
        usda = None
    return {"label": label, "confidence": conf, "usda": usda}
