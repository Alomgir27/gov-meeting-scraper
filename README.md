# Government Meeting Scraper

Robust web scraper for extracting meeting metadata from government websites with automatic retry, bot detection avoidance, and incremental saving.

**Key Features:** Sequential processing • Incremental saving • Automatic retry • Bot avoidance • Rate limiting • Zero false positives

---

## 📦 Setup

**Prerequisites:** Python 3.8+

**Compatible with:** Windows (Git Bash), Linux, Mac

```bash
bash setup.sh
```

This installs dependencies, Playwright browser, and creates necessary directories.

The scripts automatically detect your OS and configure accordingly.

---

## 🚀 Usage

### Problem 1: Scrape Meeting Metadata

```bash
bash run.sh
```

**Output:** `outputs/problem1_complete_output.json`

Scrapes 6 government websites (Nov 20, 2024 - Nov 26, 2025)

### Problem 2: Resolve Video/Audio/Document URLs

```bash
bash run.sh problem2
```

**Output:** `outputs/problem2_output.json`

Resolves and verifies 11 URLs from assignment:
- ✅ yt-dlp --simulate verification (videos/audio)
- ✅ HTTP HEAD verification (documents)
- ✅ Auto-retry network failures (2-3 attempts)
- ✅ Platform transformations (Swagit /download)

**Supported:** YouTube, IBM Video, Granicus, ChampDS, Viebit, SharePoint, Audiomack, PDF, HTML

### Custom Input (Problem 1)

```bash
python scraper.py scrape-meetings -i inputs/custom.json -o outputs/result.json
```

Input format:
```json
{
  "start_date": "2024-01-01",
  "end_date": "2024-12-31",
  "base_urls": ["https://your-site.gov/meetings"]
}
```

### Custom Input (Problem 2)

```bash
python scraper.py resolve-urls -i inputs/custom_urls.json -o outputs/resolved.json
```

Input format:
```json
[
  {"url": "https://example.com/video.mp4", "type": "video"},
  {"url": "https://example.com/doc.pdf", "type": "document"}
]
```

---

## 📋 Input/Output Formats

### Problem 1

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
[{
  "base_url": "https://example.gov/meetings",
  "medias": [{
    "meeting_url": "https://youtube.com/watch?v=...",
    "agenda_url": "https://example.gov/agenda.pdf",
    "minutes_url": "https://example.gov/minutes.pdf",
    "title": "City Council Meeting",
    "date": "2024-11-20"
  }]
}]
```

### Problem 2

**Input:**
```json
[
  {"url": "https://swagit.com/videos/123", "type": "audio"},
  {"url": "https://example.gov/doc.pdf", "type": "document"}
]
```

**Output:**
```json
[
  "https://swagit.com/videos/123/download",
  "https://example.gov/doc.pdf"
]
```

---

## 📁 Project Structure

```
scraping/
├── scraper.py              # CLI interface
├── setup.sh                # Installation script
├── run.sh                  # Quick run (Problem 1 & 2)
├── inputs/                 # Input JSON files
│   ├── problem1_all_domains.json
│   └── problem2_input.json
├── outputs/                # Generated outputs (incremental saves)
│   ├── problem1_complete_output.json
│   └── problem2_output.json
├── logs/                   # Application logs
└── src/
    ├── core/               # Core services
    │   ├── engine.py       # Main orchestrator
    │   ├── browser.py      # Browser management
    │   ├── stealth.py      # Anti-detection
    │   └── url_resolver.py # URL verification (Problem 2)
    ├── extractors/         # Site-specific extraction
    │   ├── base_extractor.py
    │   ├── site_handlers.py
    │   └── site_specific/  # Individual site handlers
    ├── storage/            # Data models & persistence
    │   ├── models.py
    │   ├── meeting_models.py
    │   └── writer.py
    └── utils/              # Helpers & logging
        ├── logger.py
        ├── helpers.py
        └── error_detector.py
```

---

## 🔧 Configuration

Edit `src/storage/models.py` and `src/core/url_resolver.py` for custom settings.

**Key settings:**
- Rate limit: 2 req/sec per domain
- Retries: 2-3 attempts for network errors
- Timeouts: 20-45s depending on operation

---

## 🐛 Troubleshooting

**Virtual environment not found:**
```bash
bash setup.sh
```

**Browser missing:**
```bash
playwright install chromium
```

**Python not found:**
- Windows: Install from python.org
- Linux: `sudo apt install python3 python3-pip`
- Mac: `brew install python3`

---

## 🎯 Assignment Coverage

✅ **Problem 1**: Meeting metadata scraping (6 domains)  
✅ **Problem 2**: URL resolution with retry logic (11 URLs)  
✅ **Bonus Task**: Universal scraper (40+ sites)

---

## 🏗️ Architecture

<div align="center">

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
│   • Sequential processing with callbacks                    │
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
                              │ • Classifies links       │
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
                              │   Incremental Save      │
                              │                         │
                              │ • Save after each domain│
                              │ • Progress tracking     │
                              │ • No data loss          │
                              └────────────┬────────────┘
                                           │
                                           ▼
                              ┌─────────────────────────┐
                              │   JSON Output           │
                              │   (outputs/*.json)      │
                              └─────────────────────────┘
```

</div>

---

**Note:** For ethical scraping of public government data only.
