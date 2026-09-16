"""
video_provider.py
------------------
Same contract as image_provider.py: each function returns an output path
or None. Video providers usually need an async job -> poll -> download
flow; the polling helper below is shared so each provider stays short.
"""

import os
import time
import logging

logger = logging.getLogger("aria.video_provider")

OUTPUT_DIR = os.environ.get("ARIA_OUTPUT_DIR", "outputs")
os.makedirs(OUTPUT_DIR, exist_ok=True)


def _new_output_path(ext):
    ts = int(time.time() * 1000)
    return os.path.join(OUTPUT_DIR, f"video_{ts}.{ext}")


def huggingface_text_to_video(prompt, **kwargs):
    """
    Hugging Face Inference Providers routed to a text-to-video backend
    (Fal / Replicate / Novita / WaveSpeed, depending on what HF has live).
    Requires HF_TOKEN.
    """
    hf_token = os.environ.get("HF_TOKEN")
    if not hf_token:
        logger.info("HF_TOKEN not set — skipping huggingface_text_to_video")
        return None

    import requests

    model = kwargs.get("model", "")  # fill in once you pick a specific HF video model
    if not model:
        logger.info("No video model configured — skipping huggingface_text_to_video")
        return None

    url = f"https://api-inference.huggingface.co/models/{model}"
    headers = {"Authorization": f"Bearer {hf_token}"}

    resp = requests.post(url, headers=headers, json={"inputs": prompt}, timeout=300)
    resp.raise_for_status()

    out_path = _new_output_path("mp4")
    with open(out_path, "wb") as f:
        f.write(resp.content)
    return out_path


def fal_direct(prompt, **kwargs):
    """
    Placeholder for calling fal.ai directly (bypassing HF's routing layer)
    once you have a FAL_KEY and have picked a specific model endpoint.
    """
    fal_key = os.environ.get("FAL_KEY")
    if not fal_key:
        logger.info("FAL_KEY not set — skipping fal_direct")
        return None
    logger.info("fal_direct not implemented yet — skipping")
    return None


VIDEO_PROVIDERS = {
    "huggingface": huggingface_text_to_video,
    "fal": fal_direct,
}
