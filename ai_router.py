"""
Quota-aware text AI router for Aria Freelancer.

Gemini is attempted first, but a 429/quota response puts that model into a
process-local cooldown so every scene does not hammer the same exhausted model.
"""

from __future__ import annotations

import os
import time
from typing import Any, Dict

import httpx

_COOLDOWN_UNTIL: Dict[str, float] = {}

def _env(name: str, default: str = "") -> str:
    return os.getenv(name, default).strip()

def _cooldown(model: str, seconds: int) -> None:
    _COOLDOWN_UNTIL[model] = time.time() + seconds

def _is_cooled(model: str) -> bool:
    return time.time() < _COOLDOWN_UNTIL.get(model, 0)

def _gemini(model: str, prompt: str) -> str:
    key = _env("GEMINI_API_KEY")
    if not key:
        raise RuntimeError("GEMINI_API_KEY is not configured")
    if _is_cooled(model):
        raise RuntimeError(f"Gemini model {model} is cooling down")

    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"
    payload = {"contents": [{"parts": [{"text": prompt}]}]}

    with httpx.Client(timeout=120) as client:
        r = client.post(url, params={"key": key}, json=payload)
        if r.status_code == 429:
            _cooldown(model, 900)
            raise RuntimeError(f"Gemini {model} quota/rate limited (cooldown 15m)")
        if r.status_code in {502, 503, 504}:
            _cooldown(model, 60)
            raise RuntimeError(f"Gemini {model} temporarily unavailable (cooldown 60s)")
        r.raise_for_status()
        return r.json()["candidates"][0]["content"]["parts"][0]["text"]

def _openrouter(model: str, prompt: str) -> str:
    key = _env("OPENROUTER_API_KEY")
    if not key:
        raise RuntimeError("OPENROUTER_API_KEY is not configured")
    url = "https://openrouter.ai/api/v1/chat/completions"
    payload = {
        "model": model or "openrouter/free",
        "messages": [{"role": "user", "content": prompt}],
    }
    with httpx.Client(timeout=120) as client:
        r = client.post(url, headers={"Authorization": f"Bearer {key}"}, json=payload)
        r.raise_for_status()
        return r.json()["choices"][0]["message"]["content"]

def _cerebras(model: str, prompt: str) -> str:
    key = _env("CEREBRAS_API_KEY")
    if not key:
        raise RuntimeError("CEREBRAS_API_KEY is not configured")
    url = "https://api.cerebras.ai/v1/chat/completions"
    payload = {
        "model": model or "gpt-oss-120b",
        "messages": [{"role": "user", "content": prompt}],
    }
    with httpx.Client(timeout=120) as client:
        r = client.post(url, headers={"Authorization": f"Bearer {key}"}, json=payload)
        r.raise_for_status()
        return r.json()["choices"][0]["message"]["content"]

def generate(prompt: str, **_: Any) -> str:
    errors = []

    primary = _env("GEMINI_MODEL", "gemini-3.6-flash")
    fallback = _env("GEMINI_FALLBACK_MODEL", "gemini-3.5-flash-lite")

    for model in (primary, fallback):
        if _is_cooled(model):
            errors.append(f"gemini:{model}:cooldown")
            continue
        try:
            result = _gemini(model, prompt)
            print(f"[AI] success provider=gemini model={model}")
            return result
        except Exception as exc:
            errors.append(f"gemini:{model}:{exc}")

    try:
        result = _openrouter(_env("OPENROUTER_MODEL", "openrouter/free"), prompt)
        print("[AI] success provider=openrouter")
        return result
    except Exception as exc:
        errors.append(f"openrouter:{exc}")

    try:
        result = _cerebras(_env("CEREBRAS_MODEL", "gpt-oss-120b"), prompt)
        print("[AI] success provider=cerebras")
        return result
    except Exception as exc:
        errors.append(f"cerebras:{exc}")

    raise RuntimeError("All text AI providers exhausted: " + " | ".join(errors))
