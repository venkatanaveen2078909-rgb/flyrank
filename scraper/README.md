# FlyRank Backend Track — Assignment A9: The Polite Scraper

A robust, respectful, and resilient web scraping pipeline in Python that extracts book catalogue data from **Books to Scrape**, normalizes messy HTML into clean schema-validated JSON records, survives broken pages without crashing, and generates an honest telemetry run report.

---

## 📋 Table of Contents
- [Target Classification & Ethics](#target-classification--ethics)
- [Politeness Rules](#politeness-rules)
- [Installation & Quickstart](#installation--quickstart)
- [Data Schema & Validation](#data-schema--validation)
- [Run Report & Proof of Execution](#run-report--proof-of-execution)
- [Why No Browser Was Needed](#why-no-browser-was-needed)
- [Testing & Failure Resilience](#testing--failure-resilience)
- [Honest Limitations](#honest-limitations)
- [Bonus: AI vs Me Reflection](#bonus-ai-vs-me-reflection)

---

## 🎯 Target Classification & Ethics

### 1. Target Website
- **URL:** [https://books.toscrape.com/](https://books.toscrape.com/)
- **Nature of Site:** A public playground sandbox deliberately designed and hosted for developers and students to practice web scraping.
- **`robots.txt` Result:** Requesting `https://books.toscrape.com/robots.txt` returns `HTTP 404 Not Found` (*"no robots file found"*). A missing file is not an open invitation; permission is derived from the explicit purpose of the sandbox.
- **Scope:** Exactly the first **3 catalogue pages** (20 books per page = 60 books total).
- **Data Collected:** Product titles, canonical URLs, prices, stock availability, ratings, and synopses.
- **Why Appropriate:** Scrapes a limited subset of mock commercial data from a dedicated testbed without touching sensitive user accounts, behind-login resources, or production commercial servers.

> **Mandatory Ethical Pledge:**  
> *"I will not reuse this code on another site without checking its rules and terms first."*

### 2. General Scraping Ethics Note
- **API First:** Always use an official REST/GraphQL API when one exists. Scraping is a fallback when no structured interface is available.
- **Respect Boundaries:** Never bypass logins, CAPTCHAs, paywalls, or blocking mechanisms.
- **Collect Minimal Data:** Fetch only the pages and fields strictly required for your application.
- **Respect Server Load:** Rate-limit requests and cache aggressively so your scraper never degrades service for human visitors.

---

## 🤝 Politeness Rules

This pipeline implements four core politeness safeguards:

1. **Honest User-Agent:**
   Introduces itself on every HTTP request with contact provenance:
   ```text
   FlyRankInternship-A9/1.0 (+https://github.com/venkatanaveen2078909-rgb/flyrank)
   ```
2. **Politeness Delay:**
   Waits **500 ms** (`time.sleep(0.5)`) between consecutive live network requests. Cached pages require 0ms delay because they never touch the external server.
3. **Strict Timeout:**
   Enforces a **10-second timeout** on every network request to prevent deadlocks from hanging connections.
4. **Local Disk Cache:**
   Saves fetched HTML pages to `scraper/cache/`. Development reruns read from cache (`CACHE HIT`), so the remote site is fetched only once. `cache/` is strictly git-ignored.

---

## ⚙️ Installation & Quickstart

### Prerequisites
- Python 3.10+
- Virtual environment (`.venv`)

### 1. Install Dependencies
```bash
pip install -r requirements.txt
```

### 2. Run the Pipeline (One Command)
```bash
python src/main.py
```

Outputs are automatically generated in `output/`:
- `output/books.json`: 60 validated records.
- `output/run-report.json`: Execution metrics.
- `output/books.csv`: Tabular export.
- `output/errors.json`: Any schema-invalid records or skipped failures.

---

## 📦 Data Schema & Validation

Records are validated using **Pydantic** (`BookRecord`):

```json
{
  "title": "A Light in the Attic",
  "product_url": "https://books.toscrape.com/catalogue/a-light-in-the-attic_1000/index.html",
  "price_text": "£51.77",
  "price_gbp": 51.77,
  "availability_text": "In stock (22 available)",
  "rating_text": "Three",
  "description": "It's hard to imagine a world without A Light in the Attic...",
  "source_page": "https://books.toscrape.com/catalogue/page-1.html",
  "fetched_at": "2026-11-08T06:43:20.081071+00:00"
}
```

- **Price Normalization:** Raw currency strings (`£51.77`) are parsed into numeric floats (`51.77`) for comparison and sorting, while preserving the raw text for auditing.
- **Canonical Identity:** The absolute `product_url` serves as the primary key. Duplicate URLs are deduplicated, ensuring **idempotency** (rerunning produces the exact same 60 records, never 120).
- **Provenance Tracking:** `source_page` and `fetched_at` are attached to every record to audit where and when each data point originated.

---

## 📊 Run Report & Proof of Execution

The following telemetry was captured directly from a real execution of the pipeline:

```json
{
  "start_time": "2026-11-08T06:43:20.081071+00:00",
  "duration_seconds": 1.99,
  "catalogue_pages": 3,
  "discovered_urls": 60,
  "unique_urls": 60,
  "pages_fetched": 0,
  "cache_hits": 63,
  "valid_records": 60,
  "invalid_records": 0,
  "failed_pages": 1
}
```

- **`cache_hits: 63`**: Demonstrates the caching system in action during development.
- **`valid_records: 60`**: All 60 books across the 3 catalogue pages were parsed and validated.
- **`failed_pages: 1`**: Demonstrates that the deliberate broken test URL was caught and isolated without crashing the pipeline.

---

## 💡 Why No Browser Was Needed

The book catalogue data is entirely server-rendered into static HTML by the web server; the titles, prices, ratings, and synopses are directly present in the initial HTTP response body. Using a headless browser (such as Playwright, Puppeteer, or Selenium) would launch a multi-hundred-megabyte Chromium process consuming immense RAM and CPU cycles for zero additional data, adding cost and latency without purpose.

---

## 🧪 Testing & Failure Resilience

### 1. Parser Unit Tests
Run the test suite with **Pytest**:
```bash
pytest tests/test_parser.py -v
```

Five dedicated unit tests verify:
1. `test_price_normalization`: Converts messy currency strings (`£51.77`, `Â£10.99`) into numeric floats.
2. `test_relative_to_absolute_urls`: Correctly joins relative `../` links using `urllib.parse.urljoin`.
3. `test_missing_description`: Stores `null`/`None` instead of inventing dummy text.
4. `test_duplicate_urls_deduplication`: Deduplicates repeated URLs to ensure idempotent output.
5. `test_malformed_html_fixture`: Handles truncated/broken HTML without throwing unhandled exceptions.

### 2. Surviving Broken Pages
The pipeline wraps individual book fetches in a `try...except` block. A deliberate broken link (`.../deliberate-broken-page-404_9999/index.html`) is processed during the run:
- The error is logged and appended to `output/errors.json`.
- The remaining 60 books survive unharmed.
- `run-report.json` records `failed_pages: 1`.

---

## ⚠️ Honest Limitations

This scraper relies on CSS selectors targeting specific class names (`div.product_main h1`, `p.price_color`, `#product_description ~ p`). If Books to Scrape modifies its HTML structure or migrates to a client-rendered Single Page Application (SPA) requiring JavaScript execution, these selectors will fail and must be updated.

---

## 🤖 Bonus: AI vs Me Reflection (Stage 7)

### Prompt Used:
> "Write a polite Python web scraper using requests and BeautifulSoup for Books to Scrape. Collect the first 3 catalogue pages (60 books), extract title, price, stock, rating, and description, save to JSON, cache pages to disk, enforce a 0.5s delay, and make sure it does not crash if a page fails."

### Three Concrete Differences:
1. **Missing URL Normalization:** The AI naively used string formatting (`f"{base_url}{href}"`) to resolve links. Because catalogue links on Books to Scrape use relative paths (`../../../`), this produced broken URLs. Our hand-built code uses `urllib.parse.urljoin(base_url, href)`.
2. **Missing Caching & Politeness in Detail Loop:** While the AI added a delay to the catalogue loop, it completely omitted rate limiting and disk caching when visiting individual book pages, resulting in dozens of unthrottled requests that would hammer the target server.
3. **No Schema Validation or Telemetry:** The AI dumped raw extracted strings directly into a dictionary without numeric price casting, provenance timestamps, or a run report. Our implementation enforces a strict Pydantic model (`BookRecord`) and logs telemetry in `run-report.json`.
