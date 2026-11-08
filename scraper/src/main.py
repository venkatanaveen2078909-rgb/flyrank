import sys
from pathlib import Path

# Support UTF-8 output on all operating systems
if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

# Ensure src directory is in sys.path
CURRENT_DIR = Path(__file__).resolve().parent
if str(CURRENT_DIR) not in sys.path:
    sys.path.insert(0, str(CURRENT_DIR))

from pipeline import run_pipeline


def main():
    """Main CLI entry point for the polite scraping pipeline."""
    # Compute output and cache directories relative to scraper folder
    base_dir = CURRENT_DIR.parent
    output_dir = base_dir / "output"
    cache_dir = base_dir / "cache"

    print("Initiating FlyRank Polite Scraper pipeline...")
    report = run_pipeline(
        start_url="https://books.toscrape.com/catalogue/page-1.html",
        max_pages=3,
        output_dir=output_dir,
        cache_dir=cache_dir,
        include_deliberate_failure=True,
    )

    print("Pipeline finished successfully.")
    print(f"Results saved to: {output_dir / 'books.json'}")
    print(f"Report saved to:  {output_dir / 'run-report.json'}")
    print(f"Total valid books stored: {report.valid_records}")
    print(f"Total failed pages survived: {report.failed_pages}")


if __name__ == "__main__":
    main()
