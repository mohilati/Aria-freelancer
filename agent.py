"""
agent.py
--------
Aria Freelancer 2.0 — Content Factory orchestrator.

Pipeline: JOB -> PLANNER -> AI ROUTER (text) -> MEDIA ROUTER (image/video)
          -> AUDIO (tts + music) -> FFMPEG assemble -> REVIEW -> DELIVERY

This file only wires pieces together — it imports your existing
content_planner.py / ai_router.py / review_agent.py if they're present in
the repo, and falls back to a minimal stand-in if they're not (so this
still runs standalone while those pieces are being rebuilt).

Run a single job:
    python agent.py --job jobs/example_job.json

Run the whole jobs/ folder:
    python agent.py --jobs-dir jobs
"""

import argparse
import json
import logging
import os
import subprocess
import sys
from pathlib import Path

from media_router import MediaRouter

logger = logging.getLogger("aria.agent")
logging.basicConfig(level=logging.INFO, format="[%(name)s] %(message)s")

OUTPUT_DIR = os.environ.get("ARIA_OUTPUT_DIR", "outputs")
os.makedirs(OUTPUT_DIR, exist_ok=True)


# ---------------------------------------------------------------------------
# Optional integration points — use your real modules if they're in the repo
# ---------------------------------------------------------------------------
try:
    from content_planner import plan_job  # your existing planner
except ImportError:
    def plan_job(job):
        """
        Minimal stand-in planner: turns one job into a list of "items"
        (e.g. N reels), each with a text prompt derived from the job.
        Replace by importing your real content_planner.plan_job.
        """
        quantity = job.get("quantity", 1)
        topic = job.get("topic") or job.get("content_type", "content")
        return [
            {"index": i, "prompt": f"{topic} — item {i + 1} of {quantity}"}
            for i in range(quantity)
        ]

try:
    from review_agent import review_output  # your existing reviewer
except ImportError:
    def review_output(item_result):
        """
        Minimal stand-in reviewer: approves anything that has at least one
        successfully generated media asset. Replace by importing your real
        review_agent.review_output.
        """
        has_asset = any(
            item_result.get(k) and item_result[k].get("ok")
            for k in ("image", "video", "tts", "music")
        )
        return "approved" if has_asset else "revision"


# ---------------------------------------------------------------------------
# FFmpeg assembly
# ---------------------------------------------------------------------------
def assemble_with_ffmpeg(image_path, audio_path, out_path):
    """
    Minimal assembly: a still image + audio track -> mp4. Swap this out
    for a real video_path + audio mux once video providers are live, or
    for a more elaborate ffmpeg filter graph (captions, transitions, etc).
    Returns out_path on success, None on failure.
    """
    if not image_path or not audio_path:
        logger.info("FFMPEG: missing image or audio input — skipping assembly")
        return None

    cmd = [
        "ffmpeg", "-y",
        "-loop", "1",
        "-i", image_path,
        "-i", audio_path,
        "-c:v", "libx264",
        "-tune", "stillimage",
        "-c:a", "aac",
        "-b:a", "192k",
        "-pix_fmt", "yuv420p",
        "-shortest",
        out_path,
    ]
    try:
        subprocess.run(cmd, check=True, capture_output=True)
        return out_path
    except FileNotFoundError:
        logger.warning("FFMPEG: ffmpeg binary not found on PATH — skipping assembly")
        return None
    except subprocess.CalledProcessError as exc:
        logger.warning(f"FFMPEG: assembly failed ({exc.stderr.decode(errors='ignore')[:300]})")
        return None


# ---------------------------------------------------------------------------
# Core cycle
# ---------------------------------------------------------------------------
def process_item(router: MediaRouter, item):
    """Runs one planned item through image + audio + assembly + review."""
    prompt = item["prompt"]
    logger.info(f"--- item {item['index']}: {prompt} ---")

    image_result = router.generate_image(prompt=prompt)
    tts_result = router.generate_tts(text=prompt)
    # music is optional background — comment out if not wanted per item
    music_result = router.generate_music(prompt=prompt)

    assembled_path = None
    if image_result.ok and tts_result.ok:
        out_path = os.path.join(OUTPUT_DIR, f"final_{item['index']}.mp4")
        assembled_path = assemble_with_ffmpeg(
            image_result.output_path, tts_result.output_path, out_path
        )

    item_result = {
        "index": item["index"],
        "prompt": prompt,
        "image": vars(image_result),
        "tts": vars(tts_result),
        "music": vars(music_result),
        "assembled_path": assembled_path,
    }
    item_result["status"] = review_output(item_result)
    return item_result


def run_job(job):
    logger.info(f"=== Running job: {job.get('id', '(no id)')} ===")
    router = MediaRouter()
    planned_items = plan_job(job)

    results = [process_item(router, item) for item in planned_items]

    approved = [r for r in results if r["status"] == "approved"]
    needs_revision = [r for r in results if r["status"] != "approved"]

    logger.info(
        f"=== Job {job.get('id', '(no id)')} done: "
        f"{len(approved)} approved, {len(needs_revision)} need revision ==="
    )
    return results


def cycle(job_path=None, jobs_dir=None):
    """Entry point used by run_once.py / the GitHub Actions workflow."""
    if job_path:
        job = json.loads(Path(job_path).read_text(encoding="utf-8"))
        return {job_path: run_job(job)}

    if jobs_dir:
        all_results = {}
        for jf in sorted(Path(jobs_dir).glob("*.json")):
            job = json.loads(jf.read_text(encoding="utf-8"))
            all_results[str(jf)] = run_job(job)
        return all_results

    logger.warning("cycle() called with neither job_path nor jobs_dir — nothing to do")
    return {}


# kept for backward compatibility with the existing GitHub Actions workflow,
# which calls agent.py's cycle() via run_once.py
main = cycle


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Aria Freelancer 2.0 agent")
    parser.add_argument("--job", help="Path to a single job JSON file")
    parser.add_argument("--jobs-dir", help="Path to a directory of job JSON files")
    args = parser.parse_args()

    if not args.job and not args.jobs_dir:
        parser.error("Pass --job <file> or --jobs-dir <dir>")

    cycle(job_path=args.job, jobs_dir=args.jobs_dir)
