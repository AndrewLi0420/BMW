# BMW Battery Industry Data Pipeline

Full-stack data pipeline that queries the Google Gemini AI API to discover and track battery supply chain facilities, extract structured data, and persist results as JSON. A React frontend provides browser-based execution and JSON download. A source validation pipeline checks the validity of every cited URL.

## Tech Stack

**Backend:** Python 3.10+, FastAPI, Pydantic 2.0, Google Gemini API (stdlib `urllib` for HTTP checks)
**Frontend:** React 18, Vite, Tailwind CSS
**Testing:** pytest

## Project Structure

```
backend/
  api/              # Gemini API client (note: file is named perplexity_client.py — legacy name, do not rename)
  pipeline/
    extractor.py        # Parse LLM output → Pydantic
    writer.py           # Write/merge/load pipeline JSON (replaces SQLite)
    source_validator.py # Validate cited source URLs; usable as library or CLI
    loader.py           # Legacy SQLite loader (kept for BMW_Visualizer pipeline_sync compat)
  db/               # Legacy SQLAlchemy ORM models (kept for BMW_Visualizer pipeline_sync compat)
  tests/            # pytest unit tests
  config.py         # Centralized env config (loads .env)
  schemas.py        # Pydantic validation schemas
  server.py         # FastAPI server (port 8001)
  main.py           # CLI entry point
  scheduler.py      # Weekly Monday 08:00 runner
  output/
    battery_pipeline.json   # Persistent output — all segments merged here
  requirements.txt
  .env.example
frontend/
  src/App.jsx       # Entire UI — segment selector, run button, JSON download
  vite.config.js    # /api proxy → localhost:8001
```

## Commands

```bash
# Backend (run from backend/)
cd backend && python server.py                                                      # API server → http://localhost:8001
cd backend && python main.py                                                        # Full pipeline (all 15 segments + news)
cd backend && python main.py --segments "Cell Manufacturing" "Recycling"            # Specific segments only
cd backend && python main.py --dry-run                                              # Print without writing to disk
cd backend && python main.py --no-news                                              # Skip news phase
cd backend && python main.py --validate-sources                                     # Run + validate all cited sources
cd backend && python main.py --output /tmp/run.json                                 # Custom output path
cd backend && python pipeline/source_validator.py --input output/battery_pipeline.json  # Validate sources standalone
cd backend && python -m pytest tests/ -v                                            # Run tests

# Frontend (separate terminal)
cd frontend && npm install
cd frontend && npm run dev    # Dev server → http://localhost:5173
cd frontend && npm run build  # Production build → frontend/dist/
```

## API Endpoints

| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/segments` | List all supply-chain segments |
| POST | `/api/run` | Run pipeline for one segment; returns facilities + citation validation |
| GET | `/api/data` | Return full pipeline JSON (all segments) |
| GET | `/api/download-json` | Download `battery_pipeline.json` as file attachment |
| POST | `/api/validate-sources` | Validate all cited source URLs in the pipeline JSON |

## Environment

Copy `backend/.env.example` → `backend/.env` and set:
- `GEMINI_API_KEY` — required

## Architecture

Data flows: CLI / Web UI → FastAPI → GeminiClient → extractor.py (Pydantic validation) → writer.py (merge into JSON)

Source validation: source_validator.py → concurrent HTTP HEAD/GET checks → citations_validation added to each facility

## JSON Output Schema

`output/battery_pipeline.json`:
```json
{
  "run_metadata": {
    "last_updated": "...",
    "total_facilities": N,
    "total_news": M,
    "source_validation_timestamp": "...",
    "sources_checked": N,
    "sources_valid": N,
    "sources_invalid": N,
    "sources_redirect": N,
    "sources_error": N
  },
  "facilities": [
    {
      "company": "...",
      "supply_chain_segment": "...",
      "citations": ["https://..."],
      "citations_validation": [
        { "url": "...", "status": "valid|invalid|redirect|error", "http_status": 200, "final_url": "...", "checked_at": "..." }
      ],
      ...all FacilitySchema fields...
    }
  ],
  "news": [
    {
      "company_name": "...",
      "headline": "...",
      "source_url": "...",
      "source_url_validation": { "url": "...", "status": "valid", ... },
      ...
    }
  ]
}
```

## Key Patterns

- **Deduplication:** Facilities merge on `(company, facility_name, facility_city)`; news merges on `(company_name, headline)` — repeated runs accumulate without duplicates.
- **LLM output parsing:** Gemini returns JSON embedded in prose; `extractor.py` strips markdown fences with regex before Pydantic validation.
- **Source validation:** `source_validator.py` performs concurrent HTTP HEAD (fallback GET) checks on all citation URLs and news source_urls, adding per-URL status dicts.
- **API proxy:** Vite dev server proxies `/api` → `http://localhost:8001` — no CORS issues in dev.
- **Segment list:** 15 supply chain segments are hardcoded in `config.py`; frontend reads them from `/api/segments`.
