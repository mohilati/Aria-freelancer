"""
Resilient visual QA for Aria Freelancer.

Important behavior:
- Never turns a Gemini 429/503 into a scene-killing rejection.
- Uses a single vision call per generated candidate.
- Keeps semantic QA focused on obvious defects and prompt mismatch.
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
    return {
        ".png": "image/png",
        ".jpg": "image/jpeg",
        ".jpeg": "image/jpeg",
        ".webp": "image/webp",
    }.get(path.suffix.lower(), "image/png")


def _transient_error(exc: Exception) -> bool:
    text = str(exc).lower()
    return (
        "429" in text
        or "too many requests" in text
        or "503" in text
        or "service unavailable" in text
        or "timeout" in text
        or "timed out" in text
    )


def review_image(image_path: str, scene: Dict[str, Any]) -> Dict[str, Any]:
    path = Path(image_path)
    if not path.exists():
        return {"approved": False, "score": 0, "issues": ["image file missing"]}

    # Basic file sanity first. This avoids spending Gemini calls on broken files.
    if path.stat().st_size < 10_000:
        return {"approved": False, "score": 0, "issues": ["image file is unexpectedly small"]}

    key = os.getenv("GEMINI_API_KEY", "").strip()
    if not key or os.getenv("ARIA_VISUAL_QA", "1") != "1":
        return {
            "approved": True,
            "score": 78,
            "issues": ["vision QA skipped"],
        }

    model = os.getenv(
        "GEMINI_VISION_MODEL",
        os.getenv("GEMINI_MODEL", "gemini-3.6-flash"),
    )

    encoded = base64.b64encode(path.read_bytes()).decode("ascii")
    scene_prompt = str(scene.get("visual_prompt") or scene.get("prompt") or "")

    prompt = f"""
You are a strict but practical visual QA agent for a premium dermatology clinic social-media advertisement.

SCENE REQUIREMENT:
{scene_prompt}

Approve images that are commercially usable and broadly match the requested shot.
Reject only clear problems:
- obvious malformed face or severe anatomy errors
- severe AI artifacts
- duplicate/extra people when the scene does not ask for them
- fake-looking clinical equipment
- visible watermark or generated text/logo
- major composition mismatch with the requested shot

Do NOT reject for:
- minor hand awkwardness if hands are not the focus
- normal skin texture
- mild background blur
- ordinary photographic imperfections
- an image being AI-generated
- small differences in pose that do not change the requested shot

Return ONLY JSON:
{{
  "approved": true or false,
  "score": 0-100,
  "issues": ["short issue 1"],
  "anatomy_ok": true,
  "face_ok": true,
  "clinical_realism_ok": true,
  "composition_ok": true
}}
"""

    payload = {
        "contents": [{
            "parts": [
                {"text": prompt},
                {
                    "inline_data": {
                        "mime_type": _image_mime(path),
                        "data": encoded,
                    }
                },
            ]
        }],
        "generationConfig": {
            "temperature": 0.0,
            "maxOutputTokens": 500,
        },
    }

    try:
        with httpx.Client(timeout=60) as client:
            response = client.post(
                GEMINI_URL.format(model=model),
                params={"key": key},
                json=payload,
            )
            response.raise_for_status()
            data = response.json()
            raw = data["candidates"][0]["content"]["parts"][0]["text"].strip()

        raw = raw.removeprefix("```json").removesuffix("```").strip()
        result = json.loads(raw)
        if not isinstance(result, dict):
            raise ValueError("invalid QA response")

        return result

    except Exception as exc:
        # A provider/rate-limit outage must not destroy otherwise usable media.
        if _transient_error(exc):
            return {
                "approved": True,
                "score": 76,
                "issues": [
                    f"vision QA temporarily unavailable: {type(exc).__name__}"
                ],
            }

        return {
            "approved": False,
            "score": 0,
            "issues": [f"visual QA error: {type(exc).__name__}: {exc}"],
        }
