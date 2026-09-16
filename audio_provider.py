"""
audio_provider.py
------------------
Two separate provider chains live here: TTS_PROVIDERS (speech) and
MUSIC_PROVIDERS (background music). Same contract as the other provider
modules — return an output path or None.
"""

import os
import time
import logging

logger = logging.getLogger("aria.audio_provider")

OUTPUT_DIR = os.environ.get("ARIA_OUTPUT_DIR", "outputs")
os.makedirs(OUTPUT_DIR, exist_ok=True)


def _new_output_path(label, ext):
    ts = int(time.time() * 1000)
    return os.path.join(OUTPUT_DIR, f"{label}_{ts}.{ext}")


# ---------- TTS ----------

def huggingface_tts(text, **kwargs):
    hf_token = os.environ.get("HF_TOKEN")
    if not hf_token:
        logger.info("HF_TOKEN not set — skipping huggingface_tts")
        return None

    import requests

    model = kwargs.get("model", "espnet/kan-bayashi_ljspeech_vits")
    url = f"https://api-inference.huggingface.co/models/{model}"
    headers = {"Authorization": f"Bearer {hf_token}"}

    resp = requests.post(url, headers=headers, json={"inputs": text}, timeout=120)
    resp.raise_for_status()

    out_path = _new_output_path("tts", "wav")
    with open(out_path, "wb") as f:
        f.write(resp.content)
    return out_path


def local_tts(text, **kwargs):
    """
    Placeholder for a fully local/offline TTS (e.g. pyttsx3, Coqui TTS).
    Useful as the last fallback since it never depends on a network call.
    """
    logger.info("local_tts not implemented yet — skipping")
    return None


# ---------- Music (MusicGen) ----------

def musicgen_local(prompt, **kwargs):
    """
    Runs Meta's MusicGen locally via the `audiocraft` or `transformers`
    library. Left unimplemented until you decide which size (small/
    medium/large) fits your hardware — small (300M) is the realistic
    default for modest GPUs/CPUs.
    """
    logger.info("musicgen_local not implemented yet — skipping")
    return None


def huggingface_musicgen(prompt, **kwargs):
    hf_token = os.environ.get("HF_TOKEN")
    if not hf_token:
        logger.info("HF_TOKEN not set — skipping huggingface_musicgen")
        return None

    import requests

    model = kwargs.get("model", "facebook/musicgen-small")
    url = f"https://api-inference.huggingface.co/models/{model}"
    headers = {"Authorization": f"Bearer {hf_token}"}

    resp = requests.post(url, headers=headers, json={"inputs": prompt}, timeout=180)
    resp.raise_for_status()

    out_path = _new_output_path("music", "wav")
    with open(out_path, "wb") as f:
        f.write(resp.content)
    return out_path


TTS_PROVIDERS = {
    "huggingface": huggingface_tts,
    "local": local_tts,
}

MUSIC_PROVIDERS = {
    "huggingface": huggingface_musicgen,
    "local": musicgen_local,
}
