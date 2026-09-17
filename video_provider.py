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


def _save(data: bytes, output_path: Optional[str]) -> str:
    path = Path(
        output_path
        or OUTPUT_DIR / f"video-{time.time_ns()}.mp4"
    )
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(data)
    return str(path)


def _download(url: str, output_path: Optional[str]) -> str:
    with httpx.Client(timeout=900, follow_redirects=True) as client:
        response = client.get(url)
        response.raise_for_status()
        return _save(response.content, output_path)


def huggingface_video(
    prompt: str,
    output_path: Optional[str] = None,
    **kwargs,
) -> Optional[str]:
    token = _hf_token()
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

    raise RuntimeError(
        f"Unexpected HF video response: {type(video).__name__}"
    )


def fal_video(
    prompt: str,
    output_path: Optional[str] = None,
    **kwargs,
) -> Optional[str]:
    if not os.getenv("FAL_KEY"):
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
            "aspect_ratio": kwargs.get("aspect_ratio", "16:9"),
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
                raise RuntimeError(
                    f"Replicate video failed: {data.get('error')}"
                )

            time.sleep(5)

    raise TimeoutError("Replicate video timed out")


VIDEO_PROVIDERS = {
    "huggingface_video": huggingface_video,
    "fal_video": fal_video,
    "replicate_video": replicate_video,
}
