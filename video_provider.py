from __future__ import annotations

import os
import time
from pathlib import Path
from typing import Optional

import httpx

OUTPUT_DIR = Path(os.getenv("ARIA_OUTPUT_DIR", "outputs"))
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


def _save(data: bytes, output_path: Optional[str]) -> str:
    path = Path(output_path or OUTPUT_DIR / f"video-{time.time_ns()}.mp4")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(data)
    return str(path)


def _download(url: str, output_path: Optional[str]) -> str:
    with httpx.Client(timeout=900, follow_redirects=True) as client:
        response = client.get(url)
        response.raise_for_status()
        return _save(response.content, output_path)


def krea_video(
    prompt: str,
    output_path: Optional[str] = None,
    **kwargs,
) -> Optional[str]:
    """Krea Kling 3.0 direct REST API."""
    key = os.getenv("KREA_API_KEY") or os.getenv("KREA_API_TOKEN")
    if not key:
        raise RuntimeError("KREA_API_KEY/KREA_API_TOKEN is not configured")

    model = kwargs.get("model") or os.getenv(
        "KREA_VIDEO_MODEL",
        "kling/kling-3.0",
    )
    endpoint = f"https://api.krea.ai/generate/video/{model}"

    payload = {
        "prompt": prompt,
        "aspect_ratio": kwargs.get("aspect_ratio", "9:16"),
        "duration": int(kwargs.get("duration", 5)),
    }

    with httpx.Client(timeout=180, follow_redirects=True) as client:
        response = client.post(
            endpoint,
            headers={
                "Authorization": f"Bearer {key}",
                "Content-Type": "application/json",
            },
            json=payload,
        )
        response.raise_for_status()
        job = response.json()

        job_id = job.get("job_id")
        if not job_id:
            raise RuntimeError(f"Krea video response has no job_id: {job}")

        for _ in range(180):
            status = client.get(
                f"https://api.krea.ai/jobs/{job_id}",
                headers={"Authorization": f"Bearer {key}"},
            )
            status.raise_for_status()
            data = status.json()

            if data.get("status") == "completed":
                urls = (data.get("result") or {}).get("urls") or []
                if urls:
                    return _download(str(urls[0]), output_path)
                raise RuntimeError("Krea video completed without result URL")

            if data.get("status") in {"failed", "canceled"}:
                raise RuntimeError(f"Krea video job {data.get('status')}")

            time.sleep(5)

    raise TimeoutError("Krea video generation timed out")


def huggingface_video(
    prompt: str,
    output_path: Optional[str] = None,
    **kwargs,
) -> Optional[str]:
    token = (
        os.getenv("HF_TOKEN")
        or os.getenv("HF_TOKEN_1")
        or os.getenv("HUGGINGFACEHUB_API_TOKEN")
    )
    if not token:
        raise RuntimeError("HF token is not configured")

    from huggingface_hub import InferenceClient

    model = kwargs.get("model") or os.getenv(
        "HF_VIDEO_MODEL",
        "Wan-AI/Wan2.2-TI2V-5B",
    )
    provider = kwargs.get("provider") or os.getenv(
        "HF_VIDEO_PROVIDER",
        "replicate",
    )

    client = InferenceClient(
        provider=provider,
        api_key=token,
        timeout=900,
    )
    video = client.text_to_video(prompt, model=model)

    if isinstance(video, bytes):
        return _save(video, output_path)
    if isinstance(video, bytearray):
        return _save(bytes(video), output_path)

    raise RuntimeError(f"Unexpected HF video response: {type(video).__name__}")


def fal_video(
    prompt: str,
    output_path: Optional[str] = None,
    **kwargs,
) -> Optional[str]:
    key = os.getenv("FAL_KEY")
    if not key:
        raise RuntimeError("FAL_KEY is not configured")

    import fal_client

    model = kwargs.get("model") or os.getenv(
        "FAL_VIDEO_MODEL",
        "fal-ai/wan/v2.7/text-to-video",
    )

    result = fal_client.subscribe(
        model,
        arguments={
            "prompt": prompt,
            "aspect_ratio": kwargs.get("aspect_ratio", "9:16"),
        },
        with_logs=False,
    )

    video = result.get("video") if isinstance(result, dict) else None
    if isinstance(video, dict) and video.get("url"):
        return _download(video["url"], output_path)
    if isinstance(video, str):
        return _download(video, output_path)

    raise RuntimeError("FAL video response did not contain a video URL")


def replicate_video(
    prompt: str,
    output_path: Optional[str] = None,
    **kwargs,
) -> Optional[str]:
    token = os.getenv("REPLICATE_API_TOKEN")
    model = kwargs.get("model") or os.getenv("REPLICATE_VIDEO_MODEL")
    if not token:
        raise RuntimeError("REPLICATE_API_TOKEN is not configured")
    if not model:
        raise RuntimeError("REPLICATE_VIDEO_MODEL is not configured")

    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
    }

    with httpx.Client(timeout=900, follow_redirects=True) as client:
        response = client.post(
            f"https://api.replicate.com/v1/models/{model}/predictions",
            headers=headers,
            json={"input": {"prompt": prompt}},
        )
        response.raise_for_status()
        data = response.json()
        poll_url = data.get("urls", {}).get("get")

        if not poll_url:
            raise RuntimeError("Replicate did not return prediction URL")

        for _ in range(180):
            status = client.get(poll_url, headers=headers)
            status.raise_for_status()
            data = status.json()

            if data.get("status") == "succeeded":
                output = data.get("output")
                if isinstance(output, str):
                    return _download(output, output_path)
                if isinstance(output, list):
                    for item in output:
                        if isinstance(item, str):
                            return _download(item, output_path)
                raise RuntimeError("Replicate returned no usable video")

            if data.get("status") in {"failed", "canceled"}:
                raise RuntimeError(f"Replicate video failed: {data.get('error')}")

            time.sleep(5)

    raise TimeoutError("Replicate video timed out")


VIDEO_PROVIDERS = {
    "krea_video": krea_video,
    "huggingface_video": huggingface_video,
    "fal_video": fal_video,
    "replicate_video": replicate_video,
}
