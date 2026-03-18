# BMW Battery Intelligence — System Pipeline

## What This System Does

This platform tracks every company in the global battery supply chain — from raw material miners to electric vehicle manufacturers. It collects, verifies, and displays structured intelligence so BMW can monitor partnerships, technologies, funding activity, and emerging players across the entire battery ecosystem.

There are two connected applications:

- **BMW Visualizer** — the main research dashboard: a web app with maps, network graphs, news feeds, and company profiles
- **BMW Pipeline** — a background data discovery engine: automatically finds new battery facilities and companies using AI

---

## The Big Picture: How Data Moves Through the System

```
┌────────────────────────────────────────────────────────────────────────┐
│                        DATA SOURCES                                    │
│                                                                        │
│   NAATBatt Database       AI Web Search        User File Uploads       │
│   (Excel spreadsheet)     (Claude + Tavily)    (CSV, XLSX, PDF)        │
│         │                       │                      │               │
└─────────┼───────────────────────┼──────────────────────┼───────────────┘
          │                       │                      │
          ▼                       ▼                      ▼
┌─────────────────────────────────────────────────────────────────────┐
│                     DATA PIPELINE                                    │
│                                                                     │
│  1. Ingest → 2. Normalize → 3. Validate → 4. Verify → 5. Store     │
│                                                                     │
└─────────────────────────────────────────────────────────────────────┘
          │
          ▼
┌──────────────────────────────────────────────────────────────┐
│                    DATABASE                                   │
│                                                              │
│   Companies │ News Headlines │ Proceedings │ Sync Logs       │
│                                                              │
└──────────────────────────────────────────────────────────────┘
          │
          ▼
┌────────────────────────────────────────────────────────────────────────┐
│                     VISUALIZER (USER-FACING)                           │
│                                                                        │
│   Map View  │  Table View  │  News Feed  │  Partnership Graph          │
│   Research Panel  │  Conference Proceedings                            │
└────────────────────────────────────────────────────────────────────────┘
```

---

## Data Source 1: The NAATBatt Excel Database

**What it is:** NAATBatt International (National Alliance for Advanced Technology Batteries) publishes an Excel database of battery supply chain companies in North America, maintained by the National Renewable Energy Laboratory (NREL). This is the primary seed for the entire system.

**What it contains:** 12 sheets covering every major supply chain segment — raw materials, cell manufacturing, recycling, equipment, R&D, modeling, services, and more.

### Step-by-Step: How NAATBatt Data Enters the System

```
Step 1 — DOWNLOAD
  ↓
  The system checks if the file has changed since last time
  (using a SHA256 fingerprint — like a unique checksum for the file)
  If unchanged → skip download, use cached version
  If changed → download fresh copy and save it

Step 2 — PARSE
  ↓
  Read all 12 sheets that contain a "Company" column
  Strip extra whitespace from all column names
  Handle duplicate column names (take the first non-empty value)

Step 3 — NORMALIZE
  ↓
  Map supply chain segment names to standard company types:
  ┌──────────────────────────────────────────────────────────┐
  │ Raw Materials             → materials supplier           │
  │ Battery Grade Materials   → materials supplier           │
  │ Other Battery Components  → materials supplier           │
  │ Electrode & Cell Mfg      → cell supplier                │
  │ Module-Pack Manufacturing → cell supplier                │
  │ Recycling-Repurposing     → recycler                     │
  │ Equipment                 → equipment supplier           │
  │ R&D                       → R&D                         │
  │ Services & Consulting     → services                     │
  │ Modeling & Software       → modeling/software            │
  │ Distributors              → services                     │
  │ Professional Services     → services                     │
  └──────────────────────────────────────────────────────────┘

Step 4 — DEDUPLICATE
  ↓
  Normalize company names (lowercase, strip spaces) for comparison
  If the same company appears on multiple sheets:
    → Merge their facility locations into one list
    → Combine their supply chain focus areas
    → Keep the most specific classification

Step 5 — GEOCODE
  ↓
  For any company with a city/state but no latitude/longitude:
    → Look up coordinates using OpenStreetMap (Nominatim service)
    → Wait 1 second between lookups to respect rate limits
    → If lookup fails, leave coordinates blank

Step 6 — UPSERT INTO DATABASE
  ↓
  For each company:
    If company name already exists in database (case-insensitive match):
      → Update NAATBatt-sourced fields only
      → Preserve any AI-enriched data already there
    If company is new:
      → Create a new record with all parsed fields

Step 7 — LOG THE SYNC
  ↓
  Record: {source, status, rows added, rows updated, timestamp}
  This creates an audit trail of every sync operation
```

