import os
from pathlib import Path
from typing import Optional

import httpx

try:
    import fal_client
except ImportError:
    fal_client = None

try:
    from huggingface_hub import InferenceClient
except ImportError:
    InferenceClient = None

OUTPUT_DIR = Path(os.getenv("ARIA_OUTPUT_DIR", "outputs/media-test"))
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


def _hf_token() -> Optional[str]:
    return (
        os.getenv("HF_TOKEN")
        or os.getenv("HF_TOKEN_1")
        or os.getenv("HUGGINGFACEHUB_API_TOKEN")
    )


def _save_bytes(data: bytes, output_path: Path) -> str:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_bytes(data)
    return str(output_path)


def _download(url: str, output_path: Path) -> str:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with httpx.Client(timeout=300.0, follow_redirects=True) as client:
        response = client.get(url)
        response.raise_for_status()
        output_path.write_bytes(response.content)
    return str(output_path)


def fal_video(prompt: str, output_path: Optional[str] = None, **kwargs) -> Optional[str]:
    if fal_client is None:
        raise RuntimeError("fal-client is not installed")
    if not os.getenv("FAL_KEY"):
        raise RuntimeError("FAL_KEY is not configured")

    model = os.getenv("FAL_VIDEO_MODEL") or "fal-ai/wan/v2.7/text-to-video"
    output = Path(output_path or OUTPUT_DIR / "video-fal.mp4")

    result = fal_client.subscribe(
        model,
        arguments={"prompt": prompt},
        with_logs=False,
    )

    if not isinstance(result, dict):
        raise RuntimeError("FAL Video returned an invalid result")

    video = result.get("video")
    if isinstance(video, dict) and video.get("url"):
        return _download(video["url"], output)
    if isinstance(video, str):
        return _download(video, output)

    raise RuntimeError("FAL Video response did not contain a video URL")


def huggingface_video(prompt: str, output_path: Optional[str] = None, **kwargs) -> Optional[str]:
    if InferenceClient is None:
        raise RuntimeError("huggingface_hub is not installed")

    token = _hf_token()
    if not token:
        raise RuntimeError("HF token is not configured")

    provider = os.getenv("HF_VIDEO_PROVIDER", "replicate")
    model = os.getenv("HF_VIDEO_MODEL", "Wan-AI/Wan2.2-TI2V-5B")
    output = Path(output_path or OUTPUT_DIR / "video-huggingface.mp4")

    client = InferenceClient(
        provider=provider,
        api_key=token,
        timeout=600,
    )

    video = client.text_to_video(
        prompt,
        model=model,
    )

    if isinstance(video, bytes):
        return _save_bytes(video, output)
    if isinstance(video, bytearray):
        return _save_bytes(bytes(video), output)

    raise RuntimeError(
        f"Unsupported Hugging Face video response: {type(video).__name__}"
    )


def replicate_video(prompt: str, output_path: Optional[str] = None, **kwargs) -> Optional[str]:
    token = os.getenv("REPLICATE_API_TOKEN")
    if not token:
        raise RuntimeError("REPLICATE_API_TOKEN is not configured")

    model = os.getenv("REPLICATE_VIDEO_MODEL")
    if not model:
        raise RuntimeError("REPLICATE_VIDEO_MODEL is not configured")

    output = Path(output_path or OUTPUT_DIR / "video-replicate.mp4")
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
    }

    with httpx.Client(timeout=300.0, follow_redirects=True) as client:
        response = client.post(
            f"https://api.replicate.com/v1/models/{model}/predictions",
            headers=headers,
            json={"input": {"prompt": prompt}},
        )
        response.raise_for_status()
        prediction = response.json()
        prediction_url = prediction.get("urls", {}).get("get")

        if not prediction_url:
            raise RuntimeError("Replicate did not return prediction URL")

        import time

        for _ in range(60):
            data = client.get(
                prediction_url,
                headers=headers,
            ).json()

            status = data.get("status")

            if status == "succeeded":
                result = data.get("output")
                if isinstance(result, str):
                    return _download(result, output)
                if isinstance(result, list):
                    for item in result:
                        if isinstance(item, str):
                            return _download(item, output)
                raise RuntimeError("Replicate returned no usable video output")

            if status in ("failed", "canceled"):
                raise RuntimeError(
                    f"Replicate video failed: {data.get('error')}"
                )

            time.sleep(5)

    raise RuntimeError("Replicate video timed out")


VIDEO_PROVIDERS = {
    "huggingface_video": huggingface_video,
    "fal_video": fal_video,
    "replicate_video": replicate_video,
}
