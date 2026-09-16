"""
image_provider.py
------------------
Each provider function takes a `prompt` (+ optional kwargs), writes an
output file into outputs/, and returns the output path — or returns
None/raises to let media_router fall through to the next provider.

Add a new provider by writing a function with this signature and
registering it in IMAGE_PROVIDERS at the bottom.
"""

import os
import time
import logging

logger = logging.getLogger("aria.image_provider")

OUTPUT_DIR = os.environ.get("ARIA_OUTPUT_DIR", "outputs")
os.makedirs(OUTPUT_DIR, exist_ok=True)


def _new_output_path(ext):
    ts = int(time.time() * 1000)
    return os.path.join(OUTPUT_DIR, f"image_{ts}.{ext}")


def huggingface_flux(prompt, **kwargs):
    """
    Hugging Face Inference Providers -> FLUX.1 Schnell.
    Requires HF_TOKEN in the environment.
    """
    hf_token = os.environ.get("HF_TOKEN")
    if not hf_token:
        logger.info("HF_TOKEN not set — skipping huggingface_flux")
        return None

    import requests

    model = kwargs.get("model", "black-forest-labs/FLUX.1-schnell")
    url = f"https://api-inference.huggingface.co/models/{model}"
    headers = {"Authorization": f"Bearer {hf_token}"}

    resp = requests.post(url, headers=headers, json={"inputs": prompt}, timeout=120)
    resp.raise_for_status()

    out_path = _new_output_path("png")
    with open(out_path, "wb") as f:
        f.write(resp.content)
    return out_path


def local_stable_diffusion(prompt, **kwargs):
    """
    Placeholder for a locally-run diffusion model (e.g. via diffusers).
    Left unimplemented until you decide on local hardware/model — returning
    None here just means the router will SKIP the image instead of failing.
    """
    logger.info("local_stable_diffusion not implemented yet — skipping")
    return None


IMAGE_PROVIDERS = {
    "huggingface": huggingface_flux,
    "local": local_stable_diffusion,
}
