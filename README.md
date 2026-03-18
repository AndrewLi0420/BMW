# BMW Battery Intelligence — Full Stack

Two projects that work together:

- **BMW_project** — AI pipeline that uses Google Gemini to discover battery supply chain facilities. Runs on port **8001**.
- **BMW_Visualizer** — Rich dashboard for visualizing companies, maps, news, partnerships, and research. Runs on port **8000**.

The pipeline feeds into the Visualizer via a sync endpoint.

---

## First-Time Setup

### BMW_project (do this once)

```bash
cd BMW_project/backend
python3 -m venv venv
source venv/bin/activate
pip3 install -r requirements.txt
cp .env.example .env
# open .env and add your GEMINI_API_KEY
```

### BMW_Visualizer (do this once)

```bash
cd /Users/andrewli/BMW_Visualizer
python3 -m venv venv
source venv/bin/activate
pip3 install -r requirements.txt
cp .env.example .env
# open .env and add your ANTHROPIC_API_KEY and TAVILY_API_KEY

cd frontend
npm install
```

---

## Running Everything

You need **two terminals**.

### Terminal 1 — BMW_Visualizer (main dashboard)

```bash
cd /Users/andrewli/BMW_Visualizer
./run.sh
```

Opens at **http://localhost:5173**
API docs at **http://localhost:8000/docs**

### Terminal 2 — BMW_project pipeline

```bash
cd /Users/andrewli/Desktop/bmw/BMW_project/backend
source venv/bin/activate
python3 main.py
```

This runs the Gemini AI pipeline across all 15 supply chain segments and writes results to `battery_pipeline.db`. Takes a few minutes.

To run only specific segments:
```bash
python3 main.py --segments "Cell Manufacturing" "Recycling"
```

To preview without writing to DB:
```bash
python3 main.py --dry-run
```

---

## Syncing Pipeline Data into the Visualizer

After `python3 main.py` finishes, click **Import Pipeline** in the Visualizer navbar.

Or from the terminal:
```bash
curl -X POST http://localhost:8000/api/sync/pipeline
```

This maps the pipeline's `battery_facilities_full` → `companies` and `battery_industry_news` → `news_headlines` in the Visualizer DB. Safe to run multiple times — it deduplicates on company name and headline.

---

## Ports

| Service | Port |
|---|---|
| BMW_Visualizer backend | 8000 |
| BMW_Visualizer frontend | 5173 |
| BMW_project backend | 8001 |

---
## When opening new terminal
"deactivate" if you want to exit venv

source ~/.zshrc if "zsh: command not found:"

---


---

## Environment Variables

### BMW_project (`BMW_project/backend/.env`)
```
GEMINI_API_KEY=your_key_here
DATABASE_URL=sqlite:///battery_pipeline.db   # optional
```

### BMW_Visualizer (`BMW_Visualizer/.env`)
```
ANTHROPIC_API_KEY=your_key_here
TAVILY_API_KEY=your_key_here
DATABASE_URL=sqlite:///./battery_intel.db    # optional
PIPELINE_DB_PATH=/Users/andrewli/Desktop/bmw/BMW_project/backend/battery_pipeline.db  # optional
```


