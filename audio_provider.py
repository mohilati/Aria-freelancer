import os
from pathlib import Path
from typing import Optional

import httpx

try:
    import fal_client
except ImportError:
    fal_client = None

try:
    from huggingface_hub import InferenceClient
except ImportError:
    InferenceClient = None


OUTPUT_DIR = Path(
    os.getenv("ARIA_OUTPUT_DIR", "outputs/media-test")
)
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


# ============================================================
# Helpers
# ============================================================

def _hf_token() -> Optional[str]:
    return (
        os.getenv("HF_TOKEN")
        or os.getenv("HF_TOKEN_1")
        or os.getenv("HUGGINGFACEHUB_API_TOKEN")
    )


def _download(url: str, output_path: Path) -> str:
    output_path.parent.mkdir(parents=True, exist_ok=True)

    with httpx.Client(
        timeout=180.0,
        follow_redirects=True,
    ) as client:
        response = client.get(url)
        response.raise_for_status()
        output_path.write_bytes(response.content)

    return str(output_path)


def _hf_client(provider: str = "auto"):
    if InferenceClient is None:
        raise RuntimeError(
            "huggingface_hub is not installed"
        )

    token = _hf_token()

    if not token:
        raise RuntimeError(
            "HF token is not configured"
        )

    return InferenceClient(
        provider=provider,
        api_key=token,
    )


# ============================================================
# ElevenLabs TTS
# ============================================================

def elevenlabs_tts(
    text: str,
    output_path: Optional[str] = None,
    **kwargs,
) -> Optional[str]:

    api_key = os.getenv("ELEVENLABS_API_KEY")

    if not api_key:
        raise RuntimeError(
            "ELEVENLABS_API_KEY is not configured"
        )

    voice_id = (
        os.getenv("ELEVENLABS_VOICE_ID")
        or "JBFqnCBsd6RMkjVDRZzb"
    )

    model_id = (
        os.getenv("ELEVENLABS_MODEL_ID")
        or "eleven_multilingual_v2"
    )

    output = Path(
        output_path
        or OUTPUT_DIR / "tts-elevenlabs.mp3"
    )

    url = (
        "https://api.elevenlabs.io/v1/text-to-speech/"
        f"{voice_id}"
    )

    payload = {
        "text": text,
        "model_id": model_id,
        "output_format": "mp3_44100_128",
    }

    headers = {
        "xi-api-key": api_key,
        "Content-Type": "application/json",
        "Accept": "audio/mpeg",
    }

    with httpx.Client(
        timeout=180.0,
        follow_redirects=True,
    ) as client:
        response = client.post(
            url,
            headers=headers,
            json=payload,
        )

        response.raise_for_status()

        output.parent.mkdir(
            parents=True,
            exist_ok=True,
        )

        output.write_bytes(response.content)

    return str(output)


# ============================================================
# Hugging Face TTS
# ============================================================

def huggingface_tts(
    text: str,
    output_path: Optional[str] = None,
    **kwargs,
) -> Optional[str]:

    if InferenceClient is None:
        raise RuntimeError(
            "huggingface_hub is not installed"
        )

    token = _hf_token()

    if not token:
        raise RuntimeError(
            "HF token is not configured"
        )

    provider = os.getenv(
        "HF_TTS_PROVIDER",
        "auto",
    )

    model = os.getenv(
        "HF_TTS_MODEL",
        "hexgrad/Kokoro-82M",
    )

    client = InferenceClient(
        provider=provider,
        api_key=token,
    )

    output = Path(
        output_path
        or OUTPUT_DIR / "tts-huggingface.flac"
    )

    output.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    audio = client.text_to_speech(
        text=text,
        model=model,
    )

    if audio is None:
        raise RuntimeError(
            "Hugging Face returned no TTS audio"
        )

    if isinstance(audio, bytes):
        output.write_bytes(audio)
        return str(output)

    if hasattr(audio, "read"):
        data = audio.read()

        if data:
            output.write_bytes(data)
            return str(output)

    raise RuntimeError(
        "Unsupported Hugging Face TTS response: "
        f"{type(audio).__name__}"
    )


