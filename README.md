# Government Meeting Scraper

Robust web scraper for extracting meeting metadata from government websites with automatic retry, bot detection avoidance, and incremental saving.

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                       User Input                             │
│              (JSON with URLs & Date Range)                   │
└────────────────────┬────────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────────┐
│                    scraper.py (CLI)                          │
│              Command-line interface handler                  │
└────────────────────┬────────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────────┐
│                  ScraperEngine (core/engine.py)              │
│   • Orchestrates scraping workflow                          │
│   • Manages browser pool & HTTP requests                    │
│   • Handles retries & rate limiting                         │
└────────┬───────────────────────────────┬────────────────────┘
         │                               │
         ▼                               ▼
┌──────────────────────┐      ┌──────────────────────────┐
│   Browser Manager    │─────▶│   Site-Specific          │
│   (core/browser.py)  │      │   Extractors             │
│                      │      │   (extractors/*)         │
│ • Playwright setup   │      │                          │
│ • Stealth mode       │      │ • Uses browser to load   │
│ • Anti-detection     │      │ • Detects site type      │
│ • Auto-scroll        │      │ • Extracts meetings      │
└──────────────────────┘      │ • Parses dates           │
                              │ • Links classification   │
                              └────────────┬─────────────┘
                                           │
                                           ▼
                              ┌─────────────────────────┐
                              │    Data Validation      │
                              │                         │
                              │ • Date range filter     │
                              │ • URL verification      │
                              │ • Duplicate removal     │
                              └────────────┬────────────┘
                                           │
                                           ▼
                              ┌─────────────────────────┐
                              │   JSON Output           │
                              │   (outputs/*.json)      │
                              └─────────────────────────┘
```

**Key Features:**
- Sequential processing with incremental saving
- Automatic retry with exponential backoff
- Bot detection avoidance with stealth mode
- Rate limiting (2 req/sec per domain)
- Zero false positives

---

## 📦 Setup

**Prerequisites:** Python 3.8+

```bash
bash setup.sh
```

This installs dependencies, Playwright browser, and creates necessary directories.

---

## 🚀 Usage

### Problem 1: Scrape Meeting Metadata

```bash
bash run.sh
```

Scrapes 6 government websites (Nov 20, 2024 - Nov 26, 2025):
- cityofventura.ca.gov/AgendaCenter
- bethlehem-pa.gov/Calendar
- lansdale.org/CivicMedia
- facebook.com/DauphinCountyPA/videos
- go.boarddocs.com/ca/acoe/Board.nsf/Public
- simbli.eboardsolutions.com (S=36030373)

**Output:** `outputs/problem1_complete_output.json` (saves after each domain)

### Custom Input

Create input file:
```json
{
  "start_date": "2024-01-01",
  "end_date": "2024-12-31",
  "base_urls": ["https://your-site.gov/meetings"]
}
```

Run:
```bash
python scraper.py scrape-meetings -i inputs/your_input.json -o outputs/your_output.json
```

### Problem 2: Resolve URLs

```bash
python scraper.py resolve-urls -i examples/problem2_input.json -o outputs/problem2_output.json
```

### Bonus Task: Universal Scraper

```bash
python scraper.py universal-scrape -i examples/bonus_input.json -o outputs/bonus_output.json
```

---

## 📋 Input/Output

**Input:**
```json
{
  "start_date": "2024-11-20",
  "end_date": "2025-11-26",
  "base_urls": ["https://example.gov/meetings"]
}
```

**Output:**
```json
[
  {
    "base_url": "https://example.gov/meetings",
    "medias": [
      {
        "meeting_url": "https://www.youtube.com/watch?v=...",
        "agenda_url": "https://example.gov/agenda.pdf",
        "minutes_url": "https://example.gov/minutes.pdf",
        "title": "City Council Meeting",
        "date": "2024-11-20"
      }
    ]
  }
]
```

---

## 📁 Project Structure

```
scraping/
├── scraper.py              # CLI interface
├── setup.sh                # Installation
├── run.sh                  # Run Problem 1
├── inputs/                 # Input JSON files
├── outputs/                # Generated outputs (incremental saves)
├── logs/                   # Application logs
└── src/
    ├── core/               # Engine & browser management
    ├── extractors/         # Site-specific extraction logic
    ├── storage/            # Data models
    └── utils/              # Helpers & logging
```

---

## 🔧 Configuration

Edit `src/storage/models.py`:
- **Rate Limit**: `rate_limit=2` (requests/sec per domain)
- **Max Retries**: `max_retries=3`
- **Browser Timeout**: `timeout=60` (seconds)

---

## 🐛 Troubleshooting

**Virtual environment:**
```bash
source .venv/Scripts/activate  # Windows
source .venv/bin/activate      # Linux/Mac
```

**Browser missing:**
```bash
playwright install chromium
```

---

## 🎯 Assignment Coverage

✅ Problem 1: Meeting metadata with date filtering  
✅ Problem 2: Video/document URL resolution  
✅ Bonus Task: Universal scraper (40+ sites)

---

**Note:** For ethical scraping of public government data only.