**When does this run?**
- Automatically every Sunday at 2:00 AM UTC
- Manually via the "Sync" button in the app
- Automatically on first server startup if the database is empty

---

## Data Source 2: AI-Powered Research

**What it is:** The system can research any company — or discover new ones — using Claude (Anthropic's AI) combined with Tavily (a search engine built for AI). All research jobs run in the background so the user doesn't have to wait.

### Company Research Pipeline

```
User enters a company name → research job created in database

┌─────────────────────────────────────────────────────────┐
│ STEP 1: WEB SEARCH                                      │
│                                                         │
│ Search 1: "[Company] battery overview"                  │
│ Search 2: "[Company] OEM deals joint ventures"          │
│                                                         │
│ Tool used: Tavily (preferred) → Claude web search       │
│            (fallback if Tavily unavailable)             │
└──────────────────────┬──────────────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────────────┐
│ STEP 2: AI SYNTHESIS                                    │
│                                                         │
│ Claude reads the search results and extracts:           │
│                                                         │
│ • Company type (start-up, cell supplier, EV OEM, etc.) │
│ • Operating status (Commercial, Pilot Plant, etc.)     │
│ • Keywords from a defined list of 20+ battery terms:   │
│   solid-state, sodium-ion, LFP, NMC, anode, cathode,  │
│   electrolyte, silicon, LLZO, recycling, dry electrode  │
│ • Announced partnerships:                              │
│     - Partner name                                     │
│     - Type (Joint Venture / Investment / MOU /         │
│             Off-take / Supply Agreement / Other)       │
│     - Scale (e.g., "$500M", "20 GWh capacity")        │
│     - Date (year or year-month)                        │
│ • Business summary (3–5 sentences)                     │
│ • HQ location (city, state, country)                   │
│ • Financial data: employees, market cap, revenue,      │
│   total funding, last fundraise date (all in USD M)   │
│ • Company website                                      │
└──────────────────────┬──────────────────────────────────┘
                       │
                       ▼ (runs in parallel)
┌─────────────────────────────────────────────────────────┐
│ STEP 3: NEWS SEARCH (parallel with synthesis)           │
│                                                         │
│ Search: "[Company] battery news funding partnership     │
│          announcement milestone 2023-2025"              │
│                                                         │
│ Claude extracts up to 10 news items per company:        │
│ • Headline                                              │
│ • Category (funding / partnership / product launch /   │
│              facility / regulatory / market /           │
│              research / other)                          │
│ • Partners mentioned                                    │
│ • Source name and URL                                   │
│ • Date (YYYY-MM-DD, YYYY-MM, or YYYY)                  │
│ • Location                                              │
│ • Topics (2–5 relevant tags)                           │
│ • Short summary                                         │
└──────────────────────┬──────────────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────────────┐
│ STEP 4: UPSERT TO DATABASE                              │
│                                                         │
│ Company data → upsert into Companies table              │
│ News items   → insert into News Headlines table         │
│ Job status   → updated to "complete"                    │
└─────────────────────────────────────────────────────────┘
```

### Company Discovery Pipeline

Used to find battery companies not yet in the database:

```
User selects a supply chain segment (e.g., "Anodes") → discovery job created

Step 1: AI searches for companies in that segment
  - "battery [segment] companies startups..."
  - "site:crunchbase.com OR site:pitchbook.com [segment] battery companies"

Step 2: Claude extracts a list of 15–25 company names

Step 3: Deduplicate against existing database
  - Case-insensitive name matching
  - Only return companies not already tracked

Step 4: Return list to user for review
  (User can then trigger research on any discovered company)
```

### Document Extraction Pipeline

For uploaded PDFs, text files, or Markdown documents:

```
User uploads file (PDF / TXT / MD)
    ↓
Extract raw text (pdfplumber for PDFs)
    ↓
Claude reads the full document and extracts:
  • Companies mentioned → structured company records
  • News events mentioned → news headlines
  • Conference papers mentioned → proceedings records
    ↓
All extracted entities stored in database under appropriate tables
```

---

## Data Source 3: File Uploads

Users can upload structured data from industry databases:

### CSV / Excel Upload

Supported export formats with automatic format detection:

```
┌────────────────────────────────────────────────────────────────────┐
│ FORMAT DETECTION                                                   │
│                                                                    │
│ Crunchbase Organizations: columns "Organization Name" +            │
│                           "Total Funding" + "Last Funding"         │
│                                                                    │
│ Crunchbase Funding Rounds: columns "Organization Name" +           │
│                            "Money Raised" + "Announced Date" +     │
│                            "Funding Type"                          │
│                                                                    │
│ PitchBook Companies: columns "Total Raised" +                      │
│                      "Post-Money Valuation" + "Last Financing"     │
│                                                                    │
│ PitchBook Deals: columns "Deal Date" + "Deal Type" +              │
│                  "Investors" + "Deal Size"                         │
│                                                                    │
│ Generic CSV/XLSX: any file with a "company_name" column           │
└────────────────────────────────────────────────────────────────────┘
```

**Money field parsing** (handles messy real-world data):
```
"$1.2B"  → 1,200.0 (millions)
"$500M"  → 500.0
"$50K"   → 0.05
"1,500"  → 1,500.0 (assumed millions if raw number > 1,000,000)
```

**Employee field parsing:**
```
"100-250" → 175 (average of range)
"1,000+"  → 1,000
"500"     → 500
```

**Deal type normalization** (maps messy export labels to standard types):
```
"joint venture"                  → Joint Venture
"off-take" or "offtake"         → Off-take
"supply agreement"              → Supply Agreement
"mou", "strategic", "alliance"  → MOU
"merger", "acquisition"         → Other
(anything else)                  → Investment
```

---

## The BMW Pipeline App: Automated Facility Discovery

This is a dedicated standalone application — separate from the Visualizer — that uses Google's Gemini AI to discover battery facilities across North America. A user triggers it manually through a clean web interface, and the results flow back into the main Visualizer database for display on maps, tables, and news feeds.

It runs at: `http://localhost:5173` (development) or port 8001 in production.

---

### The Pipeline App User Interface

The app opens to a single focused page:

```
┌──────────────────────────────────────────────────────────────┐
│  BMW Group                           Battery Intelligence     │
├──────────────────────────────────────────────────────────────┤
│                                                              │
│              Welcome, BMW                                    │
│   Battery supply chain data, powered by Gemini AI.          │
│   Select a segment below and run the pipeline to fetch       │
│   the latest facilities.                                     │
│                                                              │
│  ┌──────────────────────────────────────────────────────┐   │
│  │ Supply Chain Segment                                  │   │
│  │ [  Raw Materials                                ▾  ] │   │
│  │                                                       │   │
│  │            [ Run Pipeline ]                           │   │
│  └──────────────────────────────────────────────────────┘   │
│                                                              │
│        Data sourced via Gemini AI · North America focus      │
└──────────────────────────────────────────────────────────────┘
```

**How a user interacts with it:**

1. **Select a segment** — choose one of 15 supply chain categories from the dropdown (Raw Materials, Cell Manufacturing, Recycling, etc.)
2. **Click "Run Pipeline"** — triggers the full 5-phase pipeline for that segment
3. **Watch it run** — the button shows a spinner, a progress bar animates across the screen, and a live stopwatch counts elapsed seconds with the label "Querying Gemini and verifying data…"
4. **See results** — once complete, a results panel appears below the button
5. **Download CSV** — export all discovered facilities for the segment as a spreadsheet

**While the pipeline runs, the segment selector and Run button are disabled** so the user can't accidentally start two pipelines at once.

---

### What the Results Look Like

After the pipeline finishes, the results panel shows a summary line:

```
Found 14 facilities for Cell Manufacturing
(3 new, 11 updated) · 7 news articles added
```

Below that, every discovered facility is shown as a card:

```
┌────────────────────────────────────────────────────────┐
│  Panasonic Energy of North America          [87%] [Verified] [✓] │
│  Gigafactory Nevada · Sparks · NV                      │
│                                                        │
│  Show sources (3)  ›                                   │
└────────────────────────────────────────────────────────┘
```

Each card shows:
- **Company name** (bold) and facility name, city, state
- **Confidence badge** — color-coded percentage showing how confident Gemini was:
  - Green (80–100%) = High confidence
  - Yellow (60–79%) = Medium confidence
  - Red (0–59%) = Low confidence
- **Verification badge** — result of the fact-check pass:
  - Green "Verified" = exists and is genuinely battery-related
  - Yellow "Uncertain" = exists but unclear if battery-related
  - Red "Unverified" = could not confirm the company exists
- **Website icon** — live check result:
  - ✓ green = website responded successfully (clickable link)
  - ✗ red = website did not respond
  - ? gray = no website provided
- **Expandable sources** — click "Show sources (N)" to see the citation URLs Gemini used as evidence. Broken links are filtered out automatically before display.

A credibility legend in the top-right corner of the results explains the color coding: High / Med / Low confidence.

---

### Full Pipeline Execution (5 Phases)

```
User clicks "Run Pipeline" for a segment (e.g., "Cell Manufacturing")

╔══════════════════════════════════════════════════════════════╗
║  PHASE 1: FACILITY SEARCH                                    ║
║                                                              ║
║  Gemini AI is asked to find 10+ battery facilities           ║
║  in the selected segment across US, Canada, Mexico           ║
║                                                              ║
║  For each facility, Gemini returns:                          ║
║  • Company name and website                                  ║
║  • Facility name, address, city, state, country, zip        ║
║  • Product type and specific product                         ║
║  • Operating status                                          ║
║  • Latitude and longitude                                    ║
║  • Confidence score (0–100, self-reported by AI)            ║
║  • Citation URLs (sources the AI used as evidence)          ║
╚══════════════════════╦═══════════════════════════════════════╝
                       ║
                       ▼
╔══════════════════════════════════════════════════════════════╗
║  PHASE 2: EXTRACTION & VALIDATION                           ║
║                                                              ║
║  Raw AI output is parsed and validated:                      ║
║                                                              ║
║  • Strip markdown formatting from AI response               ║
║    (AI sometimes wraps JSON in code blocks — removed)       ║
║  • Validate each facility against strict rules:             ║
║                                                              ║
║    supply_chain_segment → must match one of 15 segments     ║
║    facility_zip         → must match US postal format       ║
║                           (12345 or 12345-6789)             ║
║                           OR international postal code       ║
║    latitude             → must be between -90 and 90        ║
║    longitude            → must be between -180 and 180      ║
║    company_website      → must be a valid URL               ║
║                           (https:// added automatically     ║
║                            if the scheme is missing)         ║
║    confidence_score     → must be an integer 0–100          ║
║    citations            → array of URLs                     ║
║                                                              ║
║  Any facility that fails validation is logged and skipped.  ║
║  The pipeline continues with the valid records.             ║
╚══════════════════════╦═══════════════════════════════════════╝
                       ║
                       ▼
╔══════════════════════════════════════════════════════════════╗
║  PHASE 3: VERIFICATION PASS                                 ║
║                                                              ║
║  A second, separate Gemini call fact-checks each company:   ║
║    "Does this company actually exist?"                      ║
║    "Is it genuinely battery-related?"                       ║
║    "Any verification notes?"                                ║
║                                                              ║
║  This is intentionally a separate AI call from Phase 1 —   ║
║  it acts as an independent second opinion.                  ║
║                                                              ║
║  Results mapped to 3 statuses:                              ║
║                                                              ║
║  ✅ Verified   → exists AND is battery-related              ║
║  ❓ Uncertain  → exists but unclear if battery-related      ║
║  ❌ Unverified → does not appear to exist                   ║
║                                                              ║
║  If this phase fails (e.g., API error), the pipeline        ║
║  continues without verification rather than stopping.       ║
╚══════════════════════╦═══════════════════════════════════════╝
                       ║
                       ▼
╔══════════════════════════════════════════════════════════════╗
║  PHASE 4: WEBSITE & CITATION REACHABILITY CHECKS            ║
║                                                              ║
║  Two parallel batches of HTTP checks run simultaneously:    ║
║                                                              ║
║  Batch A — Company websites (10 parallel requests)          ║
║    Checks if the company's official website responds        ║
║    Timeout: 5 seconds per request                           ║
║    Result:  True (up) / False (down) / None (no URL)        ║
║                                                              ║
║  Batch B — Citation URLs (up to 20 parallel requests)       ║
║    Checks every source URL Gemini cited as evidence         ║
║    Any citation URL that returns an error is removed        ║
║    from the results before showing them to the user         ║
║    (dead links are filtered out, not just flagged)          ║
║                                                              ║
║  If ALL citations for a facility are dead links, the        ║
║  facility is kept — it may still be real — but its         ║
║  citations list is cleared rather than deleted entirely.    ║
╚══════════════════════╦═══════════════════════════════════════╝
                       ║
                       ▼
╔══════════════════════════════════════════════════════════════╗
║  PHASE 5: DATABASE UPSERT                                   ║
║                                                              ║
║  Each validated, verified facility is saved with            ║
║  deduplication to prevent double-counting:                  ║
║                                                              ║
║  Unique key: (company name + facility name + facility city) ║
║                                                              ║
║  If that combination already exists → update all fields     ║
║  If it's new → insert as a new record                       ║
║                                                              ║
║  Returns counts: {facilities found, added, updated}         ║
╚══════════════════════╦═══════════════════════════════════════╝
                       ║
                       ▼
╔══════════════════════════════════════════════════════════════╗
║  PHASE 6: NEWS SEARCH (per company)                         ║
║                                                              ║
║  For every company found in this run, Gemini is asked       ║
║  to find the 5 most recent news articles about them.        ║
║                                                              ║
║  Each article stored:                                        ║
║    • Headline                                               ║
║    • Summary                                                ║
║    • Source URL                                             ║
║    • Date published                                         ║
║                                                              ║
║  Linked to the company's facility record by foreign key.    ║
║  Returns count of news articles added.                      ║
╚══════════════════════════════════════════════════════════════╝
```

---

### CSV Download

After results appear, a "Download CSV" button exports every facility for the selected segment as a spreadsheet. The file is named automatically, e.g. `cell_manufacturing_facilities.csv`.

The CSV includes all 23 fields per facility:

| Column | What it contains |
|---|---|
| id | Database row ID |
| status | Operating status (Operational, Under Construction, etc.) |
| supply_chain_segment | Which of the 15 segments |
| company | Company name |
| company_website | Company website URL |
| naatbatt_member | Whether the company is a NAATBatt member |
| hq_city / hq_state | Headquarters location |
| facility_name | Name of this specific facility |
| product_facility_type | Type of production facility |
| product | What product is made there |
| facility_address / city / state / country / zip / phone | Full address |
| latitude / longitude | GPS coordinates |
| confidence_score | AI confidence (0–100) |
| citations | Source URLs used by AI |
| website_reachable | Whether website check passed |
| verification_status | Verified / Uncertain / Unverified |

---

### Other Ways to Run the Pipeline

In addition to the web UI, the pipeline can also be triggered from the command line (useful for bulk operations or scheduled runs):

```
Run all 15 segments at once:
  python main.py

Run specific segments:
  python main.py --segments "Cell Manufacturing" "Recycling"

Test run without writing to database:
  python main.py --dry-run

Skip the news phase:
  python main.py --no-news
```

There is also an automatic scheduler that runs the full pipeline every Monday at 8:00 AM, keeping the database current without manual intervention.

---

## The Database: What Gets Stored

There are two databases. The Visualizer has the main research database; the Pipeline app has a separate facilities database that syncs into the Visualizer.

### Company Records (43+ fields per company)

Every company tracked has a rich profile. Key fields:

| Category | Fields Stored |
|---|---|
| **Identity** | Name (unique), NAATBatt ID, membership status |
| **Location** | HQ city, state, country, latitude, longitude |
| **Classification** | Company type, operating status, supply chain segment |
| **Technology** | Battery chemistries (LFP, NMC, solid-state, etc.), feedstock materials, technology keywords |
| **Business** | Employees, market cap, annual revenue, total funding raised, last fundraise date |
| **Partnerships** | Partner name, partnership type, scale, date — stored as a list |
| **Facilities** | All facility locations with address, product, capacity, status |
| **Contact** | Name, email, phone |
| **Content** | 3–5 sentence summary, long description, free-form notes |
| **Provenance** | Data source (NAATBatt / AI research / file upload / pipeline sync), last updated timestamp |

### News Headlines

Each news article linked to a company stores:
- Headline, category, source name, URL, date
- Partners mentioned, location, topic tags
- 2–3 sentence summary

**Categories:** funding, partnership, product launch, facility, regulatory, market, research, other

### Conference Proceedings

Research papers and presentations linked to a company store:
- Title, event name, date, location
- Authors list
- Technologies referenced
- Partners mentioned
- Results summary
- Source URL or uploaded file path

### Research Jobs

Every background AI research operation is tracked:
- Job type (company research / news search / discovery / document extraction / bulk research)
- Status (pending → running → complete / failed)
- Target (company name or search query)
- Result (full JSON output)
- Timestamps for creation and last update

### Sync Logs

Every data import is logged:
- Source (NAATBatt spreadsheet or pipeline sync)
- Status (success / failed)
- Rows added and updated
- Any error message
- Timestamp

---

## The Visualizer: What Users See

### Map View
- Interactive map with a pin for every company
- Pins are color-coded by company type
- Sidebar filters: search by name, filter by type, status, segment, country
- Click any pin → opens full company profile panel

### Table View
- Same data as the map, in sortable columns
- Same filter set as map view

### News Feed
- Chronological stream of all tracked news articles
- Filters: category, date range, company name, keyword search

### Partnership Network Graph
- Visual web of all known partnerships
- Blue nodes = companies in the database
- Gray nodes = external partners not yet in the database
- Lines colored by partnership type
- Click any node → opens company profile

### Research Panel
- **Research a company:** Enter any company name, AI researches and enriches it
- **Discover companies:** Pick a supply chain segment, AI finds new companies
- **Custom search:** Free-text query, AI synthesizes results
- **Bulk research:** Enter up to 10 company names, queue research jobs for all of them
- All jobs run in the background; the panel polls every 5 seconds for completion

### Conference Proceedings
- Browse, search, and filter all tracked research papers and presentations
- Filter by technology type, company, or free-text search

### Company Detail Panel
- Full profile for any selected company
- All 43+ fields displayed
- 5 most recent news articles
- 10 most recent proceedings

---

## Async Job System

Research operations are slow (they involve web searches and AI processing). The system handles this gracefully:

```
User triggers research
      ↓
Job created in database with status: "pending"
      ↓
Background worker picks it up → status: "running"
      ↓
AI search + synthesis executes
      ↓
Results written to database → status: "complete" (or "failed")
      ↓
Frontend polls /api/jobs/{id} every 5 seconds
      ↓
When "complete" → display results to user
```

Every job stores its full result as JSON so it can be inspected or replayed later.

---

## Cross-System Sync: How the Pipeline Feeds the Visualizer

The Pipeline app and the Visualizer are two separate applications with separate databases. The Pipeline discovers facilities; the Visualizer is the main research hub where BMW actually reads and analyzes data. Syncing bridges the two.

```
TWO SEPARATE DATABASES:

  battery_pipeline.db          battery_intel.db
  (BMW Pipeline App)    ──→    (BMW Visualizer)
  battery_facilities_full      Companies table
  battery_industry_news        NewsHeadline table
```

**How to trigger a sync:** In the Visualizer, go to Sync → "Sync from Pipeline". This can also be triggered automatically.

```
Step 1: Read all facilities from battery_pipeline.db
      ↓
Step 2: For each facility, upsert into Visualizer's Companies table
  • Match on company name (case-insensitive)
  • If company already exists → update only the pipeline-sourced fields,
    preserve any AI-enriched data (summaries, keywords, partners, etc.)
  • If company is new → create a fresh record
      ↓
Step 3: Read all news from battery_pipeline.db
  • Resolve company name → company ID in Visualizer database
  • Deduplicate: skip any article already stored (matched by company + headline)
  • Insert only new articles
      ↓
Step 4: Mark each synced record with data_source = "pipeline_sync"
        so analysts can see where the data came from
      ↓
Step 5: Return sync summary:
  {companies added, companies updated, news added, news skipped}
```

**What this means in practice:** A user can run the Pipeline app to discover a new batch of cell manufacturers, then immediately open the Visualizer and sync. Those companies will now appear on the map, in the table, and in the news feed — complete with the verification status, confidence scores, and website checks that the Pipeline already performed. Any additional AI research done in the Visualizer (summaries, partnership data, keywords) is preserved and not overwritten by future syncs.

---

## Data Quality and Verification Summary

The system has multiple layers of verification at every stage:

| Layer | Method | What It Checks |
|---|---|---|
| **File integrity** | SHA256 hash | NAATBatt file hasn't been silently corrupted |
| **Schema validation** | Pydantic rules | Coordinates in range, ZIP code format, valid URLs |
| **AI fact-checking** | Gemini verification pass | Company exists, is genuinely battery-related |
| **Website liveness** | HTTP HEAD request | Company website actually responds |
| **Deduplication** | Normalized name matching | Same company not added twice |
| **Source tracking** | `data_source` field | Every record knows where it came from |
| **Audit logging** | SyncLog table | Every import leaves a timestamped record |
| **Confidence scoring** | AI self-report (0–100) | AI's own confidence in each facility record |
| **Verification status** | Verified / Uncertain / Unverified | Clear quality signal on every facility |

---

## Supply Chain Segments Tracked

The system organizes the entire battery supply chain into 15 segments:

1. Raw Materials
2. Battery Grade Materials
3. Anodes
4. Cathodes
5. Electrolytes
6. Separators
7. Other Cell Components
8. Cell Manufacturing
9. Module & Pack Assembly
10. BMS & Electronics
11. Stationary Storage
12. EV Integration
13. Recycling
14. Equipment & Machinery
15. Research & Testing

---

## Technology Keywords Tracked

The system tracks which companies work on these specific battery technologies:

`solid-state` · `sodium-ion` · `lithium metal` · `anode` · `cathode` · `electrolyte` · `silicon` · `prelithiation` · `LLZO` · `lithium-sulfur` · `AI` · `simulation` · `LFP` · `anode-free` · `polymer` · `current collector` · `separator` · `sulfidic electrolyte` · `NMC` · `NCA` · `NCMA` · `dry electrode` · `formation` · `recycling` · `second-life`

---

## Partnership Types Tracked

| Type | Description |
|---|---|
| **Joint Venture** | Two companies form a new shared entity |
| **Investment** | One company invests capital in another |
| **MOU** | Memorandum of Understanding — intent to cooperate |
| **Off-take** | Agreement to purchase output (e.g., battery cells) |
| **Supply Agreement** | Formal supply contract |
| **Other** | M&A, acquisitions, other deal types |
