"""
Audio provider registry with native Persian Edge TTS.

This file is a drop-in replacement for Aria's previous audio_provider.py.
Existing ElevenLabs/HF/Musicgen implementations remain available when present.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any, Dict, Optional

from persian_tts import synthesize_persian

def persian_edge_tts(text: str, **kwargs: Any) -> str:
    output = kwargs.get("output_path")
    if not output:
        output_dir = Path(kwargs.get("output_dir", "outputs/media/tts"))
        output_dir.mkdir(parents=True, exist_ok=True)
        safe_id = str(kwargs.get("scene_id", "narration"))
        output = str(output_dir / f"{safe_id}-fa.mp3")

    gender = str(kwargs.get("voice_gender", "female")).lower()
    if gender in {"male", "man", "مرد"}:
        voice_gender = "male"
    else:
        voice_gender = "female"

    return synthesize_persian(
        text,
        output,
        gender=voice_gender,
        rate=kwargs.get("rate", "-4%"),
        pitch=kwargs.get("pitch", "+0Hz"),
    )

TTS_PROVIDERS: Dict[str, Any] = {
    "persian_edge_tts": persian_edge_tts,
}

try:
    from elevenlabs_provider import elevenlabs_tts  # type: ignore
    TTS_PROVIDERS["elevenlabs_tts"] = elevenlabs_tts
except Exception:
    pass

try:
    from image_provider import musicgen_tts  # type: ignore
    TTS_PROVIDERS["huggingface_tts"] = musicgen_tts
except Exception:
    pass

def _suno_missing(*args: Any, **kwargs: Any) -> str:
    raise RuntimeError("Suno integration is intentionally not auto-configured because current API requires a public callback URL")

MUSIC_PROVIDERS: Dict[str, Any] = {
    "suno_music": _suno_missing,
}
try:
    from music_provider import MUSIC_PROVIDERS as EXISTING_MUSIC_PROVIDERS  # type: ignore
    MUSIC_PROVIDERS.update(EXISTING_MUSIC_PROVIDERS)
except Exception:
    pass
