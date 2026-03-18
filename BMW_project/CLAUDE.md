# BMW Battery Industry Data Pipeline

Full-stack data pipeline that queries the Google Gemini AI API to discover and track battery supply chain facilities, extract structured data, and persist it to SQLite. A React frontend provides browser-based execution and CSV export.

## Tech Stack

**Backend:** Python 3.10+, FastAPI, SQLAlchemy 2.0, Pydantic 2.0, SQLite, Google Gemini API
**Frontend:** React 18, Vite, Tailwind CSS
**Testing:** pytest

## Project Structure

```
backend/
  api/              # Gemini API client (note: file is named perplexity_client.py — legacy name, do not rename)
  pipeline/         # extractor.py (parse LLM output → Pydantic) + loader.py (upsert to DB)
  db/               # SQLAlchemy ORM models
  tests/            # pytest unit tests
  config.py         # Centralized env config (loads .env)
  schemas.py        # Pydantic validation schemas
  server.py         # FastAPI server (port 8000)
  main.py           # CLI entry point
  scheduler.py      # Weekly Monday 08:00 runner
  requirements.txt
  .env.example
frontend/
  src/App.jsx       # Entire UI — segment selector, run button, CSV download
  vite.config.js    # /api proxy → localhost:8000
```

## Commands

```bash
# Backend (run from backend/)
cd backend && python server.py                                           # API server → http://localhost:8000
cd backend && python main.py                                             # Full pipeline (all 15 segments + news)
cd backend && python main.py --segments "Cell Manufacturing" "Recycling" # Specific segments only
cd backend && python main.py --dry-run                                   # Print without writing to DB
cd backend && python main.py --no-news                                   # Skip news phase
cd backend && python -m pytest tests/ -v                                 # Run tests

# Frontend (separate terminal)
cd frontend && npm install
cd frontend && npm run dev    # Dev server → http://localhost:5173
cd frontend && npm run build  # Production build → frontend/dist/
```

## Environment

Copy `backend/.env.example` → `backend/.env` and set:
- `GEMINI_API_KEY` — required
- `DATABASE_URL` — optional (defaults to `sqlite:///battery_pipeline.db`)

## Architecture

Data flows: CLI / Web UI → FastAPI → GeminiClient → extractor.py (Pydantic validation) → loader.py (upsert to SQLite)

Two DB tables: `battery_facilities_full` (19 fields) and `battery_industry_news` (FK → facilities, cascade delete).

## Key Patterns

- **Deduplication:** Facilities use a composite unique key on `(company, facility_name, facility_city)` — always upsert, never raw insert.
- **LLM output parsing:** Gemini returns JSON embedded in prose; `extractor.py` strips markdown fences with regex before Pydantic validation.
- **API proxy:** Vite dev server proxies `/api` → `http://localhost:8000` — no CORS issues in dev.
- **Segment list:** 15 supply chain segments are hardcoded in both `backend/server.py` and `frontend/src/App.jsx` — keep them in sync if adding segments.
- **News search:** Skipped in `/api/run` for speed; full news pipeline only runs via CLI (`backend/main.py`) or the scheduler.
