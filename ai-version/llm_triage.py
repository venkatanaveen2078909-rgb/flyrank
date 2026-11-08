# AI-Generated Version (Quarantine folder for Assignment A17: Bonus AI Rematch)
# Notice Flaw 1: 10-minute default SDK timeout left in place (no explicit timeout=30.0)
# Notice Flaw 2: Returns raw model string if parsing fails, breaking the API schema contract!
# Notice Flaw 3: Blind retry loop retries on 401 / bad API keys!
# Notice Flaw 4: No operational kill switch (LLM_ENABLED)

import json
from openai import OpenAI

client = OpenAI()

def triage(text: str):
    # Missing explicit timeout parameter
    # Retries on 401 authentication errors naively
    for attempt in range(3):
        try:
            res = client.chat.completions.create(
                model="openrouter/free",
                messages=[
                    {"role": "system", "content": "Classify support messages into billing, bug, feature, other."},
                    {"role": "user", "content": text}
                ]
            )
            raw = res.choices[0].message.content
            try:
                return json.loads(raw)
            except Exception:
                # Flaw: returns raw text instead of repairing or returning 422!
                return {"raw_text": raw}
        except Exception as e:
            if attempt == 2:
                raise e
