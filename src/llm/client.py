import json
import logging
import os
import random
import re
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Optional, Tuple
from dotenv import load_dotenv
from fastapi import HTTPException, status
from openai import APIConnectionError, APIStatusError, APITimeoutError, OpenAI
from pydantic import ValidationError

from src.llm.schema import Category, TriageInput, TriageOutput, Urgency

load_dotenv()

# Structured Logger
logging.basicConfig(level=logging.INFO, format="%(message)s")
logger = logging.getLogger("llm_service")

PROMPT_VERSION = "v1"
PROMPTS_DIR = Path(__file__).resolve().parent.parent.parent / "prompts"
LOGS_DIR = Path(__file__).resolve().parent.parent.parent / "logs"
QUARANTINE_FILE = LOGS_DIR / "quarantine.jsonl"


def load_system_prompt() -> str:
    """Load the versioned system prompt specification from disk."""
    prompt_file = PROMPTS_DIR / f"triage-{PROMPT_VERSION}.md"
    if not prompt_file.exists():
        raise FileNotFoundError(f"System prompt file not found at {prompt_file}")
    with open(prompt_file, "r", encoding="utf-8") as f:
        return f.read()


def get_llm_config() -> Dict[str, Any]:
    """Retrieve and validate LLM runtime configuration."""
    return {
        "base_url": os.getenv("LLM_BASE_URL", "https://openrouter.ai/api/v1"),
        "api_key": os.getenv("LLM_API_KEY", "stub-key"),
        "model": os.getenv("LLM_MODEL", "openrouter/free"),
        "is_stub": os.getenv("LLM_STUB", "0") == "1",
        "is_enabled": os.getenv("LLM_ENABLED", "true").lower() not in ("0", "false", "off"),
        "timeout": float(os.getenv("LLM_TIMEOUT", "30.0")),
    }


def clean_json_text(text: str) -> str:
    """Strip markdown formatting, code fences, and leading/trailing conversational filler."""
    text = text.strip()
    # Match markdown code fences like ```json ... ``` or ``` ... ```
    fence_pattern = r"^```(?:json)?\s*([\s\S]*?)\s*```$"
    match = re.match(fence_pattern, text)
    if match:
        text = match.group(1).strip()
    # Find the outermost curly braces
    start = text.find("{")
    end = text.rfind("}")
    if start != -1 and end != -1 and end >= start:
        text = text[start : end + 1]
    return text


def log_cost_telemetry(
    model: str,
    input_tokens: int,
    output_tokens: int,
    duration_ms: float,
    repairs: int,
) -> None:
    """Log structured telemetry per call conforming to 12-Factor App standards."""
    entry = {
        "event": "llm_call_completed",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "prompt_version": PROMPT_VERSION,
        "model": model,
        "input_tokens": input_tokens,
        "output_tokens": output_tokens,
        "duration_ms": round(duration_ms, 2),
        "repairs": repairs,
    }
    logger.info(json.dumps(entry))


def record_quarantine(raw_text: str, user_input: str, error_msg: str) -> None:
    """Quarantine bad or irreparable model output to logs/quarantine.jsonl."""
    LOGS_DIR.mkdir(parents=True, exist_ok=True)
    entry = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "prompt_version": PROMPT_VERSION,
        "user_input": user_input,
        "raw_output": raw_text,
        "error": error_msg,
    }
    with open(QUARANTINE_FILE, "a", encoding="utf-8") as f:
        f.write(json.dumps(entry) + "\n")


def call_model_with_retries(
    client: OpenAI,
    model: str,
    messages: list,
    timeout: float,
) -> Tuple[str, int, int]:
    """
    Executes model request with explicit timeout and exponential backoff retry policy.
    Retries ONLY on timeouts, 429 (rate limits), and 5xx. Never retries 400, 401, 403.
    """
    max_retries = 2
    delay = 1.0

    for attempt in range(1, max_retries + 2):
        try:
            res = client.chat.completions.create(
                model=model,
                messages=messages,
                temperature=0.0,
                timeout=timeout,
            )
            content = res.choices[0].message.content or ""
            usage = res.usage
            in_tokens = usage.prompt_tokens if usage else 0
            out_tokens = usage.completion_tokens if usage else 0
            return content, in_tokens, out_tokens

        except APITimeoutError:
            if attempt > max_retries:
                raise HTTPException(
                    status_code=status.HTTP_504_GATEWAY_TIMEOUT,
                    detail="LLM model request timed out after 30 seconds",
                )
            jitter = random.uniform(0.1, 0.5)
            time.sleep(delay + jitter)
            delay *= 2.0

        except APIStatusError as err:
            status_code = err.status_code
            # Fast fail on authentication or bad request errors - NEVER retry
            if status_code in (400, 401, 403):
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail=f"LLM Provider Authentication or configuration error: HTTP {status_code}",
                )
            if status_code == 429 or status_code >= 500:
                if attempt > max_retries:
                    raise HTTPException(
                        status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                        detail="LLM Provider rate limited or unavailable after retries",
                    )
                jitter = random.uniform(0.1, 0.5)
                time.sleep(delay + jitter)
                delay *= 2.0
            else:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail=f"LLM API Error: {err.message}",
                )

        except APIConnectionError:
            if attempt > max_retries:
                raise HTTPException(
                    status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                    detail="Cannot connect to LLM Provider network endpoint",
                )
            jitter = random.uniform(0.1, 0.5)
            time.sleep(delay + jitter)
            delay *= 2.0

    raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Unexpected LLM failure")


