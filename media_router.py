"""
Drop-in MediaRouter for Aria Freelancer.

Adds:
- Persian-first TTS through persian_tts.py.
- Clinic-specific visual prompt policy.
- Visual QA for generated images.
- Provider failover without accepting a failed visual silently.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

from image_provider import IMAGE_PROVIDERS
from video_provider import VIDEO_PROVIDERS
from audio_provider import TTS_PROVIDERS, MUSIC_PROVIDERS
from visual_prompt_policy import build_clinic_scene_prompt
from visual_qa import review_image
from persian_tts import synthesize_persian, voice_for_job

@dataclass
class ProviderResult:
    ok: bool
    provider: str
    output_path: Optional[str] = None
    error: Optional[str] = None
    skipped: bool = False
    reason: Optional[str] = None

def _chain(env_name: str, default: List[str]) -> List[str]:
    raw = os.getenv(env_name, "")
    return [x.strip() for x in raw.split(",") if x.strip()] or default

class MediaRouter:
    def __init__(self) -> None:
        self.image_chain = _chain(
            "ARIA_IMAGE_CHAIN",
            ["krea_image", "huggingface_image", "fal_image", "replicate_image"],
        )
        self.video_chain = _chain(
            "ARIA_VIDEO_CHAIN",
            ["krea_video", "huggingface_video", "fal_video", "replicate_video"],
        )
        self.tts_chain = _chain(
            "ARIA_TTS_CHAIN",
            ["persian_edge_tts", "elevenlabs_tts", "huggingface_tts"],
        )
        self.music_chain = _chain(
            "ARIA_MUSIC_CHAIN",
            ["suno_music", "krea_music", "pollinations_audio", "fal_music"],
        )

    def _run(self, names, registry, kind, **kwargs) -> ProviderResult:
        errors = []
        for name in names:
            fn = registry.get(name)
            if fn is None:
                errors.append(f"{name}: not registered")
                continue
            try:
                result = fn(**kwargs)
                if result:
                    return ProviderResult(True, name, output_path=result)
                errors.append(f"{name}: no output")
            except Exception as exc:
                errors.append(f"{name}: {type(exc).__name__}: {exc}")
        return ProviderResult(
            False,
            "none",
            error=f"{kind} providers exhausted: " + " | ".join(errors),
            skipped=True,
        )

    def generate_image(self, prompt: str, **kwargs) -> ProviderResult:
        scene = kwargs.get("scene")
        if scene:
            prompt = build_clinic_scene_prompt(
                scene,
                kwargs.get("continuity") or {},
                kwargs.get("real_reference_note") or "",
            )

        attempts = int(kwargs.get("qa_attempts", 3))
        last_error = None

        for attempt in range(attempts):
            result = self._run(
                self.image_chain,
                IMAGE_PROVIDERS,
                "image",
                prompt=prompt,
                **{k: v for k, v in kwargs.items() if k not in {"scene", "continuity", "real_reference_note", "qa_attempts"}},
            )
            if not result.ok or not result.output_path:
                last_error = result.error
                continue

            if not scene or os.getenv("ARIA_VISUAL_QA", "1") != "1":
                return result

            qa = review_image(result.output_path, scene)
            if bool(qa.get("approved")) and int(qa.get("score", 0)) >= int(os.getenv("ARIA_VISUAL_QA_MIN_SCORE", "72")):
                return result

            last_error = "visual QA rejected image: " + "; ".join(map(str, qa.get("issues", [])))
            print(f"[MEDIA] image rejected by visual QA attempt={attempt+1}: {last_error}")

        return ProviderResult(False, "none", error=last_error or "image generation failed", skipped=True)

    def generate_video(self, prompt: str, **kwargs) -> ProviderResult:
        scene = kwargs.get("scene")
        if scene:
            prompt = build_clinic_scene_prompt(
                scene,
                kwargs.get("continuity") or {},
                kwargs.get("real_reference_note") or "",
            )
        return self._run(
            self.video_chain,
            VIDEO_PROVIDERS,
            "video",
            prompt=prompt,
            **{k: v for k, v in kwargs.items() if k not in {"scene", "continuity", "real_reference_note"}},
        )

    def generate_tts(self, text: str, **kwargs) -> ProviderResult:
        language = str(kwargs.get("language", "Persian")).lower()
        if language in {"persian", "fa", "farsi"}:
            try:
                output = kwargs.get("output_path")
                if not output:
                    out_dir = kwargs.get("output_dir", "outputs/media/tts")
                    os.makedirs(out_dir, exist_ok=True)
                    output = os.path.join(out_dir, "persian-narration.mp3")
                output = synthesize_persian(
                    text,
                    output,
                    gender=voice_for_job(kwargs.get("job", {})),
                    rate=kwargs.get("rate", "-4%"),
                    pitch=kwargs.get("pitch", "+0Hz"),
                )
                return ProviderResult(True, "persian_edge_tts", output_path=output)
            except Exception as exc:
                print(f"[MEDIA] Persian Edge TTS failed: {type(exc).__name__}: {exc}")

        return self._run(self.tts_chain[1:], TTS_PROVIDERS, "tts", text=text, **kwargs)

    def generate_music(self, prompt: str, **kwargs) -> ProviderResult:
        return self._run(self.music_chain, MUSIC_PROVIDERS, "music", prompt=prompt, **kwargs)

    def generate_audio(self, kind: str, **kwargs) -> ProviderResult:
        if kind == "tts":
            return self.generate_tts(**kwargs)
        if kind == "music":
            return self.generate_music(**kwargs)
        raise ValueError(f"Unsupported audio kind: {kind}")
