import csv
import hashlib
import json
import os
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional, Tuple
import requests

from models import BookRecord, RawBookRecord, RunReport
from parser import clean_and_validate_record, parse_book_page, parse_catalogue_page

USER_AGENT = "FlyRankInternship-A9/1.0 (+https://github.com/venkatanaveen2078909-rgb/flyrank)"
REQUEST_TIMEOUT = 10.0
POLITE_DELAY_SECONDS = 0.5


class PoliteFetcher:
    """Handles polite, cached, and retry-resilient HTTP fetching."""

    def __init__(self, cache_dir: Path):
        self.cache_dir = cache_dir
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.session = requests.Session()
        self.session.headers.update({"User-Agent": USER_AGENT})
        self.pages_fetched = 0
        self.cache_hits = 0

    def _get_cache_path(self, url: str) -> Path:
        url_hash = hashlib.sha256(url.encode("utf-8")).hexdigest()[:16]
        # Clean slug for human inspectability
        slug = url.split("/")[-2] if url.endswith("/index.html") else url.split("/")[-1]
        slug = slug.replace(".html", "")[:24]
        return self.cache_dir / f"{slug}_{url_hash}.html"

    def fetch(self, url: str) -> Tuple[str, bool]:
        """
        Fetch HTML content. Checks local disk cache first.
        If cache miss, respects polite delay, enforces timeout, and retries once on 5xx or timeout.
        """
        cache_file = self._get_cache_path(url)

        if cache_file.exists():
            self.cache_hits += 1
            with open(cache_file, "r", encoding="utf-8") as f:
                return f.read(), True

        # Cache miss -> perform polite network fetch
        time.sleep(POLITE_DELAY_SECONDS)
        attempts = 2
        last_error = None

        for attempt in range(1, attempts + 1):
            try:
                res = self.session.get(url, timeout=REQUEST_TIMEOUT)
                # Do not retry client errors (404, 403)
                if res.status_code == 404 or res.status_code == 403:
                    raise requests.HTTPError(f"HTTP {res.status_code} - skipping without retry", response=res)

                res.raise_for_status()
                html = res.text

                # Save to disk cache
                with open(cache_file, "w", encoding="utf-8") as f:
                    f.write(html)

                self.pages_fetched += 1
                return html, False

            except (requests.Timeout, requests.ConnectionError) as e:
                last_error = e
                if attempt < attempts:
                    time.sleep(1.0)
            except requests.HTTPError as e:
                if e.response is not None and e.response.status_code >= 500 and attempt < attempts:
                    time.sleep(1.0)
                else:
                    raise e

        raise last_error or RuntimeError(f"Failed to fetch {url}")


