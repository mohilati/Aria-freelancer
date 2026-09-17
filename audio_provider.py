import base64
import os
import uuid
from pathlib import Path
from typing import Any, Optional

import httpx

OUTPUT_DIR = Path(os.getenv("ARIA_OUTPUT_DIR", "outputs"))
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

ELEVENLABS_API_KEY = os.getenv("ELEVENLABS_API_KEY")
# Public/default voice fallback so a missing GitHub Variable does not disable TTS.
ELEVENLABS_VOICE_ID = os.getenv("ELEVENLABS_VOICE_ID", "JBFqnCBsd6RMkjVDRZzb")
ELEVENLABS_MODEL_ID = os.getenv("ELEVENLABS_MODEL_ID", "eleven_multilingual_v2")

HF_TOKEN = os.getenv("HF_TOKEN") or os.getenv("HF_TOKEN_1") or os.getenv("HUGGINGFACEHUB_API_TOKEN")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
FAL_KEY = os.getenv("FAL_KEY")

HF_TTS_MODEL = os.getenv("HF_TTS_MODEL", "espnet/kan-bayashi_ljspeech_vits")
HF_MUSIC_MODEL = os.getenv("HF_MUSIC_MODEL", "facebook/musicgen-small")
LYRIA_MODEL = os.getenv("LYRIA_MODEL", "lyria-3.5")
FAL_MUSIC_MODEL = os.getenv("FAL_MUSIC_MODEL", "fal-ai/stable-audio-3/small/music/text-to-audio")


def _save(data: bytes, suffix: str) -> str:
    path = OUTPUT_DIR / f"audio-{uuid.uuid4().hex}{suffix}"
    path.write_bytes(data)
    return str(path)


def elevenlabs_tts(text: str, **kwargs: Any) -> Optional[str]:
    if not ELEVENLABS_API_KEY:
        return None

    response = httpx.post(
        f"https://api.elevenlabs.io/v1/text-to-speech/{ELEVENLABS_VOICE_ID}",
        params={"output_format": "mp3_44100_128"},
        headers={
            "xi-api-key": ELEVENLABS_API_KEY,
            "Content-Type": "application/json",
        },
        json={
            "text": text,
            "model_id": ELEVENLABS_MODEL_ID,
        },
        timeout=120.0,
    )
    response.raise_for_status()
    return _save(response.content, ".mp3")


def huggingface_tts(text: str, **kwargs: Any) -> Optional[str]:
    if not HF_TOKEN:
        return None

    from huggingface_hub import InferenceClient

    client = InferenceClient(
        provider=os.getenv("HF_TTS_PROVIDER", "hf-inference"),
        api_key=HF_TOKEN,
    )
    audio = client.text_to_speech(text, model=HF_TTS_MODEL)
    return _save(bytes(audio), ".wav")


def lyria_music(prompt: str, **kwargs: Any) -> Optional[str]:
    if not GEMINI_API_KEY:
        return None

    import time

    endpoint = (
        f"https://generativelanguage.googleapis.com/v1beta/models/"
        f"{LYRIA_MODEL}:generateContent"
    )

    last_error = None
    for attempt in range(3):
        try:
            response = httpx.post(
                endpoint,
                params={"key": GEMINI_API_KEY},
                headers={"Content-Type": "application/json"},
                json={
                    "contents": [{"parts": [{"text": prompt}]}],
                    "generationConfig": {"responseModalities": ["AUDIO", "TEXT"]},
                },
                timeout=180.0,
            )
            response.raise_for_status()
            payload = response.json()

            for candidate in payload.get("candidates", []):
                for part in candidate.get("content", {}).get("parts", []):
                    inline = part.get("inlineData") or part.get("inline_data")
                    if inline and inline.get("data"):
                        mime = inline.get("mimeType") or inline.get("mime_type") or "audio/wav"
                        suffix = ".mp3" if "mpeg" in mime or "mp3" in mime else ".wav"
                        return _save(base64.b64decode(inline["data"]), suffix)

            raise RuntimeError("Lyria returned no inline audio")
        except httpx.HTTPStatusError as exc:
            last_error = exc
            if exc.response.status_code == 429:
                time.sleep(2 ** attempt)
                continue
            raise

    raise last_error or RuntimeError("Lyria request failed")


def fal_music(prompt: str, **kwargs: Any) -> Optional[str]:
    if not FAL_KEY:
        return None

    import fal_client

    result = fal_client.subscribe(
        FAL_MUSIC_MODEL,
        arguments={
            "prompt": prompt,
            "duration": int(kwargs.get("duration", 15)),
            "output_format": "mp3",
            "bitrate": "192k",
        },
    )
    audio = result.get("audio") or result.get("audio_file") or {}
    url = audio.get("url")
    if not url:
        raise RuntimeError("fal returned no music output")

    response = httpx.get(url, timeout=180.0, follow_redirects=True)
    response.raise_for_status()
    return _save(response.content, ".mp3")


TTS_PROVIDERS = {
    "elevenlabs_tts": elevenlabs_tts,
    "huggingface_tts": huggingface_tts,
}

MUSIC_PROVIDERS = {
    "fal_music": fal_music,
    "lyria_music": lyria_music,
    "huggingface_musicgen": lambda prompt, **kwargs: None,
}
