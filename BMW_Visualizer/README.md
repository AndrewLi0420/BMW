# BMW Battery Intelligence Dashboard

Internal research tool for BMW's battery technology team to track US/Canada battery companies, partnerships, news, and conference proceedings.

## Quick Start

```bash
# 1. Copy and fill in your API keys
cp .env.example .env
# Edit .env with your ANTHROPIC_API_KEY and PERPLEXITY_API_KEY

# 2. Run everything
bash run.sh
```

Dashboard opens at **http://localhost:5173** · API docs at **http://localhost:8000/docs**

## Architecture

- **Backend**: FastAPI + SQLite (SQLAlchemy) on port 8000
- **Frontend**: React + Vite + Tailwind CSS on port 5173
- **AI**: Claude (`claude-sonnet-4-20250514`) + Perplexity for web search
- **Data**: NAATBatt XLSX (auto-downloaded from NREL on first run)

## Features

| Tab | Description |
|-----|-------------|
| Company Map | Leaflet map, markers color-coded by company type |
| Company Table | Searchable/sortable/paginated list, detail panel |
| News Feed | Filterable news headlines by category/company/date |
| Partnership Network | Force-directed graph of company partnerships |
| Research Panel | Discover companies, AI research, CSV/PDF upload |
| Conference Proceedings | Extracted papers, presentations, transcripts |

## NAATBatt Sync

- Auto-downloads on first run from NREL/NLR
- Weekly refresh every Sunday 02:00 AM (APScheduler)
- Manual sync via "Sync Now" button in navbar
- `GET /api/sync/status` · `POST /api/sync/naatbatt`

## Environment Variables

| Variable | Description |
|----------|-------------|
| `ANTHROPIC_API_KEY` | Claude API key |
| `PERPLEXITY_API_KEY` | Perplexity sonar API key |
| `DATABASE_URL` | SQLite path (default: `sqlite:///./battery_intel.db`) |
| `UPLOAD_DIR` | Upload directory (default: `./uploads`) |

## API Routes

```
GET  /api/companies          List/filter companies
GET  /api/companies/{id}     Company detail + news + proceedings
GET  /api/companies/map      Map markers
GET  /api/companies/network  Partnership graph {nodes, links}
POST /api/companies/research AI research a company
POST /api/companies/discover AI discover new companies

GET  /api/news               List/filter news
POST /api/news/search        AI news search

GET  /api/proceedings        List/filter proceedings

POST /api/upload/csv         Import CSV/XLSX
POST /api/upload/document    Extract from PDF/text via Claude

GET  /api/jobs/{id}          Poll job status
GET  /api/jobs               Recent jobs

GET  /api/sync/status        Last sync info
POST /api/sync/naatbatt      Trigger manual sync

POST /api/seed               Trigger seed import
GET  /api/seed/status        Seed status
```