def run_pipeline(
    start_url: str = "https://books.toscrape.com/catalogue/page-1.html",
    max_pages: int = 3,
    output_dir: Path = Path("output"),
    cache_dir: Path = Path("cache"),
    include_deliberate_failure: bool = True,
) -> RunReport:
    """
    Executes the 7-stage polite scraping pipeline:
    1. Discovers 3 catalogue pages and 60 book URLs.
    2. Fetches and parses each book page into raw records.
    3. Normalizes and validates against Pydantic schema.
    4. Handles one deliberate failure to prove error resilience.
    5. Saves output/books.json, output/books.csv, and output/run-report.json.
    """
    start_time = datetime.now(timezone.utc)
    output_dir.mkdir(parents=True, exist_ok=True)
    fetcher = PoliteFetcher(cache_dir=cache_dir)

    print("\n=======================================================")
    print("[FLAYRANK] SCRAPING PIPELINE: Books to Scrape")
    print(f"User-Agent: {USER_AGENT}")
    print(f"Delay: {POLITE_DELAY_SECONDS}s | Timeout: {REQUEST_TIMEOUT}s")
    print("=======================================================\n")

    # STAGE 1 & 2: Discover 3 catalogue pages & collect 60 book URLs
    print("--- [STAGE 1 & 2] Discovering Catalogue Pages ---")
    current_url: Optional[str] = start_url
    catalogue_pages_count = 0
    all_discovered_urls: List[str] = []

    while current_url and catalogue_pages_count < max_pages:
        html, is_cached = fetcher.fetch(current_url)
        status_label = "CACHE HIT" if is_cached else "FETCH"
        print(f"[{status_label}] Catalogue Page {catalogue_pages_count + 1}: {current_url} ({len(html)} bytes)")

        page_books, next_url = parse_catalogue_page(html, current_url)
        all_discovered_urls.extend(page_books)
        catalogue_pages_count += 1
        current_url = next_url

    # Deduplicate URLs while preserving order
    unique_book_urls = list(dict.fromkeys(all_discovered_urls))
    print(f"\nCheckpoint: catalogue_pages={catalogue_pages_count}, discovered={len(all_discovered_urls)}, unique_urls={len(unique_book_urls)}")

    # STAGE 5 PREPARATION: Deliberate failure test URL
    urls_to_scrape = list(unique_book_urls)
    if include_deliberate_failure:
        fake_broken_url = "https://books.toscrape.com/catalogue/deliberate-broken-page-404_9999/index.html"
        urls_to_scrape.append(fake_broken_url)
        print(f"Injected 1 deliberate broken URL to test failure resilience: {fake_broken_url}")

    # STAGE 3 & 4: Extract raw records, normalize, and validate with Pydantic
    print(f"\n--- [STAGE 3 & 4] Extracting & Validating {len(urls_to_scrape)} Book Pages ---")
    valid_books: List[BookRecord] = []
    invalid_records: List[Dict] = []
    failed_pages = 0

    for idx, book_url in enumerate(urls_to_scrape, 1):
        fetch_time = datetime.now(timezone.utc).isoformat()
        try:
            html, is_cached = fetcher.fetch(book_url)
            # Find catalogue provenance source
            source_page = start_url

            raw = parse_book_page(
                html=html,
                product_url=book_url,
                source_page=source_page,
                fetched_at=fetch_time,
            )

            try:
                clean_rec = clean_and_validate_record(raw)
                valid_books.append(clean_rec)
                if idx <= 3 or idx % 20 == 0:
                    status_lbl = "CACHE" if is_cached else "FETCH"
                    print(f"  [{idx}/{len(urls_to_scrape)}] [{status_lbl}] OK: '{clean_rec.title[:30]}' - GBP {clean_rec.price_gbp:.2f}")
            except Exception as val_err:
                invalid_records.append({"url": book_url, "error": str(val_err)})
                print(f"  [{idx}/{len(urls_to_scrape)}] Schema Validation Error: {book_url} ({val_err})")

        except Exception as fetch_err:
            failed_pages += 1
            invalid_records.append({"url": book_url, "error": str(fetch_err)})
            print(f"  [{idx}/{len(urls_to_scrape)}] [SKIP] Broken page survived: {book_url} ({fetch_err})")

    # Deduplicate valid records by canonical product_url (idempotency guarantee)
    seen_urls = set()
    deduped_books: List[BookRecord] = []
    for book in valid_books:
        url_str = str(book.product_url)
        if url_str not in seen_urls:
            seen_urls.add(url_str)
            deduped_books.append(book)

    # WRITE OUTPUTS
    # 1. output/books.json
    books_json_path = output_dir / "books.json"
    with open(books_json_path, "w", encoding="utf-8") as f:
        json.dump([b.model_dump(mode="json") for b in deduped_books], f, indent=2, ensure_ascii=False)

    # 2. output/errors.json
    errors_json_path = output_dir / "errors.json"
    with open(errors_json_path, "w", encoding="utf-8") as f:
        json.dump(invalid_records, f, indent=2)

    # 3. output/books.csv (Extra feature)
    books_csv_path = output_dir / "books.csv"
    with open(books_csv_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["title", "product_url", "price_gbp", "price_text", "availability_text", "rating_text", "source_page", "fetched_at"])
        for b in deduped_books:
            writer.writerow([b.title, str(b.product_url), b.price_gbp, b.price_text, b.availability_text, b.rating_text, str(b.source_page), b.fetched_at])

    end_time = datetime.now(timezone.utc)
    duration = round((end_time - start_time).total_seconds(), 2)

    report = RunReport(
        start_time=start_time.isoformat(),
        duration_seconds=duration,
        catalogue_pages=catalogue_pages_count,
        discovered_urls=len(all_discovered_urls),
        unique_urls=len(unique_book_urls),
        pages_fetched=fetcher.pages_fetched,
        cache_hits=fetcher.cache_hits,
        valid_records=len(deduped_books),
        invalid_records=len(invalid_records) - failed_pages,
        failed_pages=failed_pages,
    )

    # 4. output/run-report.json
    report_path = output_dir / "run-report.json"
    with open(report_path, "w", encoding="utf-8") as f:
        json.dump(report.model_dump(mode="json"), f, indent=2)

    print("\n=======================================================")
    print("[REPORT] RUN SUMMARY")
    print(f"Duration: {duration}s")
    print(f"Pages Fetched over Network: {fetcher.pages_fetched} | Cache Hits: {fetcher.cache_hits}")
    print(f"Valid Stored Records: {len(deduped_books)} (written to {books_json_path})")
    print(f"Failed Pages Survived: {failed_pages}")
    print("=======================================================\n")

    return report
