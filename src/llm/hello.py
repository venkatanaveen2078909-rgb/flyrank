import os
from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()

base_url = os.getenv("LLM_BASE_URL", "https://openrouter.ai/api/v1")
api_key = os.getenv("LLM_API_KEY", "stub-key")
model = os.getenv("LLM_MODEL", "openrouter/free")
is_stub = os.getenv("LLM_STUB", "1") == "1"

if is_stub or api_key == "stub-key" or not api_key:
    print("ready (stub mode verified)")
else:
    try:
        client = OpenAI(base_url=base_url, api_key=api_key, timeout=10.0)
        res = client.chat.completions.create(
            model=model,
            messages=[{"role": "user", "content": "Reply with exactly the word: ready"}],
        )
        print(res.choices[0].message.content.strip())
    except Exception as e:
        print(f"Provider connection error: {e}")
