import re
from typing import List, Optional, Tuple
from urllib.parse import urljoin
from bs4 import BeautifulSoup
from models import BookRecord, RawBookRecord


def parse_catalogue_page(html: str, base_url: str) -> Tuple[List[str], Optional[str]]:
    """
    Parse a catalogue page:
    1. Extracts all 20 book relative URLs and converts them to absolute URLs using urljoin.
    2. Discovers the 'next' catalogue page URL if present.
    """
    soup = BeautifulSoup(html, "html.parser")
    book_urls: List[str] = []

    for article in soup.select("article.product_pod"):
        a_tag = article.select_one("h3 > a")
        if a_tag and a_tag.get("href"):
            raw_href = a_tag["href"].strip()
            absolute_url = urljoin(base_url, raw_href)
            book_urls.append(absolute_url)

    next_btn = soup.select_one("li.next > a")
    next_page_url = None
    if next_btn and next_btn.get("href"):
        next_page_url = urljoin(base_url, next_btn["href"].strip())

    return book_urls, next_page_url


def parse_book_page(
    html: str, product_url: str, source_page: str, fetched_at: str
) -> RawBookRecord:
    """
    Extract the 8 required raw fields from a book detail page.
    Selectors target the product area specifically to avoid picking up unrelated layout text.
    """
    soup = BeautifulSoup(html, "html.parser")

    # Title: inside product_main <h1> or h1 tag
    title_elem = soup.select_one("div.product_main h1") or soup.select_one("h1")
    title = title_elem.get_text(strip=True) if title_elem else "Unknown Title"

    # Price text: <p class="price_color">
    price_elem = soup.select_one("p.price_color")
    price_text = price_elem.get_text(strip=True) if price_elem else "£0.00"

    # Availability text: <p class="instock availability">
    avail_elem = soup.select_one("p.instock.availability")
    if avail_elem:
        availability_text = " ".join(avail_elem.get_text().split())
    else:
        availability_text = "Unknown availability"

    # Star rating: <p class="star-rating Three">
    rating_elem = soup.select_one("p.star-rating")
    rating_text = "Zero"
    if rating_elem:
        classes = rating_elem.get("class", [])
        for c in classes:
            if c != "star-rating":
                rating_text = c
                break

    # Description: under #product_description + p
    desc_elem = soup.select_one("#product_description ~ p")
    description = desc_elem.get_text(strip=True) if desc_elem else None
    if description == "":
        description = None

    return RawBookRecord(
        title=title,
        product_url=product_url,
        price_text=price_text,
        availability_text=availability_text,
        rating_text=rating_text,
        description=description,
        source_page=source_page,
        fetched_at=fetched_at,
    )


def normalize_price(price_text: str) -> float:
    """
    Convert raw currency string like '£51.77' or 'Â£51.77' into a clean float 51.77.
    """
    match = re.search(r"(\d+\.\d{2})", price_text)
    if match:
        return float(match.group(1))
    # Fallback to general float extraction
    numbers = re.findall(r"\d+", price_text)
    if numbers:
        return float(".".join(numbers[:2]))
    return 0.0


def clean_and_validate_record(raw: RawBookRecord) -> BookRecord:
    """Normalize raw fields and validate against the strict Pydantic BookRecord schema."""
    numeric_price = normalize_price(raw.price_text)
    return BookRecord(
        title=raw.title,
        product_url=raw.product_url,
        price_text=raw.price_text,
        price_gbp=numeric_price,
        availability_text=raw.availability_text,
        rating_text=raw.rating_text,
        description=raw.description,
        source_page=raw.source_page,
        fetched_at=raw.fetched_at,
    )
