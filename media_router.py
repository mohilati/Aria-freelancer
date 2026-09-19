"""
Resilient MediaRouter for Aria Freelancer.

Design:
- Krea-first image/video generation.
- Provider errors are logged individually.
- Visual QA is bounded and does not kill a scene on Gemini rate limits.
- A rejected image gets a targeted correction prompt on the next attempt.
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
            ["krea_image", "pollinations_image", "huggingface_image", "fal_image", "replicate_image"],
        )
        self.video_chain = _chain(
            "ARIA_VIDEO_CHAIN",
            ["krea_video", "pollinations_video", "huggingface_video", "fal_video", "replicate_video"],
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
                print(f"[MEDIA] {kind} provider={name} unavailable: not registered")
                continue

            try:
                result = fn(**kwargs)
                if result:
                    print(f"[MEDIA] {kind} provider={name} succeeded")
                    return ProviderResult(True, name, output_path=result)

                errors.append(f"{name}: no output")
                print(f"[MEDIA] {kind} provider={name} returned no output")

            except Exception as exc:
                msg = f"{type(exc).__name__}: {exc}"
                errors.append(f"{name}: {msg}")
                print(f"[MEDIA] {kind} provider={name} failed: {msg}")

        return ProviderResult(
            False,
            "none",
            error=f"{kind} providers exhausted: " + " | ".join(errors),
            skipped=True,
        )

    @staticmethod
    def _scene_prompt(scene: Optional[Dict[str, Any]], continuity: Dict[str, Any], reference: str) -> str:
        if not scene:
            return ""
        return build_clinic_scene_prompt(scene, continuity, reference)

    def generate_image(self, prompt: str, **kwargs) -> ProviderResult:
        scene = kwargs.get("scene")
        continuity = kwargs.get("continuity") or {}
        reference = kwargs.get("real_reference_note") or ""

        base_prompt = self._scene_prompt(scene, continuity, reference) if scene else prompt
        current_prompt = base_prompt
        attempts = max(1, min(int(kwargs.get("qa_attempts", 2)), 2))
        last_error = None

        clean_kwargs = {
            k: v for k, v in kwargs.items()
            if k not in {"scene", "continuity", "real_reference_note", "qa_attempts"}
        }

        for attempt in range(1, attempts + 1):
            result = self._run(
                self.image_chain,
                IMAGE_PROVIDERS,
                "image",
                prompt=current_prompt,
                **clean_kwargs,
            )

            if not result.ok or not result.output_path:
                last_error = result.error
                continue

            if not scene or os.getenv("ARIA_VISUAL_QA", "1") != "1":
                return result

            qa = review_image(result.output_path, scene)
            score = int(qa.get("score", 0) or 0)
            approved = bool(qa.get("approved"))

            if approved and score >= int(os.getenv("ARIA_VISUAL_QA_MIN_SCORE", "70")):
                return result

            issues = [str(x) for x in qa.get("issues", []) if str(x).strip()]
            last_error = "visual QA rejected image: " + "; ".join(issues or ["quality threshold"])

            print(
                f"[MEDIA] image rejected by visual QA "
                f"attempt={attempt}: {last_error}"
            )

            # Targeted correction rather than regenerating the same prompt.
            if attempt < attempts:
                current_prompt = (
                    base_prompt
                    + "\n\nCORRECTION FOR NEXT GENERATION:\n"
                    + "\n".join(f"- {issue}" for issue in issues[:4])
                    + "\nKeep the requested camera framing and shot type exact. "
                      "Prefer simple natural poses and avoid unnecessary hands or extra people."
                )

        return ProviderResult(
            False,
            "none",
            error=last_error or "image generation failed",
            skipped=True,
        )

    def generate_video(self, prompt: str, **kwargs) -> ProviderResult:
        scene = kwargs.get("scene")
        continuity = kwargs.get("continuity") or {}
        reference = kwargs.get("real_reference_note") or ""

        if scene:
            prompt = self._scene_prompt(scene, continuity, reference)

        clean_kwargs = {
            k: v for k, v in kwargs.items()
            if k not in {"scene", "continuity", "real_reference_note"}
        }

        return self._run(
            self.video_chain,
            VIDEO_PROVIDERS,
            "video",
            prompt=prompt,
            **clean_kwargs,
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
                print(
                    f"[MEDIA] Persian Edge TTS failed: "
                    f"{type(exc).__name__}: {exc}"
                )

        clean_kwargs = {
            k: v for k, v in kwargs.items()
            if k not in {"job", "output_path", "language"}
        }
        return self._run(
            self.tts_chain,
            TTS_PROVIDERS,
            "tts",
            text=text,
            **clean_kwargs,
        )

    def generate_music(self, prompt: str, **kwargs) -> ProviderResult:
        return self._run(
            self.music_chain,
            MUSIC_PROVIDERS,
            "music",
            prompt=prompt,
            **kwargs,
        )

    def generate_audio(self, kind: str, **kwargs) -> ProviderResult:
        if kind == "tts":
            return self.generate_tts(**kwargs)
        if kind == "music":
            return self.generate_music(**kwargs)
        raise ValueError(f"Unsupported audio kind: {kind}")
