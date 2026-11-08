from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field, HttpUrl, field_validator


class RawBookRecord(BaseModel):
    """Raw record extracted directly from the HTML before normalization."""
    title: str
    product_url: str
    price_text: str
    availability_text: str
    rating_text: str
    description: Optional[str] = None
    source_page: str
    fetched_at: str


class BookRecord(BaseModel):
    """Clean, schema-validated book record ready for production storage."""
    title: str = Field(..., min_length=1, description="Book title")
    product_url: HttpUrl = Field(..., description="Canonical absolute product URL")
    price_text: str = Field(..., description="Original raw price text (e.g. £51.77)")
    price_gbp: float = Field(..., ge=0.0, description="Normalized numeric price in GBP")
    availability_text: str = Field(..., description="Raw stock availability string")
    rating_text: str = Field(..., description="Word rating e.g. One, Two, Three, Four, Five")
    description: Optional[str] = Field(default=None, description="Book synopsis (null if missing)")
    source_page: HttpUrl = Field(..., description="Provenance: catalogue page URL where link was found")
    fetched_at: str = Field(..., description="ISO 8601 UTC timestamp of fetch")

    @field_validator("title")
    @classmethod
    def validate_title(cls, v: str) -> str:
        cleaned = v.strip()
        if not cleaned:
            raise ValueError("Title cannot be empty")
        return cleaned


class RunReport(BaseModel):
    """Execution telemetry report proving respectful and resilient scraping."""
    start_time: str
    duration_seconds: float
    catalogue_pages: int
    discovered_urls: int
    unique_urls: int
    pages_fetched: int
    cache_hits: int
    valid_records: int
    invalid_records: int
    failed_pages: int
