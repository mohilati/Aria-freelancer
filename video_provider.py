import os
from pathlib import Path
from typing import Optional

import httpx

try:
    from huggingface_hub import InferenceClient
except ImportError:
    InferenceClient = None

try:
    import fal_client
except ImportError:
    fal_client = None

OUTPUT_DIR = Path(os.getenv("ARIA_OUTPUT_DIR", "outputs/media-test"))
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


def _hf_token() -> Optional[str]:
    return (
        os.getenv("HF_TOKEN")
        or os.getenv("HF_TOKEN_1")
        or os.getenv("HUGGINGFACEHUB_API_TOKEN")
    )


def _save(data: bytes, path: Path) -> str:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(data)
    return str(path)


def _download(url: str, path: Path) -> str:
    with httpx.Client(timeout=600, follow_redirects=True) as client:
        r = client.get(url)
        r.raise_for_status()
        return _save(r.content, path)


def huggingface_video(prompt: str, output_path: Optional[str] = None, **kwargs) -> Optional[str]:
    if InferenceClient is None:
        raise RuntimeError("huggingface_hub is not installed")

    token = _hf_token()
    if not token:
        raise RuntimeError("HF token is not configured")

    # This model is documented by HF as supported through Replicate.
    model = "Wan-AI/Wan2.2-TI2V-5B"
    output = Path(output_path or OUTPUT_DIR / "video-huggingface.mp4")

    client = InferenceClient(
        provider="replicate",
        api_key=token,
        timeout=600,
    )

    video = client.text_to_video(prompt, model=model)

    if isinstance(video, bytes):
        return _save(video, output)

    if isinstance(video, bytearray):
        return _save(bytes(video), output)

    raise RuntimeError(
        f"Unexpected HF video response: {type(video).__name__}"
    )


def fal_video(prompt: str, output_path: Optional[str] = None, **kwargs) -> Optional[str]:
    if fal_client is None:
        raise RuntimeError("fal-client is not installed")
    if not os.getenv("FAL_KEY"):
        raise RuntimeError("FAL_KEY is not configured")

    model = "fal-ai/wan/v2.7/text-to-video"
    output = Path(output_path or OUTPUT_DIR / "video-fal.mp4")

    result = fal_client.subscribe(
        model,
        arguments={"prompt": prompt},
        with_logs=False,
    )

    if isinstance(result, dict):
        video = result.get("video")
        if isinstance(video, dict) and video.get("url"):
            return _download(video["url"], output)
        if isinstance(video, str):
            return _download(video, output)

    raise RuntimeError("FAL Video response did not contain a video URL")


def replicate_video(prompt: str, output_path: Optional[str] = None, **kwargs) -> Optional[str]:
    token = os.getenv("REPLICATE_API_TOKEN")
    if not token:
        raise RuntimeError("REPLICATE_API_TOKEN is not configured")

    model = os.getenv("REPLICATE_VIDEO_MODEL")
    if not model:
        raise RuntimeError("REPLICATE_VIDEO_MODEL is not configured")

    output = Path(output_path or OUTPUT_DIR / "video-replicate.mp4")
    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}

    with httpx.Client(timeout=600, follow_redirects=True) as client:
        r = client.post(
            f"https://api.replicate.com/v1/models/{model}/predictions",
            headers=headers,
            json={"input": {"prompt": prompt}},
        )
        r.raise_for_status()
        data = r.json()
        poll_url = data.get("urls", {}).get("get")

        if not poll_url:
            raise RuntimeError("Replicate did not return prediction URL")

        import time
        for _ in range(120):
            status = client.get(poll_url, headers=headers)
            status.raise_for_status()
            data = status.json()

            if data.get("status") == "succeeded":
                result = data.get("output")
                if isinstance(result, str):
                    return _download(result, output)
                if isinstance(result, list):
                    for item in result:
                        if isinstance(item, str):
                            return _download(item, output)
                raise RuntimeError("Replicate returned no usable video")

            if data.get("status") in ("failed", "canceled"):
                raise RuntimeError(f"Replicate video failed: {data.get('error')}")

            time.sleep(5)

    raise RuntimeError("Replicate video timed out")


VIDEO_PROVIDERS = {
    "huggingface_video": huggingface_video,
    "fal_video": fal_video,
    "replicate_video": replicate_video,
}