# ============================================================
# FAL Music
# ============================================================

def fal_music(
    prompt: str,
    output_path: Optional[str] = None,
    **kwargs,
) -> Optional[str]:

    if fal_client is None:
        raise RuntimeError(
            "fal-client is not installed"
        )

    if not os.getenv("FAL_KEY"):
        raise RuntimeError(
            "FAL_KEY is not configured"
        )

    model = (
        os.getenv("FAL_MUSIC_MODEL")
        or "fal-ai/stable-audio-3/small/music/text-to-audio"
    )

    duration = kwargs.get(
        "duration",
        15,
    )

    output_format = kwargs.get(
        "output_format",
        "mp3",
    )

    output = Path(
        output_path
        or OUTPUT_DIR / "music-fal.mp3"
    )

    result = fal_client.subscribe(
        model,
        arguments={
            "prompt": prompt,
            "duration": duration,
            "output_format": output_format,
        },
        with_logs=False,
    )

    if not result:
        raise RuntimeError(
            "FAL Music returned no result"
        )

    audio = result.get("audio")

    audio_url = None

    if isinstance(audio, dict):
        audio_url = audio.get("url")

    if not audio_url:
        audio_url = result.get("audio_url")

    if not audio_url:
        raise RuntimeError(
            "FAL Music response did not contain "
            "an audio URL"
        )

    return _download(
        audio_url,
        output,
    )


# ============================================================
# Google Lyria Music
# ============================================================

def lyria_music(
    prompt: str,
    output_path: Optional[str] = None,
    **kwargs,
) -> Optional[str]:

    api_key = os.getenv("GEMINI_API_KEY")

    if not api_key:
        raise RuntimeError(
            "GEMINI_API_KEY is not configured"
        )

    model = (
        os.getenv("LYRIA_MODEL")
        or "lyria-3.5"
    )

    output = Path(
        output_path
        or OUTPUT_DIR / "music-lyria.wav"
    )

    url = (
        "https://generativelanguage.googleapis.com/"
        f"v1beta/models/{model}:generateContent"
    )

    payload = {
        "contents": [
            {
                "parts": [
                    {
                        "text": prompt,
                    }
                ]
            }
        ]
    }

    headers = {
        "Content-Type": "application/json",
        "x-goog-api-key": api_key,
    }

    last_error = None

    for attempt in range(3):
        try:
            with httpx.Client(
                timeout=180.0,
                follow_redirects=True,
            ) as client:
                response = client.post(
                    url,
                    headers=headers,
                    json=payload,
                )

            if response.status_code == 429:
                last_error = (
                    "Lyria rate limited: HTTP 429"
                )

                if attempt < 2:
                    import time
                    time.sleep(2 ** attempt)

                continue

            response.raise_for_status()

            data = response.json()

            audio_bytes = None

            candidates = data.get(
                "candidates",
                [],
            )

            for candidate in candidates:
                content = candidate.get(
                    "content",
                    {},
                )

                for part in content.get(
                    "parts",
                    [],
                ):
                    inline_data = part.get(
                        "inlineData"
                    )

                    if (
                        inline_data
                        and inline_data.get("data")
                    ):
                        import base64

                        audio_bytes = (
                            base64.b64decode(
                                inline_data["data"]
                            )
                        )

                        break

                if audio_bytes:
                    break

            if not audio_bytes:
                raise RuntimeError(
                    "Lyria response did not contain "
                    "audio data"
                )

            output.parent.mkdir(
                parents=True,
                exist_ok=True,
            )

            output.write_bytes(
                audio_bytes
            )

            return str(output)

        except Exception as exc:
            last_error = exc

            if attempt < 2:
                import time
                time.sleep(2 ** attempt)

    raise RuntimeError(
        f"Lyria failed after retries: {last_error}"
    )


# ============================================================
# Provider registries
# ============================================================

TTS_PROVIDERS = {
    "elevenlabs_tts": elevenlabs_tts,
    "huggingface_tts": huggingface_tts,
}


MUSIC_PROVIDERS = {
    "fal_music": fal_music,
    "lyria_music": lyria_music,
}
