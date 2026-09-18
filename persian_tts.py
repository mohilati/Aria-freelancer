"""
Persian-first TTS for Aria Freelancer.

Primary voice:
- Microsoft Edge neural Persian voices through edge-tts.
- fa-IR-DilaraNeural (female)
- fa-IR-FaridNeural (male)

The module deliberately avoids Kokoro as the default for Persian because
the project needs a native Persian voice rather than an English-oriented
fallback.

No API key is required by edge-tts, but the GitHub runner needs internet access.
"""

from __future__ import annotations

import asyncio
import re
from pathlib import Path
from typing import Optional

import edge_tts

PERSIAN_VOICES = {
    "female": "fa-IR-DilaraNeural",
    "male": "fa-IR-FaridNeural",
}

_DIGIT_MAP = str.maketrans(
    "0123456789",
    "۰۱۲۳۴۵۶۷۸۹",
)

def normalize_persian_for_tts(text: str) -> str:
    """Make generated Persian easier for neural TTS to pronounce naturally."""
    if not text:
        return ""

    text = str(text)
    replacements = {
        "\u200c": "\u200c",  # keep Persian half-space
        "ي": "ی",
        "ى": "ی",
        "ك": "ک",
        "ۀ": "هٔ",
        "ة": "ه",
        "ؤ": "ؤ",
        "إ": "ا",
        "أ": "ا",
        "ئ": "یٔ",
        "ـ": "",
        "...": "…",
    }
    for old, new in replacements.items():
        text = text.replace(old, new)

    # Make western digits Persian so the voice is less likely to switch
    # pronunciation patterns mid-sentence.
    text = text.translate(_DIGIT_MAP)

    # Replace common punctuation with natural speech pauses.
    text = re.sub(r"[|/]+", "، ", text)
    text = re.sub(r"\s*-\s*", "، ", text)
    text = re.sub(r"\s{2,}", " ", text)

    # Avoid accidental markdown/emoji artifacts in spoken audio.
    text = re.sub(r"[*_`#>]+", " ", text)
    text = re.sub(r"\s{2,}", " ", text).strip()

    return text

async def _save(text: str, output: str, voice: str, rate: str, pitch: str) -> str:
    communicate = edge_tts.Communicate(
        text,
        voice=voice,
        rate=rate,
        pitch=pitch,
    )
    await communicate.save(output)
    return output

def synthesize_persian(
    text: str,
    output_path: str,
    gender: str = "female",
    rate: str = "-4%",
    pitch: str = "+0Hz",
) -> str:
    """Synthesize Persian narration and return an MP3 path."""
    cleaned = normalize_persian_for_tts(text)
    if not cleaned:
        raise ValueError("Persian TTS received empty text")

    voice = PERSIAN_VOICES.get(gender, PERSIAN_VOICES["female"])
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)

    asyncio.run(_save(cleaned, str(path), voice, rate, pitch))

    if not path.exists() or path.stat().st_size < 1000:
        raise RuntimeError("Persian TTS produced an empty or invalid audio file")

    return str(path)

def voice_for_job(job: dict) -> str:
    requested = str(job.get("voice_gender") or job.get("narrator_gender") or "female").lower()
    return "male" if requested in {"male", "man", "مرد"} else "female"
