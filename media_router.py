from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from aria_provider_pool import (
    generate_image,
    generate_video,
    generate_tts,
    generate_music,
    provider_stats,
)


@dataclass
class ProviderResult:
    ok: bool
    provider: str
    output_path: Optional[str] = None
    output_url: Optional[str] = None
    error: Optional[str] = None
    skipped: bool = False
    reason: Optional[str] = None


def _convert(result) -> ProviderResult:
    return ProviderResult(
        ok=bool(result.ok),
        provider=result.provider,
        output_path=result.output_path,
        output_url=getattr(result, "output_url", None),
        error=result.error,
        skipped=bool(result.skipped),
        reason=getattr(result, "reason", None),
    )


class MediaRouter:
    """Public media API used by the rest of Aria."""

    def generate_image(self, prompt: str, **kwargs) -> ProviderResult:
        return _convert(generate_image(prompt, **kwargs))

    def generate_video(self, prompt: str, **kwargs) -> ProviderResult:
        return _convert(generate_video(prompt, **kwargs))

    def generate_tts(self, text: str, **kwargs) -> ProviderResult:
        return _convert(generate_tts(text, **kwargs))

    def generate_music(self, prompt: str, **kwargs) -> ProviderResult:
        return _convert(generate_music(prompt, **kwargs))

    def generate_audio(self, kind: str, **kwargs) -> ProviderResult:
        if kind == "tts":
            return self.generate_tts(**kwargs)
        if kind == "music":
            return self.generate_music(**kwargs)
        raise ValueError(f"Unsupported audio kind: {kind}")

    def provider_stats(self):
        return provider_stats()
