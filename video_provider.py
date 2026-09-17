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


def _download(url: str, path: Path) -> str:
    path.parent.mkdir(parents=True, exist_ok=True)

    with httpx.Client(timeout=300.0, follow_redirects=True) as client:
        response = client.get(url)
        response.raise_for_status()
        path.write_bytes(response.content)

    return str(path)


def huggingface_video(
    prompt: str,
    output_path: Optional[str] = None,
    **kwargs,
) -> Optional[str]:

    if InferenceClient is None:
        raise RuntimeError("huggingface_hub is not installed")

    token = _hf_token()

    if not token:
        raise RuntimeError("HF token is not configured")

    provider = os.getenv("HF_VIDEO_PROVIDER", "auto")

    model = (
        os.getenv("HF_VIDEO_MODEL")
        or "Wan-AI/Wan2.1-T2V-1.3B"
    )

    client = InferenceClient(
        provider=provider,
        api_key=token,
    )

    output = Path(
        output_path
        or OUTPUT_DIR / "video-huggingface.mp4"
    )

    output.parent.mkdir(parents=True, exist_ok=True)

    video = client.text_to_video(
        prompt,
        model=model,
    )

    if not video:
        raise RuntimeError(
            "Hugging Face returned no video"
        )

    if isinstance(video, bytes):
        output.write_bytes(video)
        return str(output)

    if hasattr(video, "read"):
        output.write_bytes(video.read())
        return str(output)

    raise RuntimeError(
        f"Unsupported HF video response: "
        f"{type(video).__name__}"
    )


def replicate_video(
    prompt: str,
    output_path: Optional[str] = None,
    **kwargs,
) -> Optional[str]:

    token = os.getenv("REPLICATE_API_TOKEN")

    if not token:
        raise RuntimeError(
            "REPLICATE_API_TOKEN is not configured"
        )

    model = os.getenv("REPLICATE_VIDEO_MODEL")

    if not model:
        raise RuntimeError(
            "REPLICATE_VIDEO_MODEL is not configured"
        )

    try:
        import replicate
    except ImportError:
        raise RuntimeError(
            "replicate package is not installed"
        )

    output = Path(
        output_path
        or OUTPUT_DIR / "video-replicate.mp4"
    )

    result = replicate.run(
        model,
        input={
            "prompt": prompt,
        },
    )

    if not result:
        raise RuntimeError(
            "Replicate returned no video"
        )

    if isinstance(result, str):
        return _download(result, output)

    if hasattr(result, "read"):
        output.write_bytes(result.read())
        return str(output)

    if isinstance(result, list) and result:
        first = result[0]

        if isinstance(first, str):
            return _download(first, output)

        if hasattr(first, "read"):
            output.write_bytes(first.read())
            return str(output)

    raise RuntimeError(
        f"Unsupported Replicate response: "
        f"{type(result).__name__}"
    )


def fal_video(
    prompt: str,
    output_path: Optional[str] = None,
    **kwargs,
) -> Optional[str]:

    if fal_client is None:
        raise RuntimeError("fal-client is not installed")

    if not os.getenv("FAL_KEY"):
        raise RuntimeError("FAL_KEY is not configured")

    model = (
        os.getenv("FAL_VIDEO_MODEL")
        or "fal-ai/wan/v2.7/text-to-video"
    )

    output = Path(
        output_path
        or OUTPUT_DIR / "video-fal.mp4"
    )

    arguments = {
        "prompt": prompt,
    }

    if kwargs.get("aspect_ratio"):
        arguments["aspect_ratio"] = kwargs["aspect_ratio"]

    if kwargs.get("duration"):
        arguments["duration"] = kwargs["duration"]

    result = fal_client.subscribe(
        model,
        arguments=arguments,
        with_logs=False,
    )

    if not result:
        raise RuntimeError(
            "FAL returned no result"
        )

    video = result.get("video")

    if isinstance(video, dict):
        url = video.get("url")

        if url:
            return _download(url, output)

    raise RuntimeError(
        "FAL response did not contain a video URL"
    )


VIDEO_PROVIDERS = {
    "huggingface_video": huggingface_video,
    "replicate_video": replicate_video,
    "fal_video": fal_video,
}
