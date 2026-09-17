import base64
import os
import time
import uuid
from pathlib import Path
from typing import Any, Optional

import httpx

OUTPUT_DIR = Path(os.getenv("ARIA_OUTPUT_DIR", "outputs"))
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

HF_TOKEN = os.getenv("HF_TOKEN") or os.getenv("HF_TOKEN_1") or os.getenv("HUGGINGFACEHUB_API_TOKEN")
ELEVENLABS_API_KEY = os.getenv("ELEVENLABS_API_KEY")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

HF_TTS_MODEL = os.getenv("HF_TTS_MODEL", "espnet/kan-bayashi_ljspeech_vits")
HF_MUSIC_MODEL = os.getenv("HF_MUSIC_MODEL", "facebook/musicgen-small")
ELEVENLABS_VOICE_ID = os.getenv("ELEVENLABS_VOICE_ID", "")
ELEVENLABS_MODEL_ID = os.getenv("ELEVENLABS_MODEL_ID", "eleven_multilingual_v2")
LYRIA_MODEL = os.getenv("LYRIA_MODEL", "lyria-3.5")


def _save(data: bytes, suffix: str) -> str:
    path = OUTPUT_DIR / f"audio-{uuid.uuid4().hex}{suffix}"
    path.write_bytes(data)
    return str(path)


def elevenlabs_tts(text: str, **kwargs: Any) -> Optional[str]:
    if not ELEVENLABS_API_KEY or not ELEVENLABS_VOICE_ID:
        return None

    url = f"https://api.elevenlabs.io/v1/text-to-speech/{ELEVENLABS_VOICE_ID}"
    headers = {
        "xi-api-key": ELEVENLABS_API_KEY,
        "Content-Type": "application/json",
        "Accept": "audio/mpeg",
    }
    payload = {
        "text": text,
        "model_id": ELEVENLABS_MODEL_ID,
    }

    with httpx.Client(timeout=180.0, follow_redirects=True) as client:
        response = client.post(url, headers=headers, json=payload)
        response.raise_for_status()
        return _save(response.content, ".mp3")


def huggingface_tts(text: str, **kwargs: Any) -> Optional[str]:
    if not HF_TOKEN:
        return None

    url = f"https://api-inference.huggingface.co/models/{HF_TTS_MODEL}"
    headers = {"Authorization": f"Bearer {HF_TOKEN}"}

    with httpx.Client(timeout=180.0, follow_redirects=True) as client:
        response = client.post(url, headers=headers, json={"inputs": text})
        response.raise_for_status()
        if not response.content:
            raise RuntimeError("Hugging Face TTS returned empty audio")
        return _save(response.content, ".wav")


def lyria_music(prompt: str, **kwargs: Any) -> Optional[str]:
    if not GEMINI_API_KEY:
        return None

    url = f"https://generativelanguage.googleapis.com/v1beta/models/{LYRIA_MODEL}:generateContent"
    headers = {
        "x-goog-api-key": GEMINI_API_KEY,
        "Content-Type": "application/json",
    }
    payload = {
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {
            "responseModalities": ["AUDIO", "TEXT"],
        },
    }

    with httpx.Client(timeout=300.0, follow_redirects=True) as client:
        response = client.post(url, headers=headers, json=payload)
        response.raise_for_status()
        data = response.json()

    parts = []
    for candidate in data.get("candidates", []):
        parts.extend(candidate.get("content", {}).get("parts", []))

    for part in parts:
        inline = part.get("inlineData") or part.get("inline_data")
        if inline and inline.get("data"):
            mime = inline.get("mimeType") or inline.get("mime_type", "audio/mpeg")
            raw = base64.b64decode(inline["data"])
            suffix = ".wav" if "wav" in mime else ".mp3"
            return _save(raw, suffix)

    raise RuntimeError("Lyria returned no inline audio data")


def huggingface_musicgen(prompt: str, **kwargs: Any) -> Optional[str]:
    if not HF_TOKEN:
        return None

    url = f"https://api-inference.huggingface.co/models/{HF_MUSIC_MODEL}"
    headers = {"Authorization": f"Bearer {HF_TOKEN}"}

    with httpx.Client(timeout=300.0, follow_redirects=True) as client:
        response = client.post(url, headers=headers, json={"inputs": prompt})
        response.raise_for_status()
        if not response.content:
            raise RuntimeError("MusicGen returned empty audio")
        return _save(response.content, ".wav")


TTS_PROVIDERS = {
    "elevenlabs_tts": elevenlabs_tts,
    "huggingface_tts": huggingface_tts,
}

MUSIC_PROVIDERS = {
    "lyria_music": lyria_music,
    "huggingface_musicgen": huggingface_musicgen,
}
