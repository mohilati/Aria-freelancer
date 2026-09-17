import os
import time
import uuid
from pathlib import Path
from typing import Any, Optional

import httpx

OUTPUT_DIR = Path(os.getenv("ARIA_OUTPUT_DIR", "outputs"))
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

HF_TOKEN = os.getenv("HF_TOKEN") or os.getenv("HF_TOKEN_1") or os.getenv("HUGGINGFACEHUB_API_TOKEN")
REPLICATE_TOKEN = os.getenv("REPLICATE_API_TOKEN")
FAL_KEY = os.getenv("FAL_KEY")

HF_VIDEO_MODEL = os.getenv("HF_VIDEO_MODEL", "Wan-AI/Wan2.1-T2V-1.3B")
REPLICATE_VIDEO_MODEL = os.getenv("REPLICATE_VIDEO_MODEL", "")
FAL_VIDEO_MODEL = os.getenv("FAL_VIDEO_MODEL", "fal-ai/wan/v2.7/text-to-video")


def _save(data: bytes, suffix=".mp4") -> str:
    path = OUTPUT_DIR / f"video-{uuid.uuid4().hex}{suffix}"
    path.write_bytes(data)
    return str(path)


def fal_video(prompt: str, **kwargs: Any) -> Optional[str]:
    if not FAL_KEY:
        return None

    import fal_client

    arguments = {
        "prompt": prompt,
    }
    if kwargs.get("aspect_ratio"):
        arguments["aspect_ratio"] = kwargs["aspect_ratio"]
    if kwargs.get("duration"):
        arguments["duration"] = kwargs["duration"]

    result = fal_client.subscribe(FAL_VIDEO_MODEL, arguments=arguments)
    video = result.get("video") or {}
    url = video.get("url")
    if not url:
        raise RuntimeError("fal returned no video output")

    with httpx.Client(timeout=180.0, follow_redirects=True) as client:
        media = client.get(url)
        media.raise_for_status()
        return _save(media.content)


def huggingface_video(prompt: str, **kwargs: Any) -> Optional[str]:
    if not HF_TOKEN:
        return None

    from huggingface_hub import InferenceClient

    client = InferenceClient(
        provider=os.getenv("HF_VIDEO_PROVIDER", "fal-ai"),
        api_key=HF_TOKEN,
    )
    result = client.text_to_video(prompt, model=HF_VIDEO_MODEL)
    data = result if isinstance(result, bytes) else bytes(result)
    return _save(data)


def _replicate_prediction(client: httpx.Client, model: str, payload: dict) -> dict:
    response = client.post(
        f"https://api.replicate.com/v1/models/{model}/predictions",
        headers={
            "Authorization": f"Bearer {REPLICATE_TOKEN}",
            "Content-Type": "application/json",
        },
        json=payload,
    )
    response.raise_for_status()
    prediction = response.json()

    for _ in range(180):
        status = prediction.get("status")
        if status == "succeeded":
            return prediction
        if status in {"failed", "canceled"}:
            raise RuntimeError(prediction.get("error") or f"Replicate status={status}")
        time.sleep(2)
        response = client.get(
            prediction["urls"]["get"],
            headers={"Authorization": f"Bearer {REPLICATE_TOKEN}"},
        )
        response.raise_for_status()
        prediction = response.json()

    raise TimeoutError("Replicate prediction timed out")


def replicate_video(prompt: str, **kwargs: Any) -> Optional[str]:
    if not REPLICATE_TOKEN or not REPLICATE_VIDEO_MODEL:
        return None

    with httpx.Client(timeout=60.0, follow_redirects=True) as client:
        prediction = _replicate_prediction(
            client,
            REPLICATE_VIDEO_MODEL,
            {"input": {"prompt": prompt}},
        )
        output = prediction.get("output")
        if not output:
            raise RuntimeError("Replicate returned no video output")
        output_url = output[0] if isinstance(output, list) else output
        media = client.get(output_url)
        media.raise_for_status()
        return _save(media.content)


VIDEO_PROVIDERS = {
    "fal_video": fal_video,
    "huggingface_video": huggingface_video,
    "replicate_video": replicate_video,
}
