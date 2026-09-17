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
HF_VIDEO_MODEL = os.getenv("HF_VIDEO_MODEL", "Wan-AI/Wan2.1-T2V-1.3B")
REPLICATE_VIDEO_MODEL = os.getenv("REPLICATE_VIDEO_MODEL", "")


def _save(data: bytes) -> str:
    path = OUTPUT_DIR / f"video-{uuid.uuid4().hex}.mp4"
    path.write_bytes(data)
    return str(path)


def huggingface_video(prompt: str, **kwargs: Any) -> Optional[str]:
    if not HF_TOKEN:
        return None

    from huggingface_hub import InferenceClient

    client = InferenceClient(
        provider=os.getenv("HF_VIDEO_PROVIDER", "fal-ai"),
        api_key=HF_TOKEN,
    )
    video = client.text_to_video(prompt, model=HF_VIDEO_MODEL)
    if hasattr(video, "read"):
        data = video.read()
    elif isinstance(video, bytes):
        data = video
    else:
        data = bytes(video)
    return _save(data)


def replicate_video(prompt: str, **kwargs: Any) -> Optional[str]:
    if not REPLICATE_TOKEN or not REPLICATE_VIDEO_MODEL:
        return None

    headers = {
        "Authorization": f"Bearer {REPLICATE_TOKEN}",
        "Content-Type": "application/json",
    }

    with httpx.Client(timeout=60.0, follow_redirects=True) as client:
        response = client.post(
            f"https://api.replicate.com/v1/models/{REPLICATE_VIDEO_MODEL}/predictions",
            headers=headers,
            json={"input": {"prompt": prompt}},
        )
        response.raise_for_status()
        prediction = response.json()

        for _ in range(180):
            status = prediction.get("status")
            if status == "succeeded":
                break
            if status in {"failed", "canceled"}:
                raise RuntimeError(prediction.get("error") or f"Replicate status={status}")
            time.sleep(2)
            response = client.get(
                prediction["urls"]["get"],
                headers={"Authorization": f"Bearer {REPLICATE_TOKEN}"},
            )
            response.raise_for_status()
            prediction = response.json()
        else:
            raise TimeoutError("Replicate video prediction timed out")

        output = prediction.get("output")
        if not output:
            raise RuntimeError("Replicate returned no video output")
        output_url = output[0] if isinstance(output, list) else output
        media = client.get(output_url)
        media.raise_for_status()
        return _save(media.content)


VIDEO_PROVIDERS = {
    "huggingface_video": huggingface_video,
    "replicate_video": replicate_video,
}
