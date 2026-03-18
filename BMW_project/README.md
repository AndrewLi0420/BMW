# BMW Battery Industry Data Pipeline

Automated data pipeline that searches for battery industry companies and news using Google Gemini AI, extracts structured data, and stores it in a SQLite database mirroring the NAATBatt Database schema.

## Features
- **AI-Powered Search**: Uses Gemini 2.5 Flash to find battery facility data and industry news
- **Pydantic Validation**: Validates zip codes, coordinates, URLs, and dates before DB insertion
- **Deduplication**: Composite key `(Company, Facility_Name, Facility_City)` prevents duplicates
- **Scheduled Automation**: Weekly pipeline runs via `scheduler.py`
- **Web UI**: Single-page React frontend to run segments and download CSV exports

## Setup
```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env   # add your GEMINI_API_KEY
```

## Running the Web UI

Start both the backend and frontend in separate terminals:

**Terminal 1 — API server:**
```bash
source venv/bin/activate
python server.py
# Runs at http://localhost:8000
```

**Terminal 2 — Frontend:**
```bash
cd frontend
npm install   # first time only
npm run dev
# Open http://localhost:5173
```

Pick a supply chain segment, click **Run Pipeline**, then **Download CSV** when it finishes.

## CLI Usage
```bash
# Full pipeline (all 15 segments)
python main.py

# Specific segments only
python main.py --segments "Cell Manufacturing" "Recycling"

# Dry run — print extracted data without writing to DB
python main.py --segments "Anodes" --dry-run

# Skip news search phase
python main.py --no-news

# Weekly scheduled runs (every Monday 08:00)
python scheduler.py

# Run tests
python -m pytest tests/ -v
```

## Tech Stack
Python 3.10+ · FastAPI · SQLAlchemy · Pydantic · Google Gemini API · SQLite · React · Vite · Tailwind CSS
