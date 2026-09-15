import os
import httpx

GEMINI_BASE_URL = os.getenv("GEMINI_BASE_URL", "https://generativelanguage.googleapis.com/v1beta")
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-3.6-flash")
GEMINI_FALLBACK_MODEL = os.getenv("GEMINI_FALLBACK_MODEL", "gemini-2.5-flash-lite")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "").strip()

OPENROUTER_MODEL = os.getenv("OPENROUTER_MODEL", "openrouter/free")
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY", "").strip()

CEREBRAS_MODEL = os.getenv("CEREBRAS_MODEL", "gpt-oss-120b")
CEREBRAS_API_KEY = os.getenv("CEREBRAS_API_KEY", "").strip()

SYSTEM = """You are Aria Freelancer, a professional AI content specialist.
Create useful, accurate, natural Persian or English marketing content.
Never invent facts, prices, credentials, testimonials, citations, or sources.
Never make medical diagnosis claims or treatment promises.
For health-related businesses, keep content educational and safe.
Follow the client's requested tone and audience.
Return only the requested deliverable.
"""

def call_gemini(prompt):
    if not GEMINI_API_KEY:
        raise RuntimeError("GEMINI_API_KEY is missing")
    errors = []
    for model in (GEMINI_MODEL, GEMINI_FALLBACK_MODEL):
        if not model:
            continue
        try:
            print(f"Trying Gemini: {model}")
            payload = {
                "system_instruction": {"parts": [{"text": SYSTEM}]},
                "contents": [{"role": "user", "parts": [{"text": prompt}]}],
                "generationConfig": {"temperature": 0.7, "maxOutputTokens": 4000},
            }
            with httpx.Client(timeout=60) as client:
                r = client.post(
                    f"{GEMINI_BASE_URL}/models/{model}:generateContent",
                    headers={"Content-Type": "application/json", "x-goog-api-key": GEMINI_API_KEY},
                    json=payload,
                )
            if r.status_code >= 400:
                raise RuntimeError(f"HTTP {r.status_code}: {r.text[:800]}")
            result = r.json()["candidates"][0]["content"]["parts"][0]["text"].strip()
            if not result:
                raise RuntimeError("Empty Gemini response")
            print(f"Gemini succeeded: {model}")
            return result
        except Exception as exc:
            print(f"Gemini failed: {model}: {exc}")
            errors.append(f"{model}: {exc}")
    raise RuntimeError("Gemini failed: " + " | ".join(errors))

def call_openrouter(prompt):
    if not OPENROUTER_API_KEY:
        raise RuntimeError("OPENROUTER_API_KEY is missing")
    print(f"Trying OpenRouter: {OPENROUTER_MODEL}")
    payload = {
        "model": OPENROUTER_MODEL,
        "messages": [{"role": "system", "content": SYSTEM}, {"role": "user", "content": prompt}],
        "temperature": 0.7,
        "max_tokens": 4000,
    }
    with httpx.Client(timeout=60) as client:
        r = client.post(
            "https://openrouter.ai/api/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {OPENROUTER_API_KEY}",
                "Content-Type": "application/json",
                "HTTP-Referer": "https://github.com/mohilati/Aria-freelancer",
                "X-Title": "Aria Freelancer",
            },
            json=payload,
        )
    if r.status_code >= 400:
        raise RuntimeError(f"HTTP {r.status_code}: {r.text[:800]}")
    result = r.json()["choices"][0]["message"]["content"].strip()
    if not result:
        raise RuntimeError("Empty OpenRouter response")
    print("OpenRouter succeeded")
    return result

def call_cerebras(prompt):
    if not CEREBRAS_API_KEY:
        raise RuntimeError("CEREBRAS_API_KEY is missing")
    print(f"Trying Cerebras: {CEREBRAS_MODEL}")
    payload = {
        "model": CEREBRAS_MODEL,
        "messages": [{"role": "system", "content": SYSTEM}, {"role": "user", "content": prompt}],
        "temperature": 0.7,
        "max_tokens": 4000,
    }
    with httpx.Client(timeout=60) as client:
        r = client.post(
            "https://api.cerebras.ai/v1/chat/completions",
            headers={"Authorization": f"Bearer {CEREBRAS_API_KEY}", "Content-Type": "application/json"},
            json=payload,
        )
    if r.status_code >= 400:
        raise RuntimeError(f"HTTP {r.status_code}: {r.text[:800]}")
    result = r.json()["choices"][0]["message"]["content"].strip()
    if not result:
        raise RuntimeError("Empty Cerebras response")
    print("Cerebras succeeded")
    return result

def generate(prompt):
    errors = []
    for name, fn in (("Gemini", call_gemini), ("OpenRouter", call_openrouter), ("Cerebras", call_cerebras)):
        try:
            return fn(prompt)
        except Exception as exc:
            print(f"{name} unavailable: {exc}")
            errors.append(f"{name}: {exc}")
    raise RuntimeError("All AI providers failed. " + " | ".join(errors))
