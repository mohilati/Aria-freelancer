from __future__ import annotations

import os
import time
from pathlib import Path
from typing import Optional

import httpx

OUTPUT_DIR = Path(os.getenv("ARIA_OUTPUT_DIR", "outputs"))
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


def _hf_token() -> Optional[str]:
    return (
        os.getenv("HF_TOKEN")
        or os.getenv("HF_TOKEN_1")
        or os.getenv("HUGGINGFACEHUB_API_TOKEN")
    )


def _save(data: bytes, output_path: Optional[str], suffix: str) -> str:
    path = Path(
        output_path
        or OUTPUT_DIR / f"audio-{time.time_ns()}{suffix}"
    )
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(data)
    return str(path)


def _download(url: str, output_path: Optional[str], suffix: str) -> str:
    with httpx.Client(timeout=900, follow_redirects=True) as client:
        response = client.get(url)
        response.raise_for_status()
        return _save(response.content, output_path, suffix)


def huggingface_tts(
    text: str,
    output_path: Optional[str] = None,
    **kwargs,
) -> Optional[str]:
    token = _hf_token()
    if not token:
        raise RuntimeError("HF token is not configured")

    from huggingface_hub import InferenceClient

    model = kwargs.get("model") or os.getenv(
        "HF_TTS_MODEL",
        "hexgrad/Kokoro-82M",
    )
    provider = kwargs.get("provider") or os.getenv(
        "HF_TTS_PROVIDER",
        "replicate",
    )
    voice = kwargs.get("voice") or os.getenv(
        "HF_TTS_VOICE",
        "af_nicole",
    )

    client = InferenceClient(
        provider=provider,
        api_key=token,
        timeout=600,
    )
    audio = client.text_to_speech(
        text=text,
        model=model,
        extra_body={"voice": voice},
    )

    if isinstance(audio, bytes):
        return _save(audio, output_path, ".flac")
    if isinstance(audio, bytearray):
        return _save(bytes(audio), output_path, ".flac")

    raise RuntimeError(
        f"Unexpected HF TTS response: {type(audio).__name__}"
    )


def elevenlabs_tts(
    text: str,
    output_path: Optional[str] = None,
    **kwargs,
) -> Optional[str]:
    api_key = os.getenv("ELEVENLABS_API_KEY")
    if not api_key:
        raise RuntimeError("ELEVENLABS_API_KEY is not configured")

    voice_id = kwargs.get("voice_id") or os.getenv(
        "ELEVENLABS_VOICE_ID",
        "JBFqnCBsd6RMkjVDRZzb",
    )
    model_id = kwargs.get("model_id") or os.getenv(
        "ELEVENLABS_MODEL_ID",
        "eleven_multilingual_v2",
    )

    with httpx.Client(timeout=300, follow_redirects=True) as client:
        response = client.post(
            f"https://api.elevenlabs.io/v1/text-to-speech/{voice_id}",
            headers={
                "xi-api-key": api_key,
                "Content-Type": "application/json",
                "Accept": "audio/mpeg",
            },
            json={
                "text": text,
                "model_id": model_id,
                "output_format": "mp3_44100_128",
            },
        )
        response.raise_for_status()
        return _save(response.content, output_path, ".mp3")


def huggingface_musicgen(
    prompt: str,
    output_path: Optional[str] = None,
    **kwargs,
) -> Optional[str]:
    token = _hf_token()
    if not token:
        raise RuntimeError("HF token is not configured")

    from huggingface_hub import InferenceClient

    model = kwargs.get("model") or os.getenv(
        "HF_MUSIC_MODEL",
        "m-a-p/YuE-s1-7B-anneal-en-cot",
    )
    provider = kwargs.get("provider") or os.getenv(
        "HF_MUSIC_PROVIDER",
        "fal-ai",
    )

    client = InferenceClient(
        provider=provider,
        model=model,
        api_key=token,
        timeout=900,
    )

    audio = client.text_to_speech(
        kwargs.get("lyrics", prompt),
        extra_body={
            "genres": kwargs.get(
                "genres",
                "cinematic electronic technology background music",
            )
        },
    )

    if isinstance(audio, bytes):
        return _save(audio, output_path, ".mp3")
    if isinstance(audio, bytearray):
        return _save(bytes(audio), output_path, ".mp3")

    raise RuntimeError(
        f"Unexpected HF music response: {type(audio).__name__}"
    )


def fal_music(
    prompt: str,
    output_path: Optional[str] = None,
    **kwargs,
) -> Optional[str]:
    if not os.getenv("FAL_KEY"):
        raise RuntimeError("FAL_KEY is not configured")

    import fal_client

    model = kwargs.get("model") or os.getenv(
        "FAL_MUSIC_MODEL",
        "fal-ai/stable-audio-3/small/music/text-to-audio",
    )

    result = fal_client.subscribe(
        model,
        arguments={
            "prompt": prompt,
            "duration": kwargs.get("duration", 8),
            "output_format": "mp3",
        },
        with_logs=False,
    )

    audio = result.get("audio") if isinstance(result, dict) else None
    if isinstance(audio, dict) and audio.get("url"):
        return _download(audio["url"], output_path, ".mp3")
    if isinstance(audio, str):
        return _download(audio, output_path, ".mp3")
    if isinstance(result, dict) and isinstance(result.get("audio_url"), str):
        return _download(result["audio_url"], output_path, ".mp3")

    raise RuntimeError("FAL music response did not contain an audio URL")


MUSIC_PROVIDERS = {
    "huggingface_musicgen": huggingface_musicgen,
    "fal_music": fal_music,
}

TTS_PROVIDERS = {
    "huggingface_tts": huggingface_tts,
    "elevenlabs_tts": elevenlabs_tts,
}
