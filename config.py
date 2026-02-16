import os
from dotenv import load_dotenv

# Load .env from project root (same folder as main.py)
load_dotenv()

ENV = os.getenv("ENV", "development")
DEBUG = os.getenv("DEBUG", "False").lower() == "true"

SECRET_KEY = os.getenv("SECRET_KEY", "nutrivision-dev-secret")
SESSION_SECRET = os.getenv("SESSION_SECRET", SECRET_KEY)

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./nutrivision.db")
DATABASE_PATH = os.getenv("DATABASE_PATH", DATABASE_URL.replace("sqlite:///", "", 1) if DATABASE_URL.startswith("sqlite:///") else "nutrivision.db")

# API Keys
GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")
GROQ_MODEL = os.getenv("GROQ_MODEL", "llama-3.1-8b-instant")

OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY", "")
OPENROUTER_MODEL = os.getenv("OPENROUTER_MODEL", "google/gemma-2-9b-it")
OPENROUTER_SITE = os.getenv("OPENROUTER_SITE", "http://localhost")
OPENROUTER_APP = os.getenv("OPENROUTER_APP", "NutriVision")

TAVILY_API_KEY = os.getenv("TAVILY_API_KEY", "")
USDA_API_KEY = os.getenv("USDA_API_KEY", "DEMO_KEY")

# Feature flags
ENABLE_GROCERY_MODE = os.getenv("ENABLE_GROCERY_MODE", "True").lower() == "true"
ENABLE_MENU_OCR = os.getenv("ENABLE_MENU_OCR", "True").lower() == "true"
ENABLE_AI_SIMULATOR = os.getenv("ENABLE_AI_SIMULATOR", "True").lower() == "true"
ENABLE_WEEKLY_REPORT = os.getenv("ENABLE_WEEKLY_REPORT", "True").lower() == "true"
