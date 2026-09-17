import os
from dataclasses import dataclass
from typing import Any, Callable, Dict, List, Optional
from image_provider import IMAGE_PROVIDERS
from video_provider import VIDEO_PROVIDERS
from audio_provider import TTS_PROVIDERS, MUSIC_PROVIDERS

@dataclass
class ProviderResult:
    ok: bool
    provider: str
    output_path: Optional[str] = None
    error: Optional[str] = None
    skipped: bool = False

def _env_chain(name: str, default: List[str]) -> List[str]:
    raw = os.getenv(name, "")
    return [x.strip() for x in raw.split(",") if x.strip()] if raw.strip() else default

class MediaRouter:
    def __init__(self) -> None:
        self.image_chain = _env_chain("IMAGE_PROVIDER", ["huggingface_flux", "replicate_image"])
        self.video_chain = _env_chain("VIDEO_PROVIDER", ["huggingface_video", "replicate_video", "fal_video"])
        self.tts_chain = _env_chain("TTS_PROVIDER", ["elevenlabs_tts", "huggingface_tts"])
        self.music_chain = _env_chain("MUSIC_PROVIDER", ["lyria_music", "huggingface_musicgen"])

    def _run_chain(self, chain, registry, kind, **kwargs):
        errors = []
        for name in chain:
            provider = registry.get(name)
            if provider is None:
                errors.append(f"{name}: provider not registered")
                continue
            try:
                output = provider(**kwargs)
                if output:
                    return ProviderResult(True, name, output_path=output)
                errors.append(f"{name}: returned no output")
            except Exception as exc:
                errors.append(f"{name}: {type(exc).__name__}: {exc}")
        return ProviderResult(False, "none", error=f"{kind} providers exhausted: " + " | ".join(errors), skipped=True)

    def generate_image(self, prompt: str, **kwargs): return self._run_chain(self.image_chain, IMAGE_PROVIDERS, "image", prompt=prompt, **kwargs)
    def generate_video(self, prompt: str, **kwargs): return self._run_chain(self.video_chain, VIDEO_PROVIDERS, "video", prompt=prompt, **kwargs)
    def generate_tts(self, text: str, **kwargs): return self._run_chain(self.tts_chain, TTS_PROVIDERS, "tts", text=text, **kwargs)
    def generate_music(self, prompt: str, **kwargs): return self._run_chain(self.music_chain, MUSIC_PROVIDERS, "music", prompt=prompt, **kwargs)
    def generate_audio(self, kind: str, **kwargs):
        if kind == "tts": return self.generate_tts(**kwargs)
        if kind == "music": return self.generate_music(**kwargs)
        raise ValueError(f"Unsupported audio kind: {kind}")
