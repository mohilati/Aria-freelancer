import os
import time
from pathlib import Path
from typing import Optional

import requests
from huggingface_hub import InferenceClient


OUTPUT_DIR = Path(
    os.getenv("ARIA_OUTPUT_DIR", "outputs/media-test")
)
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


def _save_video(data: bytes, prefix: str) -> str:
    if not data:
        raise RuntimeError("Video provider returned empty data")

    filename = f"{prefix}-{int(time.time() * 1000)}.mp4"
    path = OUTPUT_DIR / filename

    path.write_bytes(data)

    if not path.exists() or path.stat().st_size == 0:
        raise RuntimeError("Video file was created but is empty")

    return str(path)


def huggingface_video(
    prompt: str,
    model: Optional[str] = None,
    **kwargs,
) -> str:
    """
    Generate a video using Hugging Face Inference Providers.

    text_to_video() returns raw video bytes.
    It does NOT return {"video": {...}}.
    """

    token = (
        os.getenv("HF_TOKEN")
        or os.getenv("HF_TOKEN_1")
        or os.getenv("HUGGINGFACEHUB_API_TOKEN")
    )

    if not token:
        raise RuntimeError("HF_TOKEN is not configured")

    model = model or os.getenv(
        "HF_VIDEO_MODEL",
        "Wan-AI/Wan2.1-T2V-1.3B",
    )

    client = InferenceClient(
        provider="hf-inference",
        api_key=token,
    )

    params = {}

    for key in (
        "guidance_scale",
        "num_frames",
        "num_inference_steps",
        "seed",
    ):
        value = kwargs.get(key)
        if value is not None:
            params[key] = value

    negative_prompt = kwargs.get("negative_prompt")
    if negative_prompt:
        params["negative_prompt"] = negative_prompt

    video_bytes = client.text_to_video(
        prompt,
        model=model,
        **params,
    )

    if not isinstance(video_bytes, bytes):
        raise RuntimeError(
            f"Unexpected Hugging Face video response type: "
            f"{type(video_bytes).__name__}"
        )

    return _save_video(video_bytes, "hf-video")


def replicate_video(
    prompt: str,
    model: Optional[str] = None,
    **kwargs,
) -> Optional[str]:
    """
    Replicate fallback.
    """

    token = os.getenv("REPLICATE_API_TOKEN")
    model = model or os.getenv("REPLICATE_VIDEO_MODEL")

    if not token or not model:
        return None

    response = requests.post(
        "https://api.replicate.com/v1/predictions",
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
        },
        json={
            "version": model,
            "input": {
                "prompt": prompt,
            },
        },
        timeout=60,
    )

    response.raise_for_status()
    prediction = response.json()

    for _ in range(60):
        status_url = prediction.get("urls", {}).get("get")

        if not status_url:
            return None

        status_response = requests.get(
            status_url,
            headers={
                "Authorization": f"Bearer {token}",
            },
            timeout=30,
        )

        status_response.raise_for_status()
        data = status_response.json()

        status = data.get("status")

        if status == "succeeded":
            output = data.get("output")

            if isinstance(output, list):
                output = output[0] if output else None

            if not output:
                return None

            video_response = requests.get(
                output,
                timeout=180,
            )
            video_response.raise_for_status()

            return _save_video(
                video_response.content,
                "replicate-video",
            )

        if status in {"failed", "canceled"}:
            return None

        time.sleep(5)

    return None


def fal_video(
    prompt: str,
    model: Optional[str] = None,
    **kwargs,
) -> Optional[str]:
    """
    Direct fal.ai provider.
    """

    key = os.getenv("FAL_KEY")

    if not key:
        raise RuntimeError("FAL_KEY is not configured")

    import fal_client

    model = model or os.getenv(
        "FAL_VIDEO_MODEL",
        "fal-ai/wan/v2.7/text-to-video",
    )

    arguments = {
        "prompt": prompt,
    }

    aspect_ratio = kwargs.get("aspect_ratio")
    duration = kwargs.get("duration")

    if aspect_ratio:
        arguments["aspect_ratio"] = aspect_ratio

    if duration:
        arguments["duration"] = duration

    result = fal_client.subscribe(
        model,
        arguments=arguments,
    )

    if not isinstance(result, dict):
        raise RuntimeError(
            f"Unexpected FAL response type: "
            f"{type(result).__name__}"
        )

    video = result.get("video")

    if isinstance(video, dict):
        video_url = video.get("url")
    elif isinstance(video, str):
        video_url = video
    else:
        video_url = None

    if not video_url:
        raise RuntimeError(
            "FAL returned no video URL"
        )

    response = requests.get(
        video_url,
        timeout=180,
    )
    response.raise_for_status()

    return _save_video(
        response.content,
        "fal-video",
    )


VIDEO_PROVIDERS = {
    "fal_video": fal_video,
    "replicate_video": replicate_video,
    "huggingface_video": huggingface_video,
    }
