"""
Aria Provider Pool
------------------
Quota-aware round-robin media provider pool.

It distributes legitimate workload across configured providers while
respecting local daily caps and provider-side errors. It is not intended
to bypass provider terms or quotas.

Supported integrations:
- Pollinations: image + audio
- Krea: image + video
- KIE: configurable image/video/audio endpoints
- Pixazo: configurable image/video endpoints
- Suno API: music
- JSON2Video: final video composition/render
- Existing Aria HF/FAL/Replicate/ElevenLabs registries

Required secrets (use GitHub Actions Secrets, never hardcode):
POLLINATIONS_API_KEY
KREA_API_KEY
KIEAI_API_KEY (or KIE_API_KEY)
PIXAZO_API_KEY
SUNO_API_KEY
JSON2VIDEO_API_KEY
HF_TOKEN
FAL_KEY
REPLICATE_API_TOKEN

Optional local daily caps:
ARIA_DAILY_CAP_POLLINATIONS_IMAGE=20
ARIA_DAILY_CAP_KREA_IMAGE=20
ARIA_DAILY_CAP_KIE_IMAGE=20
ARIA_DAILY_CAP_PIXAZO_IMAGE=20
...
Unset = no local cap. The provider's own quota still applies.

Optional chains:
ARIA_IMAGE_CHAIN=pollinations_image,krea_image,kie_image,pixazo_image,huggingface_image,fal_image,replicate_image
ARIA_VIDEO_CHAIN=krea_video,kie_video,pixazo_video,huggingface_video,fal_video,replicate_video
ARIA_TTS_CHAIN=elevenlabs_tts,pollinations_tts,huggingface_tts
ARIA_MUSIC_CHAIN=suno_music,kie_music,pollinations_audio,huggingface_musicgen,fal_music
ARIA_COMPOSITION_CHAIN=json2video_render

State file:
ARIA_PROVIDER_STATE=outputs/.aria_provider_usage.json
"""

from __future__ import annotations

import hashlib
import json
import os
import time
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional
from urllib.parse import quote

import httpx

OUTPUT_DIR = Path(os.getenv("ARIA_OUTPUT_DIR", "outputs"))
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
STATE_PATH = Path(os.getenv("ARIA_PROVIDER_STATE", str(OUTPUT_DIR / ".aria_provider_usage.json")))
HTTP_TIMEOUT = float(os.getenv("ARIA_PROVIDER_HTTP_TIMEOUT", "120"))
POLL_INTERVAL = float(os.getenv("ARIA_PROVIDER_POLL_INTERVAL", "3"))
MAX_POLL_SECONDS = int(os.getenv("ARIA_PROVIDER_MAX_POLL_SECONDS", "900"))


def env(*names: str) -> Optional[str]:
    for name in names:
        value = os.getenv(name)
        if value:
            return value.strip()
    return None


def today() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d")


def chain(name: str, default: List[str]) -> List[str]:
    raw = os.getenv(name, "")
    values = [x.strip() for x in raw.split(",") if x.strip()]
    return values or list(default)


def daily_cap(provider: str) -> Optional[int]:
    raw = os.getenv("ARIA_DAILY_CAP_" + provider.upper())
    if raw in (None, ""):
        return None
    value = int(raw)
    if value < 0:
        raise ValueError("Daily cap cannot be negative")
    return value


@dataclass
class ProviderResult:
    ok: bool
    provider: str
    output_path: Optional[str] = None
    output_url: Optional[str] = None
    error: Optional[str] = None
    skipped: bool = False
    reason: Optional[str] = None


