from enum import Enum
from pydantic import BaseModel, Field, field_validator


class Category(str, Enum):
    BILLING = "billing"
    BUG = "bug"
    FEATURE = "feature"
    OTHER = "other"


class Urgency(str, Enum):
    LOW = "low"
    NORMAL = "normal"
    HIGH = "high"


class TriageInput(BaseModel):
    """Input payload for support ticket triage."""
    text: str = Field(..., description="Support ticket message text (1-2000 characters)")

    @field_validator("text")
    @classmethod
    def validate_text(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("Support message text cannot be empty or whitespace-only")
        cleaned = v.strip()
        if len(cleaned) > 2000:
            raise ValueError("Support message text exceeds maximum limit of 2000 characters")
        return cleaned


class TriageOutput(BaseModel):
    """Strict, closed JSON schema for triage classification."""
    category: Category = Field(..., description="Classification category")
    urgency: Urgency = Field(..., description="Priority level")
    confidence: float = Field(..., ge=0.0, le=1.0, description="Confidence score between 0.0 and 1.0")
    reason: str = Field(..., max_length=300, description="One concise sentence explaining the triage decision")
