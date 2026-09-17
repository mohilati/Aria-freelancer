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

HF_IMAGE_MODEL = os.getenv("HF_IMAGE_MODEL", "black-forest-labs/FLUX.1-schnell")
REPLICATE_IMAGE_MODEL = os.getenv("REPLICATE_IMAGE_MODEL", "")
FAL_IMAGE_MODEL = os.getenv("FAL_IMAGE_MODEL", "fal-ai/flux/schnell")


def _save(data: bytes, suffix=".png") -> str:
    path = OUTPUT_DIR / f"image-{uuid.uuid4().hex}{suffix}"
    path.write_bytes(data)
    return str(path)


def fal_image(prompt: str, **kwargs: Any) -> Optional[str]:
    if not FAL_KEY:
        return None

    import fal_client

    result = fal_client.subscribe(
        FAL_IMAGE_MODEL,
        arguments={
            "prompt": prompt,
            "image_size": kwargs.get("image_size", "square_hd"),
            "num_images": 1,
        },
    )
    images = result.get("images") or []
    if not images:
        raise RuntimeError("fal returned no image output")

    url = images[0].get("url")
    if not url:
        raise RuntimeError("fal image result has no URL")

    with httpx.Client(timeout=120.0, follow_redirects=True) as client:
        media = client.get(url)
        media.raise_for_status()
        return _save(media.content)


def huggingface_image(prompt: str, **kwargs: Any) -> Optional[str]:
    if not HF_TOKEN:
        return None

    from huggingface_hub import InferenceClient

    client = InferenceClient(
        provider=os.getenv("HF_IMAGE_PROVIDER", "fal-ai"),
        api_key=HF_TOKEN,
    )
    image = client.text_to_image(prompt, model=HF_IMAGE_MODEL)
    path = OUTPUT_DIR / f"image-{uuid.uuid4().hex}.png"
    image.save(path)
    return str(path)


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

    for _ in range(120):
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


def replicate_image(prompt: str, **kwargs: Any) -> Optional[str]:
    if not REPLICATE_TOKEN or not REPLICATE_IMAGE_MODEL:
        return None

    with httpx.Client(timeout=60.0, follow_redirects=True) as client:
        prediction = _replicate_prediction(
            client,
            REPLICATE_IMAGE_MODEL,
            {"input": {"prompt": prompt}},
        )
        output = prediction.get("output")
        if not output:
            raise RuntimeError("Replicate returned no image output")
        output_url = output[0] if isinstance(output, list) else output
        media = client.get(output_url)
        media.raise_for_status()
        return _save(media.content)


IMAGE_PROVIDERS = {
    "fal_image": fal_image,
    "huggingface_image": huggingface_image,
    "replicate_image": replicate_image,
}
