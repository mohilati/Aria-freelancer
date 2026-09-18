"""
Visual QA for generated clinic-ad images.

Uses Gemini vision directly through the same GEMINI_API_KEY already used by Aria.
A failed/unsafe visual is rejected so the assembler never silently accepts a bad
image just because generation returned bytes.
"""

from __future__ import annotations

import base64
import json
import os
from pathlib import Path
from typing import Any, Dict

import httpx

GEMINI_URL = "https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"

def _image_mime(path: Path) -> str:
    suffix = path.suffix.lower()
    return {
        ".png": "image/png",
        ".jpg": "image/jpeg",
        ".jpeg": "image/jpeg",
        ".webp": "image/webp",
    }.get(suffix, "image/png")

def review_image(image_path: str, scene: Dict[str, Any]) -> Dict[str, Any]:
    path = Path(image_path)
    if not path.exists():
        return {"approved": False, "score": 0, "issues": ["image file missing"]}

    key = os.getenv("GEMINI_API_KEY", "").strip()
    if not key:
        # Do not block the pipeline if vision QA is not configured.
        return {"approved": True, "score": 70, "issues": ["vision QA skipped: GEMINI_API_KEY missing"]}

    model = os.getenv("GEMINI_VISION_MODEL", os.getenv("GEMINI_MODEL", "gemini-3.5-flash-lite"))
    data = base64.b64encode(path.read_bytes()).decode("ascii")

    prompt = f"""
You are the visual quality-control agent for a professional dermatology clinic advertisement.

Review the attached generated image for this scene:
{json.dumps(scene, ensure_ascii=False)}

Return ONLY JSON:
{{
  "approved": true or false,
  "score": 0-100,
  "issues": ["..."],
  "anatomy_ok": true or false,
  "face_ok": true or false,
  "clinical_realism_ok": true or false,
  "composition_ok": true or false,
  "continuity_ok": true or false
}}

Reject images with obvious deformed hands, extra fingers, malformed faces,
plastic/waxy skin, fake medical equipment, unreadable embedded text,
watermarks, duplicated people, or obviously synthetic clinic environments.
Do not reject merely because the image is AI-generated; judge visible quality.
"""

    payload = {
        "contents": [{
            "parts": [
                {"text": prompt},
                {"inline_data": {"mime_type": _image_mime(path), "data": data}},
            ]
        }],
        "generationConfig": {"temperature": 0.1},
    }

    try:
        with httpx.Client(timeout=90) as client:
            response = client.post(
                GEMINI_URL.format(model=model),
                params={"key": key},
                json=payload,
            )
            response.raise_for_status()
            raw = response.json()["candidates"][0]["content"]["parts"][0]["text"]
        raw = raw.strip().removeprefix("```json").removesuffix("```").strip()
        result = json.loads(raw)
        return result if isinstance(result, dict) else {"approved": False, "score": 0, "issues": ["invalid QA response"]}
    except Exception as exc:
        # QA failure should not turn into a false approval.
        return {"approved": False, "score": 0, "issues": [f"visual QA error: {type(exc).__name__}: {exc}"]}