class UsageState:
    def __init__(self, path: Path):
        self.path = path
        self.data = {"date": today(), "usage": {}, "cooldowns": {}, "cursor": {}}
        self.load()

    def load(self) -> None:
        try:
            if self.path.exists():
                loaded = json.loads(self.path.read_text(encoding="utf-8"))
                if isinstance(loaded, dict):
                    self.data.update(loaded)
        except Exception:
            pass

        if self.data.get("date") != today():
            self.data = {"date": today(), "usage": {}, "cooldowns": {}, "cursor": {}}

    def save(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        tmp = self.path.with_suffix(".tmp")
        tmp.write_text(json.dumps(self.data, ensure_ascii=False, indent=2), encoding="utf-8")
        tmp.replace(self.path)

    def used(self, provider: str) -> int:
        return int(self.data["usage"].get(provider, 0))

    def available(self, provider: str) -> bool:
        cap = daily_cap(provider)
        if cap is not None and self.used(provider) >= cap:
            return False
        return time.time() >= float(self.data["cooldowns"].get(provider, 0))

    def consume(self, provider: str) -> None:
        self.data["usage"][provider] = self.used(provider) + 1

    def cooldown(self, provider: str, seconds: int) -> None:
        self.data["cooldowns"][provider] = time.time() + seconds

    def next_start(self, kind: str, length: int) -> int:
        start = int(self.data["cursor"].get(kind, 0)) % max(length, 1)
        self.data["cursor"][kind] = (start + 1) % max(length, 1)
        return start


def save_bytes(data: bytes, suffix: str, prefix: str) -> str:
    digest = hashlib.sha256(data).hexdigest()[:10]
    path = OUTPUT_DIR / f"{prefix}-{uuid.uuid4().hex[:10]}-{digest}{suffix}"
    path.write_bytes(data)
    return str(path)


def download(url: str, suffix: str, prefix: str, headers: Optional[Dict[str, str]] = None) -> str:
    with httpx.Client(timeout=max(HTTP_TIMEOUT, 180), follow_redirects=True) as client:
        response = client.get(url, headers=headers or {})
        response.raise_for_status()
        return save_bytes(response.content, suffix, prefix)


def bearer(token: str) -> Dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def extract_url(value: Any) -> Optional[str]:
    if isinstance(value, str) and value.startswith(("http://", "https://")):
        return value
    if isinstance(value, list):
        for item in value:
            found = extract_url(item)
            if found:
                return found
    if isinstance(value, dict):
        for key in (
            "url", "video_url", "audio_url", "image_url", "media_url",
            "download_url", "source_audio_url", "source_image_url",
            "urls", "output", "images", "videos", "audio", "result", "response",
        ):
            if key in value:
                found = extract_url(value[key])
                if found:
                    return found
    return None


def poll(client: httpx.Client, url: str, headers: Dict[str, str]) -> Dict[str, Any]:
    deadline = time.time() + MAX_POLL_SECONDS
    while time.time() < deadline:
        response = client.get(url, headers=headers)
        response.raise_for_status()
        data = response.json()
        status = str(
            data.get("status") or data.get("state") or data.get("successFlag") or ""
        ).lower()

        if status in {"completed", "succeeded", "success"}:
            return data
        if status in {"failed", "cancelled", "canceled", "error", "create_task_failed"}:
            raise RuntimeError(
                str(data.get("error") or data.get("message") or data.get("errorMessage") or data)
            )
        if extract_url(data):
            return data
        time.sleep(POLL_INTERVAL)

    raise TimeoutError("Provider job timed out")


# ------------------------- New providers -------------------------

def pollinations_image(prompt: str, **kwargs: Any) -> str:
    token = env("POLLINATIONS_API_KEY")
    if not token:
        raise RuntimeError("POLLINATIONS_API_KEY is not configured")

    model = kwargs.get("model") or os.getenv("POLLINATIONS_IMAGE_MODEL", "flux")
    url = f"https://gen.pollinations.ai/image/{quote(prompt, safe='')}?model={quote(str(model), safe='')}"

    with httpx.Client(timeout=max(HTTP_TIMEOUT, 180), follow_redirects=True) as client:
        response = client.get(url, headers=bearer(token))
        response.raise_for_status()
        ctype = response.headers.get("content-type", "")
        suffix = ".png" if "png" in ctype else ".svg" if "svg" in ctype else ".jpg"
        return save_bytes(response.content, suffix, "pollinations-image")


def pollinations_tts(text: str, **kwargs: Any) -> str:
    token = env("POLLINATIONS_API_KEY")
    if not token:
        raise RuntimeError("POLLINATIONS_API_KEY is not configured")

    voice = kwargs.get("voice") or os.getenv("POLLINATIONS_VOICE", "nova")
    url = f"https://gen.pollinations.ai/audio/{quote(text, safe='')}?voice={quote(str(voice), safe='')}"
    return download(url, ".mp3", "pollinations-audio", bearer(token))


def krea_image(prompt: str, **kwargs: Any) -> str:
    token = env("KREA_API_KEY", "KREA_API_KEY_1", "KREA_API_TOKEN")
    if not token:
        raise RuntimeError("KREA_API_KEY is not configured")

    endpoint = os.getenv(
        "KREA_IMAGE_ENDPOINT",
        "https://api.krea.ai/generate/image/krea/krea-2/medium",
    )
    payload = {
        "prompt": prompt,
        "aspect_ratio": kwargs.get("aspect_ratio", "16:9"),
        "resolution": kwargs.get("resolution", "1K"),
    }

    with httpx.Client(timeout=max(HTTP_TIMEOUT, 180), follow_redirects=True) as client:
        response = client.post(
            endpoint,
            headers={**bearer(token), "Content-Type": "application/json"},
            json=payload,
        )
        response.raise_for_status()
        data = response.json()
        job_id = data.get("job_id")

        if job_id:
            data = poll(client, f"https://api.krea.ai/jobs/{job_id}", bearer(token))

        url = extract_url(data)
        if not url:
            raise RuntimeError(f"Krea image returned no URL: {data}")
        return download(url, ".png", "krea-image")


def krea_video(prompt: str, **kwargs: Any) -> str:
    token = env("KREA_API_KEY", "KREA_API_KEY_1", "KREA_API_TOKEN")
    if not token:
        raise RuntimeError("KREA_API_KEY is not configured")

    endpoint = os.getenv(
        "KREA_VIDEO_ENDPOINT",
        "https://api.krea.ai/generate/video/kling/kling-3.0",
    )
    payload = {
        "prompt": prompt,
        "duration": kwargs.get("duration", 5),
        "mode": kwargs.get("mode", "std"),
        "aspect_ratio": kwargs.get("aspect_ratio", "16:9"),
    }

    with httpx.Client(timeout=max(HTTP_TIMEOUT, 180), follow_redirects=True) as client:
        response = client.post(
            endpoint,
            headers={**bearer(token), "Content-Type": "application/json"},
            json=payload,
        )
        response.raise_for_status()
        data = response.json()
        job_id = data.get("job_id")
        if job_id:
            data = poll(client, f"https://api.krea.ai/jobs/{job_id}", bearer(token))

        url = extract_url(data)
        if not url:
            raise RuntimeError(f"Krea video returned no URL: {data}")
        return download(url, ".mp4", "krea-video")


def _generic_task_provider(
    key_names: List[str],
    endpoint_env: str,
    status_env: str,
    prompt: str,
    suffix: str,
    prefix: str,
    header_name: str = "Authorization",
    **kwargs: Any,
) -> str:
    token = env(*key_names)
    if not token:
        raise RuntimeError(f"{key_names[0]} is not configured")

    endpoint = os.getenv(endpoint_env)
    if not endpoint:
        raise RuntimeError(f"{endpoint_env} is not configured")

    payload = dict(kwargs.get("payload") or {})
    payload.setdefault("prompt", prompt)

    headers = {"Content-Type": "application/json"}
    headers[header_name] = f"Bearer {token}" if header_name == "Authorization" else token

    with httpx.Client(timeout=max(HTTP_TIMEOUT, 180), follow_redirects=True) as client:
        response = client.post(endpoint, headers=headers, json=payload)
        response.raise_for_status()
        data = response.json()

        task_id = (
            data.get("taskId") or data.get("task_id")
            or (data.get("data") or {}).get("taskId")
            or (data.get("data") or {}).get("task_id")
            or data.get("request_id")
        )

        if task_id:
            status_url = os.getenv(status_env)
            if not status_url:
                raise RuntimeError(f"{status_env} is required when the provider is asynchronous")
            status_url = status_url.replace("{task_id}", str(task_id)).replace(
                "{request_id}", str(task_id)
            )
            data = poll(client, status_url, headers)

        url = extract_url(data)
        if not url:
            raise RuntimeError(f"Provider returned no downloadable URL: {data}")
        return download(url, suffix, prefix)


def kie_image(prompt: str, **kwargs: Any) -> str:
    return _generic_task_provider(
        ["KIEAI_API_KEY", "KIE_API_KEY"],
        "KIE_IMAGE_ENDPOINT",
        "KIE_IMAGE_STATUS_ENDPOINT",
        prompt, ".png", "kie-image", **kwargs
    )


def kie_video(prompt: str, **kwargs: Any) -> str:
    return _generic_task_provider(
        ["KIEAI_API_KEY", "KIE_API_KEY"],
        "KIE_VIDEO_ENDPOINT",
        "KIE_VIDEO_STATUS_ENDPOINT",
        prompt, ".mp4", "kie-video", **kwargs
    )


def kie_music(prompt: str, **kwargs: Any) -> str:
    return _generic_task_provider(
        ["KIEAI_API_KEY", "KIE_API_KEY"],
        "KIE_AUDIO_ENDPOINT",
        "KIE_AUDIO_STATUS_ENDPOINT",
        prompt, ".mp3", "kie-audio", **kwargs
    )


def pixazo_image(prompt: str, **kwargs: Any) -> str:
    return _generic_task_provider(
        ["PIXAZO_API_KEY", "PIXAZO_API_KEY_1"],
        "PIXAZO_IMAGE_ENDPOINT",
        "PIXAZO_IMAGE_STATUS_ENDPOINT",
        prompt, ".png", "pixazo-image",
        header_name="Ocp-Apim-Subscription-Key",
        **kwargs
    )


def pixazo_video(prompt: str, **kwargs: Any) -> str:
    return _generic_task_provider(
        ["PIXAZO_API_KEY", "PIXAZO_API_KEY_1"],
        "PIXAZO_VIDEO_ENDPOINT",
        "PIXAZO_VIDEO_STATUS_ENDPOINT",
        prompt, ".mp4", "pixazo-video",
        header_name="Ocp-Apim-Subscription-Key",
        **kwargs
    )


def suno_music(prompt: str, **kwargs: Any) -> str:
    token = env("SUNO_API_KEY", "SUNO_API_KEY_1", "SUNO_API_TOKEN")
    if not token:
        raise RuntimeError("SUNO_API_KEY is not configured")

    base = os.getenv("SUNO_API_BASE_URL", "https://api.sunoapi.org").rstrip("/")
    endpoint = os.getenv("SUNO_GENERATE_ENDPOINT", f"{base}/api/v1/generate")
    status_endpoint = os.getenv(
        "SUNO_STATUS_ENDPOINT",
        f"{base}/api/v1/generate/record-info",
    )

    payload = {
        "prompt": kwargs.get("lyrics", prompt),
        "customMode": kwargs.get("custom_mode", True),
        "instrumental": kwargs.get("instrumental", False),
        "model": kwargs.get("model", "V4_5PLUS"),
        "style": kwargs.get("style", "cinematic electronic"),
        "title": kwargs.get("title", "Aria Generated Track"),
    }

    with httpx.Client(timeout=max(HTTP_TIMEOUT, 180), follow_redirects=True) as client:
        response = client.post(
            endpoint,
            headers={**bearer(token), "Content-Type": "application/json"},
            json=payload,
        )
        response.raise_for_status()
        data = response.json()
        task_id = data.get("taskId") or (data.get("data") or {}).get("taskId")
        if not task_id:
            url = extract_url(data)
            if url:
                return download(url, ".mp3", "suno-music")
            raise RuntimeError(f"Suno returned no taskId: {data}")

        status_url = status_endpoint + (
            "&" if "?" in status_endpoint else "?"
        ) + "taskId=" + quote(str(task_id), safe="")

        result = poll(client, status_url, bearer(token))
        url = extract_url(result)
        if not url:
            raise RuntimeError(f"Suno completed without audio URL: {result}")
        return download(url, ".mp3", "suno-music")


def json2video_render(movie_json: Dict[str, Any]) -> str:
    token = env("JSON2VIDEO_API_KEY", "JSON2VIDEO_API_KEY_1")
    if not token:
        raise RuntimeError("JSON2VIDEO_API_KEY is not configured")

    base = os.getenv(
        "JSON2VIDEO_BASE_URL",
        "https://api.json2video.com/v2",
    ).rstrip("/")

    with httpx.Client(timeout=max(HTTP_TIMEOUT, 180), follow_redirects=True) as client:
        response = client.post(
            f"{base}/movies",
            headers={
                "x-api-key": token,
                "Content-Type": "application/json",
            },
            json=movie_json,
        )
        response.raise_for_status()
        data = response.json()
        project = data.get("project") or data.get("projectId") or data.get("id")
        if not project:
            url = extract_url(data)
            if url:
                return download(url, ".mp4", "json2video")
            raise RuntimeError(f"JSON2Video returned no project: {data}")

        deadline = time.time() + MAX_POLL_SECONDS
        while time.time() < deadline:
            status = client.get(
                f"{base}/movies",
                params={"project": project},
                headers={"x-api-key": token},
            )
            status.raise_for_status()
            result = status.json()
            url = extract_url(result)
            state = str(result.get("status") or result.get("state") or "").lower()
            if url:
                return download(url, ".mp4", "json2video")
            if state in {"failed", "error", "cancelled", "canceled"}:
                raise RuntimeError(f"JSON2Video failed: {result}")
            time.sleep(POLL_INTERVAL)

    raise TimeoutError("JSON2Video render timed out")


# ------------------------- Pool -------------------------

DEFAULT_CHAINS = {
    "image": [
        "pollinations_image", "krea_image", "kie_image", "pixazo_image",
        "huggingface_image", "fal_image", "replicate_image",
    ],
    "video": [
        "krea_video", "kie_video", "pixazo_video",
        "huggingface_video", "fal_video", "replicate_video",
    ],
    "tts": ["elevenlabs_tts", "pollinations_tts", "huggingface_tts"],
    "music": [
        "suno_music", "kie_music", "pollinations_audio",
        "huggingface_musicgen", "fal_music",
    ],
    "composition": ["json2video_render"],
}


class ProviderPool:
    def __init__(self) -> None:
        self.state = UsageState(STATE_PATH)

        self.registries: Dict[str, Dict[str, Optional[Callable[..., Any]]]] = {
            "image": {
                "pollinations_image": pollinations_image,
                "krea_image": krea_image,
                "kie_image": kie_image,
                "pixazo_image": pixazo_image,
            },
            "video": {
                "krea_video": krea_video,
                "kie_video": kie_video,
                "pixazo_video": pixazo_video,
            },
            "tts": {"pollinations_tts": pollinations_tts},
            "music": {
                "suno_music": suno_music,
                "kie_music": kie_music,
                "pollinations_audio": pollinations_tts,
            },
            "composition": {"json2video_render": json2video_render},
        }

        # Reuse Aria's already-tested provider modules.
        try:
            from image_provider import IMAGE_PROVIDERS
            self.registries["image"].update(IMAGE_PROVIDERS)
        except Exception:
            pass

        try:
            from video_provider import VIDEO_PROVIDERS
            self.registries["video"].update(VIDEO_PROVIDERS)
        except Exception:
            pass

        try:
            from audio_provider import TTS_PROVIDERS, MUSIC_PROVIDERS
            self.registries["tts"].update(TTS_PROVIDERS)
            self.registries["music"].update(MUSIC_PROVIDERS)
        except Exception:
            pass

    def _chain(self, kind: str) -> List[str]:
        env_name = {
            "image": "ARIA_IMAGE_CHAIN",
            "video": "ARIA_VIDEO_CHAIN",
            "tts": "ARIA_TTS_CHAIN",
            "music": "ARIA_MUSIC_CHAIN",
            "composition": "ARIA_COMPOSITION_CHAIN",
        }[kind]
        return chain(env_name, DEFAULT_CHAINS[kind])

    def _ordered(self, kind: str) -> List[str]:
        providers = self._chain(kind)
        if not providers:
            return []
        cursor = int(self.state.data["cursor"].get(kind, 0)) % len(providers)
        return providers[cursor:] + providers[:cursor]

    def _advance_cursor(self, kind: str, provider: str) -> None:
        providers = self._chain(kind)
        if not providers:
            return
        try:
            index = providers.index(provider)
        except ValueError:
            index = 0
        self.state.data["cursor"][kind] = (index + 1) % len(providers)

    def generate(self, kind: str, prompt: str = "", **kwargs: Any) -> ProviderResult:
        if kind == "composition":
            movie_json = kwargs.get("movie_json")
            if not isinstance(movie_json, dict):
                raise ValueError("composition requires movie_json=dict")
            return self.render_video(movie_json)

        if kind not in self.registries:
            raise ValueError(f"Unsupported kind: {kind}")

        errors: List[str] = []

        for provider in self._ordered(kind):
            fn = self.registries[kind].get(provider)

            if fn is None:
                errors.append(f"{provider}: not registered")
                continue

            if not self.state.available(provider):
                cap = daily_cap(provider)
                if cap is not None and self.state.used(provider) >= cap:
                    errors.append(f"{provider}: local daily cap reached")
                else:
                    errors.append(f"{provider}: cooldown active")
                continue

            try:
                if kind == "tts":
                    result = fn(text=prompt, **kwargs)
                elif kind == "composition":
                    result = fn(**kwargs)
                else:
                    result = fn(prompt=prompt, **kwargs)

                if result:
                    self.state.consume(provider)
                    self._advance_cursor(kind, provider)
                    self.state.save()
                    return ProviderResult(ok=True, provider=provider, output_path=str(result))

                errors.append(f"{provider}: no output")

            except Exception as exc:
                message = f"{type(exc).__name__}: {exc}"
                errors.append(f"{provider}: {message}")

                lowered = message.lower()
                if any(x in lowered for x in (
                    "429", "rate limit", "rate-limit", "quota",
                    "insufficient credit", "insufficient credits", "402",
                    "too many requests",
                )):
                    self.state.cooldown(provider, 6 * 60 * 60)
                elif any(x in lowered for x in (
                    "401", "403", "unauthorized", "forbidden",
                )):
                    self.state.cooldown(provider, 24 * 60 * 60)
                else:
                    self.state.cooldown(provider, 5 * 60)

                self.state.save()

        return ProviderResult(
            ok=False,
            provider="none",
            error=f"{kind} providers exhausted: " + " | ".join(errors),
            skipped=True,
            reason="all configured providers were unavailable, capped, or failed",
        )

    def render_video(self, movie_json: Dict[str, Any]) -> ProviderResult:
        return self.generate("composition", movie_json=movie_json)

    def stats(self) -> Dict[str, Any]:
        providers = set()
        for values in DEFAULT_CHAINS.values():
            providers.update(values)

        return {
            "date": self.state.data.get("date"),
            "providers": {
                name: {
                    "used_today": self.state.used(name),
                    "local_cap": daily_cap(name),
                    "remaining_local": (
                        None
                        if daily_cap(name) is None
                        else max(daily_cap(name) - self.state.used(name), 0)
                    ),
                    "available": self.state.available(name),
                }
                for name in sorted(providers)
            },
        }


_POOL: Optional[ProviderPool] = None


def get_provider_pool() -> ProviderPool:
    global _POOL
    if _POOL is None:
        _POOL = ProviderPool()
    return _POOL


def generate_image(prompt: str, **kwargs: Any) -> ProviderResult:
    return get_provider_pool().generate("image", prompt, **kwargs)


def generate_video(prompt: str, **kwargs: Any) -> ProviderResult:
    return get_provider_pool().generate("video", prompt, **kwargs)


def generate_tts(text: str, **kwargs: Any) -> ProviderResult:
    return get_provider_pool().generate("tts", text, **kwargs)


def generate_music(prompt: str, **kwargs: Any) -> ProviderResult:
    return get_provider_pool().generate("music", prompt, **kwargs)


def render_video(movie_json: Dict[str, Any]) -> ProviderResult:
    return get_provider_pool().render_video(movie_json)


def provider_stats() -> Dict[str, Any]:
    return get_provider_pool().stats()