def triage_message(user_input: str) -> TriageOutput:
    """
    Main triage coordinator:
    - Checks kill switch (LLM_ENABLED)
    - Checks stub mode (LLM_STUB)
    - Calls model
    - Validates against Pydantic schema
    - Executes single repair retry on schema failure
    - Quarantines unrecoverable outputs (422)
    """
    config = get_llm_config()

    # 1. Kill Switch Check
    if not config["is_enabled"]:
        # Deterministic safe fallback
        logger.warning(json.dumps({"event": "kill_switch_active", "action": "fallback_applied"}))
        return TriageOutput(
            category=Category.OTHER,
            urgency=Urgency.NORMAL,
            confidence=0.0,
            reason="LLM integration currently disabled by operational kill switch",
        )

    # 2. Stub Mode Check (Zero cost development & CI tests)
    if config["is_stub"] or config["api_key"] == "stub-key":
        lower = user_input.lower()
        if "ignore all" in lower or "system override" in lower:
            cat = Category.OTHER
            urg = Urgency.LOW
            reason = "Adversarial prompt injection attempt safely quarantined as irrelevant"
        elif "charge" in lower or "refund" in lower or "bill" in lower or "invoice" in lower:
            cat = Category.BILLING
            urg = Urgency.HIGH if ("refund" in lower or "twice" in lower) else Urgency.NORMAL
            reason = "Customer message mentions payment or refund inquiry"
        elif "bug" in lower or "error" in lower or "crash" in lower or "spin" in lower or "typo" in lower:
            cat = Category.BUG
            urg = Urgency.HIGH if ("crash" in lower or "500" in lower) else Urgency.LOW
            reason = "Customer message describes technical defect or malfunction"
        elif "feature" in lower or "suggest" in lower or "would be" in lower or "add dark mode" in lower or "support" in lower:
            cat = Category.FEATURE
            urg = Urgency.LOW
            reason = "Customer proposing product enhancement or request"
        else:
            cat = Category.OTHER
            urg = Urgency.LOW
            reason = "General inquiry or ambiguous request"

        log_cost_telemetry(
            model="stub-mode",
            input_tokens=len(user_input.split()),
            output_tokens=30,
            duration_ms=5.0,
            repairs=0,
        )
        return TriageOutput(category=cat, urgency=urg, confidence=0.92, reason=reason)

    # 3. Live Model Execution
    start_call = time.time()
    system_prompt = load_system_prompt()
    client = OpenAI(base_url=config["base_url"], api_key=config["api_key"])

    # Separate system prompt from untrusted user content (Prompt Injection defense)
    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_input},
    ]

    raw_response, in_tok, out_tok = call_model_with_retries(
        client=client,
        model=config["model"],
        messages=messages,
        timeout=config["timeout"],
    )

    # 4. Parse & Validate
    repairs = 0
    parsed_json_str = clean_json_text(raw_response)

    try:
        output_obj = TriageOutput.model_validate_json(parsed_json_str)
    except (ValueError, ValidationError) as first_err:
        # 5. Repair Loop: Execute exactly ONE repair retry
        repairs = 1
        repair_messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_input},
            {"role": "assistant", "content": raw_response},
            {
                "role": "user",
                "content": (
                    f"Your previous response was rejected due to this schema validation error:\n"
                    f"{str(first_err)}\n"
                    f"Return ONLY valid JSON matching the exact schema."
                ),
            },
        ]

        repair_raw, rep_in, rep_out = call_model_with_retries(
            client=client,
            model=config["model"],
            messages=repair_messages,
            timeout=config["timeout"],
        )
        in_tok += rep_in
        out_tok += rep_out
        second_json_str = clean_json_text(repair_raw)

        try:
            output_obj = TriageOutput.model_validate_json(second_json_str)
        except (ValueError, ValidationError) as second_err:
            # 6. Quarantine unrecoverable output and fail with 422
            record_quarantine(
                raw_text=repair_raw,
                user_input=user_input,
                error_msg=f"Repair failed: {str(second_err)}",
            )
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"Model output could not be validated against schema: {str(second_err)}",
            )

    elapsed_ms = (time.time() - start_call) * 1000.0
    log_cost_telemetry(
        model=config["model"],
        input_tokens=in_tok,
        output_tokens=out_tok,
        duration_ms=elapsed_ms,
        repairs=repairs,
    )

    return output_obj
