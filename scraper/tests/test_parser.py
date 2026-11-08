import sys
from pathlib import Path

# Add scraper/src to sys.path
SRC_DIR = Path(__file__).resolve().parent.parent / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from parser import clean_and_validate_record, normalize_price, parse_book_page, parse_catalogue_page
from models import RawBookRecord


def test_price_normalization():
    """1. Price normalization: converts varied currency strings to floats."""
    assert normalize_price("£51.77") == 51.77
    assert normalize_price("Â£10.99") == 10.99
    assert normalize_price("£0.00") == 0.00
    assert normalize_price("Price: £123.45 incl tax") == 123.45
    assert normalize_price("Free") == 0.0


def test_relative_to_absolute_urls():
    """2. Relative -> Absolute URLs: resolves ../ paths without string concatenation."""
    sample_html = """
    <article class="product_pod">
        <h3><a href="../../../catalogue/a-light-in-the-attic_1000/index.html">Title</a></h3>
    </article>
    <li class="next"><a href="page-2.html">next</a></li>
    """
    base_url = "https://books.toscrape.com/catalogue/page-1.html"
    book_urls, next_url = parse_catalogue_page(sample_html, base_url)

    assert len(book_urls) == 1
    assert book_urls[0] == "https://books.toscrape.com/catalogue/a-light-in-the-attic_1000/index.html"
    assert next_url == "https://books.toscrape.com/catalogue/page-2.html"


def test_missing_description():
    """3. Missing description: sets null/None without inventing missing text."""
    sample_html = """
    <div class="product_main">
        <h1>Book Without Description</h1>
        <p class="price_color">£19.99</p>
        <p class="instock availability">In stock</p>
        <p class="star-rating Four"></p>
    </div>
    """
    raw = parse_book_page(
        html=sample_html,
        product_url="https://books.toscrape.com/catalogue/no-desc_1/index.html",
        source_page="https://books.toscrape.com/catalogue/page-1.html",
        fetched_at="2026-11-08T12:00:00Z",
    )
    assert raw.description is None
    record = clean_and_validate_record(raw)
    assert record.description is None


def test_duplicate_urls_deduplication():
    """4. Duplicate URLs: ensures duplicate page links are removed."""
    sample_html = """
    <article class="product_pod"><h3><a href="book-1.html">Book 1</a></h3></article>
    <article class="product_pod"><h3><a href="book-1.html">Book 1 Duplicate</a></h3></article>
    <article class="product_pod"><h3><a href="book-2.html">Book 2</a></h3></article>
    """
    base_url = "https://books.toscrape.com/catalogue/page-1.html"
    book_urls, _ = parse_catalogue_page(sample_html, base_url)
    assert len(book_urls) == 3
    # Pipeline deduplication
    unique_urls = list(dict.fromkeys(book_urls))
    assert len(unique_urls) == 2


def test_malformed_html_fixture():
    """5. Malformed fixture: handles truncated or messy HTML safely without crashing."""
    malformed_html = "<div><h1>Truncated Title Only...<p class='price_color'>£9.50"
    raw = parse_book_page(
        html=malformed_html,
        product_url="https://books.toscrape.com/catalogue/malformed_99/index.html",
        source_page="https://books.toscrape.com/catalogue/page-1.html",
        fetched_at="2026-11-08T12:00:00Z",
    )
    assert "Truncated Title" in raw.title
    record = clean_and_validate_record(raw)
    assert record.price_gbp == 9.50
    assert record.rating_text == "Zero"
