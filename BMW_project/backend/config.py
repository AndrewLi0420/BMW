"""
Central configuration for the Battery Industry Data Pipeline.
Loads settings from environment variables / .env file.
"""

import os
from dotenv import load_dotenv

load_dotenv()

# ── API ──────────────────────────────────────────────────────────────────────
GEMINI_API_KEY: str = os.getenv("GEMINI_API_KEY", "")
GEMINI_MODEL: str = "gemini-2.5-pro"

# ── Database ─────────────────────────────────────────────────────────────────
DATABASE_URL: str = os.getenv("DATABASE_URL", "sqlite:///battery_pipeline.db")

# ── Supply‑Chain Segments (mirrors NAATBatt spreadsheet tabs) ────────────────
SUPPLY_CHAIN_SEGMENTS: list[str] = [
    "Raw Materials",
    "Battery Grade Materials",
    "Anodes",
    "Cathodes",
    "Electrolytes",
    "Separators",
    "Other Cell Components",
    "Cell Manufacturing",
    "Module & Pack Assembly",
    "BMS & Electronics",
    "Stationary Storage",
    "EV Integration",
    "Recycling",
    "Equipment & Machinery",
    "Research & Testing",
]

# ── Pipeline Defaults ────────────────────────────────────────────────────────
MAX_RETRIES: int = 3
RETRY_BACKOFF_FACTOR: float = 2.0  # seconds (exponential)
