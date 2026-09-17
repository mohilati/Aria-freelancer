from __future__ import annotations

import os
import time
import uuid
from pathlib import Path
from typing import Any, Optional

import httpx

OUTPUT_DIR = Path(os.getenv("ARIA_OUTPUT_DIR", "outputs"))
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


def _hf_token() -> Optional[str]:
    return (
        os.getenv("HF_TOKEN")
        or os.getenv("HF_TOKEN_1")
        or os.getenv("HUGGINGFACEHUB_API_TOKEN")
    )


def _save(data: bytes, suffix: str = ".png") -> str:
    path = OUTPUT_DIR / f"image-{uuid.uuid4().hex}{suffix}"
    path.write_bytes(data)
    return str(path)


def _download(url: str, suffix: str = ".png") -> str:
    with httpx.Client(timeout=300, follow_redirects=True) as client:
        response = client.get(url)
        response.raise_for_status()
        return _save(response.content, suffix)


def huggingface_image(prompt: str, **kwargs: Any) -> Optional[str]:
    token = _hf_token()
    if not token:
        raise RuntimeError("HF token is not configured")

    from huggingface_hub import InferenceClient

    model = kwargs.get("model") or os.getenv(
        "HF_IMAGE_MODEL",
        "black-forest-labs/FLUX.1-schnell",
    )
    provider = kwargs.get("provider") or os.getenv(
        "HF_IMAGE_PROVIDER",
        "fal-ai",
    )

    client = InferenceClient(
        provider=provider,
        api_key=token,
        timeout=300,
    )
    image = client.text_to_image(prompt, model=model)
    path = OUTPUT_DIR / f"image-hf-{uuid.uuid4().hex}.png"
    image.save(path)
    return str(path)


def fal_image(prompt: str, **kwargs: Any) -> Optional[str]:
    key = os.getenv("FAL_KEY")
    if not key:
        raise RuntimeError("FAL_KEY is not configured")

    import fal_client

    model = kwargs.get("model") or os.getenv(
        "FAL_IMAGE_MODEL",
        "fal-ai/flux/schnell",
    )

    result = fal_client.subscribe(
        model,
        arguments={
            "prompt": prompt,
            "image_size": kwargs.get("image_size", "square_hd"),
            "num_images": 1,
        },
        with_logs=False,
    )

    images = result.get("images") or []
    if not images:
        raise RuntimeError("FAL returned no image output")

    url = images[0].get("url")
    if not url:
        raise RuntimeError("FAL image result has no URL")

    return _download(url, ".png")


def replicate_image(prompt: str, **kwargs: Any) -> Optional[str]:
    token = os.getenv("REPLICATE_API_TOKEN")
    model = kwargs.get("model") or os.getenv("REPLICATE_IMAGE_MODEL")
    if not token:
        raise RuntimeError("REPLICATE_API_TOKEN is not configured")
    if not model:
        raise RuntimeError("REPLICATE_IMAGE_MODEL is not configured")

    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
    }

    with httpx.Client(timeout=120, follow_redirects=True) as client:
        response = client.post(
            f"https://api.replicate.com/v1/models/{model}/predictions",
            headers=headers,
            json={"input": {"prompt": prompt}},
        )
        response.raise_for_status()
        prediction = response.json()

        poll_url = prediction.get("urls", {}).get("get")
        if not poll_url:
            raise RuntimeError("Replicate did not return a polling URL")

        for _ in range(120):
            status = client.get(poll_url, headers=headers)
            status.raise_for_status()
            data = status.json()

            if data.get("status") == "succeeded":
                output = data.get("output")
                if isinstance(output, str):
                    return _download(output, ".png")
                if isinstance(output, list) and output:
                    return _download(str(output[0]), ".png")
                raise RuntimeError("Replicate returned no image output")

            if data.get("status") in {"failed", "canceled"}:
                raise RuntimeError(
                    f"Replicate image failed: {data.get('error')}"
                )

            time.sleep(3)

    raise TimeoutError("Replicate image timed out")


IMAGE_PROVIDERS = {
    "huggingface_image": huggingface_image,
    "fal_image": fal_image,
    "replicate_image": replicate_image,
}
