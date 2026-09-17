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

OUTPUT_DIR = Path(os.getenv("ARIA_OUTPUT_DIR", "outputs/media-test"))
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


def _hf_token() -> Optional[str]:
    return (
        os.getenv("HF_TOKEN")
        or os.getenv("HF_TOKEN_1")
        or os.getenv("HUGGINGFACEHUB_API_TOKEN")
    )


def _save_bytes(data: bytes, output_path: Path) -> str:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_bytes(data)
    return str(output_path)


def _download(url: str, output_path: Path) -> str:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with httpx.Client(timeout=300.0, follow_redirects=True) as client:
        response = client.get(url)
        response.raise_for_status()
        output_path.write_bytes(response.content)
    return str(output_path)


def elevenlabs_tts(text: str, output_path: Optional[str] = None, **kwargs) -> Optional[str]:
    api_key = os.getenv("ELEVENLABS_API_KEY")
    if not api_key:
        raise RuntimeError("ELEVENLABS_API_KEY is not configured")

    voice_id = os.getenv("ELEVENLABS_VOICE_ID") or "JBFqnCBsd6RMkjVDRZzb"
    model_id = os.getenv("ELEVENLABS_MODEL_ID") or "eleven_multilingual_v2"
    output = Path(output_path or OUTPUT_DIR / "tts-elevenlabs.mp3")

    with httpx.Client(timeout=180.0, follow_redirects=True) as client:
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
        return _save_bytes(response.content, output)


def huggingface_tts(text: str, output_path: Optional[str] = None, **kwargs) -> Optional[str]:
    if InferenceClient is None:
        raise RuntimeError("huggingface_hub is not installed")

    token = _hf_token()
    if not token:
        raise RuntimeError("HF token is not configured")

    provider = os.getenv("HF_TTS_PROVIDER", "replicate")
    model = os.getenv("HF_TTS_MODEL", "hexgrad/Kokoro-82M")
    output = Path(output_path or OUTPUT_DIR / "tts-huggingface.flac")

    client = InferenceClient(
        provider=provider,
        api_key=token,
        timeout=180,
    )

    audio = client.text_to_speech(
        text,
        model=model,
        extra_body={"voice": kwargs.get("voice", "af_nicole")},
    )

    if isinstance(audio, bytes):
        return _save_bytes(audio, output)
    if isinstance(audio, bytearray):
        return _save_bytes(bytes(audio), output)

    raise RuntimeError(
        f"Unsupported Hugging Face TTS response: {type(audio).__name__}"
    )


def fal_music(prompt: str, output_path: Optional[str] = None, **kwargs) -> Optional[str]:
    if fal_client is None:
        raise RuntimeError("fal-client is not installed")
    if not os.getenv("FAL_KEY"):
        raise RuntimeError("FAL_KEY is not configured")

    model = os.getenv(
        "FAL_MUSIC_MODEL",
        "fal-ai/stable-audio-3/small/music/text-to-audio",
    )
    output = Path(output_path or OUTPUT_DIR / "music-fal.mp3")

    result = fal_client.subscribe(
        model,
        arguments={
            "prompt": prompt,
            "duration": kwargs.get("duration", 8),
            "output_format": kwargs.get("output_format", "mp3"),
        },
        with_logs=False,
    )

    if not isinstance(result, dict):
        raise RuntimeError("FAL Music returned an invalid result")

    audio = result.get("audio")
    if isinstance(audio, dict) and audio.get("url"):
        return _download(audio["url"], output)
    if isinstance(result.get("audio_url"), str):
        return _download(result["audio_url"], output)

    raise RuntimeError("FAL Music response did not contain an audio URL")


def huggingface_musicgen(prompt: str, output_path: Optional[str] = None, **kwargs) -> Optional[str]:
    if InferenceClient is None:
        raise RuntimeError("huggingface_hub is not installed")

    token = _hf_token()
    if not token:
        raise RuntimeError("HF token is not configured")

    provider = os.getenv("HF_MUSIC_PROVIDER", "fal-ai")
    model = os.getenv(
        "HF_MUSIC_MODEL",
        "m-a-p/YuE-s1-7B-anneal-en-cot",
    )
    output = Path(output_path or OUTPUT_DIR / "music-huggingface.mp3")

    client = InferenceClient(
        provider=provider,
        model=model,
        api_key=token,
        timeout=600,
    )

    lyrics = kwargs.get("lyrics", prompt)
    genres = kwargs.get(
        "genres",
        "professional cinematic technology background music",
    )

    audio = client.text_to_speech(
        lyrics,
        extra_body={"genres": genres},
    )

    if isinstance(audio, bytes):
        return _save_bytes(audio, output)
    if isinstance(audio, bytearray):
        return _save_bytes(bytes(audio), output)

    raise RuntimeError(
        f"Unsupported Hugging Face Music response: {type(audio).__name__}"
    )


MUSIC_PROVIDERS = {
    "huggingface_musicgen": huggingface_musicgen,
    "fal_music": fal_music,
}

TTS_PROVIDERS = {
    "huggingface_tts": huggingface_tts,
    "elevenlabs_tts": elevenlabs_tts,
}
