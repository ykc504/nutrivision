# NutriVision AI (Hackathon-ready)

Dark, minimal, browser-based nutrition assistant with:

- Barcode scan (camera) + product search with images (Open Food Facts)
- Personalized scoring + risks (conditions-aware)
- Additive analyzer with **sourced concerns** via **Tavily + Groq** (optional)
- Menu OCR with **green/yellow/red** recommendations + dropdown “Why?”
- AI Coach that answers **any question** (Groq preferred; local FLAN-T5 fallback)

## 1) Run locally

```bash
cd nutrition-app
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -r requirements.txt
python main.py
```

Open: `http://127.0.0.1:8000`

## 2) Camera barcode scanning (mobile)

Most mobile browsers require **HTTPS** for camera access.

Use ngrok:

```bash
ngrok http 8000
```

Open the **HTTPS** ngrok URL on your phone.

## 3) Enable Tavily + Groq (recommended)

Set environment variables:

```bash
export TAVILY_API_KEY="..."
export GROQ_API_KEY="..."
```

- Tavily is used to fetch reputable snippets for additives.
- Groq is used to summarize/coach using an OpenAI-compatible API.

If keys are not set, the app still runs (falls back to built-in database + basic logic).

## 4) Notes on Torch

Do **not** pin `torch==2.4.0` on Windows—some indexes only provide newer versions.
Install torch without pinning:

```bash
pip install torch torchvision
```

Torch is **optional** if you use Groq for the AI Coach.
