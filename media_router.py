"""
media_router.py
----------------
Central dispatcher for Aria Freelancer's media generation.

Each media type (image, video, audio) has an ordered list of providers
(configurable via env vars). The router tries them in order and, if a
provider fails or is unavailable, falls through to the next one. If every
provider in the chain fails, that media type is SKIPPED (not a hard fail) so
one missing API key never kills the whole job.

Usage:
    from media_router import MediaRouter

    router = MediaRouter()
    result = router.generate_image(prompt="...")
    result = router.generate_video(prompt="...")
    result = router.generate_audio(text="...", kind="tts")   # or kind="music"
"""

import os
import logging

from image_provider import IMAGE_PROVIDERS
from video_provider import VIDEO_PROVIDERS
from audio_provider import TTS_PROVIDERS, MUSIC_PROVIDERS

logger = logging.getLogger("aria.media_router")
logging.basicConfig(level=logging.INFO, format="[%(name)s] %(message)s")


class ProviderResult:
    """Uniform result object returned by every provider call."""

    def __init__(self, ok, provider=None, output_path=None, error=None, skipped=False):
        self.ok = ok
        self.provider = provider
        self.output_path = output_path
        self.error = error
        self.skipped = skipped

    def __repr__(self):
        if self.skipped:
            return "<ProviderResult SKIPPED>"
        if self.ok:
            return f"<ProviderResult ok provider={self.provider} path={self.output_path}>"
        return f"<ProviderResult FAILED provider={self.provider} error={self.error}>"


def _env_chain(env_var, default_chain):
    """
    Reads a comma-separated provider order from an env var, e.g.
        IMAGE_PROVIDER=huggingface,local
    Falls back to default_chain if the env var isn't set.
    """
    raw = os.environ.get(env_var)
    if not raw:
        return list(default_chain)
    return [p.strip() for p in raw.split(",") if p.strip()]


class MediaRouter:
    def __init__(self):
        self.image_chain = _env_chain("IMAGE_PROVIDER", list(IMAGE_PROVIDERS.keys()))
        self.video_chain = _env_chain("VIDEO_PROVIDER", list(VIDEO_PROVIDERS.keys()))
        self.tts_chain = _env_chain("TTS_PROVIDER", list(TTS_PROVIDERS.keys()))
        self.music_chain = _env_chain("MUSIC_PROVIDER", list(MUSIC_PROVIDERS.keys()))

    def _run_chain(self, media_label, chain, registry, **kwargs):
        for name in chain:
            fn = registry.get(name)
            if fn is None:
                logger.warning(f"{media_label}: unknown provider '{name}', skipping entry")
                continue
            logger.info(f"{media_label}: trying provider '{name}'...")
            try:
                output_path = fn(**kwargs)
                if output_path:
                    logger.info(f"{media_label}: '{name}' succeeded -> {output_path}")
                    return ProviderResult(ok=True, provider=name, output_path=output_path)
                logger.warning(f"{media_label}: '{name}' returned no output, trying next")
            except Exception as exc:  # noqa: BLE001 - we want to fall through on any failure
                logger.warning(f"{media_label}: '{name}' failed ({exc}), trying next")

        logger.warning(f"{media_label}: all providers failed/unavailable — SKIPPING this media type")
        return ProviderResult(ok=False, skipped=True, error="all providers exhausted")

    def generate_image(self, prompt, **kwargs):
        return self._run_chain("IMAGE", self.image_chain, IMAGE_PROVIDERS, prompt=prompt, **kwargs)

    def generate_video(self, prompt, **kwargs):
        return self._run_chain("VIDEO", self.video_chain, VIDEO_PROVIDERS, prompt=prompt, **kwargs)

    def generate_tts(self, text, **kwargs):
        return self._run_chain("TTS", self.tts_chain, TTS_PROVIDERS, text=text, **kwargs)

    def generate_music(self, prompt, **kwargs):
        return self._run_chain("MUSIC", self.music_chain, MUSIC_PROVIDERS, prompt=prompt, **kwargs)

    def generate_audio(self, kind="tts", **kwargs):
        if kind == "tts":
            return self.generate_tts(**kwargs)
        if kind == "music":
            return self.generate_music(**kwargs)
        raise ValueError(f"Unknown audio kind: {kind}")
