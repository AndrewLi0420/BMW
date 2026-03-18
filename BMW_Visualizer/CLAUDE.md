# BMW Visualizer

Internal research dashboard for BMW's battery technology team. Tracks US/Canada battery companies, industry partnerships, news, and conference proceedings. Uses Claude AI + Tavily for research. Displays data via interactive maps, network graphs, and tables. Auto-syncs weekly with the NAATBatt XLSX database from NREL.

## Tech Stack

**Backend:** Python 3.10+, FastAPI, SQLAlchemy, SQLite, Claude Sonnet (claude-sonnet-4-6), Tavily (web search), APScheduler, pdfplumber, pandas
**Frontend:** React 18, Vite 5, Tailwind CSS 3, Leaflet (maps), react-force-graph-2d (network graph), axios

## Project Structure

```
BMW_Visualizer/
  backend/
    main.py             # FastAPI entry point (port 8000)
    ai_research.py      # Claude + Tavily research logic
    models.py           # SQLAlchemy ORM
    database.py         # Session management + DB init
    config.py           # Env config (loads .env)
    seed.py             # NAATBatt XLSX importer
    scheduler.py        # APScheduler (weekly Sunday 02:00 AM sync)
    routes/
      companies.py
      news.py
      proceedings.py
      upload.py         # CSV/PDF/XLSX batch import
      jobs.py           # Async job status polling
      pipeline_sync.py  # NAATBatt sync trigger
  frontend/
    src/
      App.jsx           # Main router
      components/       # CompanyMap, CompanyTable, CompanyDetail,
                        # PartnershipNetwork, NewsFeed, ResearchPanel, Proceedings, Sidebar
    dist/               # Pre-built production assets
  data/                 # NAATBatt XLSX cache (auto-downloaded)
  uploads/              # User-uploaded files for batch import
  run.sh                # All-in-one startup script
  requirements.txt
  .env.example
```

## Commands

```bash
# Easiest — starts everything
bash run.sh

# Manual
source venv/bin/activate
pip install -r requirements.txt
python backend/main.py        # FastAPI → http://localhost:8000

cd frontend && npm install
cd frontend && npm run dev    # Vite dev server → http://localhost:5173
cd frontend && npm run build
```

## Environment

Copy `.env.example` → `.env` and set:
- `ANTHROPIC_API_KEY` — required (Claude)
- `TAVILY_API_KEY` — required (web search, formerly PERPLEXITY_API_KEY)
- `DATABASE_URL` — optional (defaults to `sqlite:///./battery_intel.db`)
- `UPLOAD_DIR` — optional (defaults to `./uploads`)

## API Routes

```
GET  /api/companies              List/filter with pagination
GET  /api/companies/{id}         Detail + related news + proceedings
GET  /api/companies/map          Map markers (lat/lng, type)
GET  /api/companies/network      Partnership graph {nodes, links}
POST /api/companies/research     AI research a company
POST /api/companies/discover     AI discover new companies

GET  /api/news                   List/filter news
POST /api/news/search            AI news search

GET  /api/proceedings            List/filter proceedings
POST /api/proceedings/upload     Extract from PDF/text

POST /api/upload/csv             Import CSV/XLSX
POST /api/upload/document        Extract data from PDF via Claude

GET  /api/jobs/{id}              Poll async job status
GET  /api/jobs                   Recent job history

GET  /api/sync/status            NAATBatt sync info + next scheduled run
POST /api/sync/naatbatt          Trigger manual NAATBatt sync
```

## Database

Four tables:
- `companies` — 47+ columns including financials, location, partnerships
- `news_headlines` — FK → companies (cascade delete)
- `proceedings` — conference papers/presentations
- `sync_log` — NAATBatt import history

Index on `company_name` for fast lookups.

## gstack
- Use the /browse skill from gstack for all web browsing
- Never use mcp__claude-in-chrome__* tools
- Available skills: /office-hours, /plan-ceo-review, /plan-eng-review, /plan-design-review, /design-consultation, /review, /ship, /browse, /qa, /qa-only, /design-review, /setup-browser-cookies, /retro, /debug, /document-release
- If gstack skills aren't working, run `cd .claude/skills/gstack && ./setup` to build the binary and register skills

## Key Patterns

- **NAATBatt sync:** XLSX auto-downloaded from NREL on first run; weekly refresh Sunday 02:00 AM via APScheduler. Manual trigger via `POST /api/sync/naatbatt`.
- **Async jobs:** Long-running AI tasks (research, discover, upload) are processed as background jobs. Poll `GET /api/jobs/{id}` for status. Jobs auto-expire after 3 days.
- **Claude model:** Hardcoded to `claude-sonnet-4-6` in `backend/config.py`.
- **Cross-pipeline sync:** References BMW_project's DB at `/Users/andrewli/Desktop/bmw/BMW_project/backend/battery_pipeline.db` for pipeline sync route.
- **File uploads:** CSV/XLSX go through `routes/upload.py`; PDF extraction uses Claude via the same route.
