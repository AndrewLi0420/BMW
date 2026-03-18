"""
Google Gemini API client for real-time web search and data extraction.

Uses the google-genai SDK with the latest Gemini model to search for
battery industry facilities and news, returning structured JSON.
"""

from __future__ import annotations

import logging
import time

from google import genai
from google.genai import types

from config import (
    GEMINI_API_KEY,
    GEMINI_MODEL,
    MAX_RETRIES,
    RETRY_BACKOFF_FACTOR,
)

logger = logging.getLogger(__name__)


class GeminiClient:
    """Wrapper around the Google Gemini generative AI API."""

    def __init__(self, api_key: str | None = None) -> None:
        self.api_key = api_key or GEMINI_API_KEY
        if not self.api_key:
            raise ValueError(
                "GEMINI_API_KEY is not set. "
                "Export it or add it to your .env file."
            )
        self.client = genai.Client(api_key=self.api_key)

    # ── Low-level request ────────────────────────────────────────────────
    def _request(self, prompt: str) -> str:
        """Send a generate_content request with retry logic."""
        for attempt in range(1, MAX_RETRIES + 1):
            try:
                response = self.client.models.generate_content(
                    model=GEMINI_MODEL,
                    contents=prompt,
                    config=types.GenerateContentConfig(
                        tools=[types.Tool(google_search=types.GoogleSearch())]
                    ),
                )
                return response.text
            except Exception as exc:
                wait = RETRY_BACKOFF_FACTOR ** attempt
                logger.warning(
                    "Gemini API attempt %d/%d failed: %s — retrying in %.1fs",
                    attempt,
                    MAX_RETRIES,
                    exc,
                    wait,
                )
                if attempt == MAX_RETRIES:
                    raise
                time.sleep(wait)

        raise RuntimeError("Gemini API request failed after all retries")

    # ── High-level helpers ───────────────────────────────────────────────
    def search_facilities(self, segment: str) -> str:
        """
        Ask Gemini to find battery facilities in a given supply-chain
        segment and return the answer as a JSON array.
        """
        prompt = (
            "You are a research assistant specializing in the battery industry. "
            "Search for battery industry facilities in the "
            f'"{segment}" supply chain segment.\n\n'
            "Include companies with active or planned facilities in the US, "
            "Canada, and Mexico. Return as many facilities as you can find "
            "(aim for 10+).\n\n"
            "Return ONLY a valid JSON array — no markdown code fences, no "
            "explanation, no extra text. Each object must have these keys "
            "(use null for unknown values):\n"
            '  "status"                     — one of: Commercial, Paused Construction, '
            "Proposed, Pilot Plant, Under Construction, Operational, Closed\n"
            f'  "supply_chain_segment"       — exactly: "{segment}"\n'
            '  "company"                    — legal company name\n'
            '  "company_website"            — corporate URL\n'
            '  "naatbatt_member"            — true or false\n'
            '  "hq_city"                    — headquarters city\n'
            '  "hq_state"                   — headquarters state/province\n'
            '  "facility_name"              — name of the plant/center\n'
            '  "product_facility_type"      — general description (e.g., "Prismatic pouch cells")\n'
            '  "product"                    — specific chemistry/tech (e.g., "LFP", "NMC")\n'
            '  "facility_address"           — full street address\n'
            '  "facility_city"              — city of facility\n'
            '  "facility_state_or_province" — state/province of facility\n'
            '  "facility_country"           — country\n'
            '  "facility_zip"               — postal code\n'
            '  "facility_phone"             — contact number\n'
            '  "latitude"                   — float\n'
            '  "longitude"                  — float\n'
            '  "confidence_score"           — integer 0-100: your confidence this record is real and accurate\n'
            '  "citations"                  — JSON array of strings: direct URLs to the sources you used (e.g., ["https://reuters.com/...", "https://energy.gov/..."]). Use real, specific URLs always.\n'
        )
        return self._request(prompt)

    def verify_facilities(self, segment: str, companies: list[str]) -> str:
        """
        Ask Gemini to fact-check a list of companies for a given segment.
        Returns a JSON array with verification results per company.
        """
        company_list = "\n".join(f"- {c}" for c in companies)
        prompt = (
            "You are a battery industry expert performing a fact-check. "
            f'For the "{segment}" supply chain segment, verify each company below.\n\n'
            f"Companies:\n{company_list}\n\n"
            "Return ONLY a valid JSON array — no markdown code fences, no explanation. "
            "Each object must have these keys:\n"
            '  "company"            — exactly as given above\n'
            '  "exists"             — true if this is a real, verifiable company\n'
            '  "battery_related"    — true if genuinely active in the battery or energy storage industry\n'
            '  "verification_notes" — one sentence explaining your assessment\n'
        )
        return self._request(prompt)

    def search_news(self, company: str) -> str:
        """
        Ask Gemini to find recent battery industry news about a company
        and return the answer as a JSON array.
        """
        prompt = (
            "You are a research assistant specializing in the battery industry. "
            f'Search for the latest news about "{company}" in the battery or '
            "energy storage industry.\n\n"
            "Return the 5 most recent and relevant articles.\n\n"
            "Return ONLY a valid JSON array — no markdown code fences, no "
            "explanation, no extra text. Each object must have these keys "
            "(use null for unknown values):\n"
            '  "company_name"    — the company name\n'
            '  "headline"        — title of the article\n'
            '  "summary"         — 1-2 sentence summary\n'
            '  "source_url"      — link to the article\n'
            '  "date_published"  — date in YYYY-MM-DD format\n'
        )
        return self._request(prompt)
