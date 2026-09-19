import json
import re
from pathlib import Path

from ai_router import generate
from content_planner import build_plan
from content_generator import generate_content
from review_agent import review_content
from media_router import MediaRouter
from media_assembler import assemble_video

ROOT = Path(__file__).parent
JOBS = ROOT / "jobs"
OUT = ROOT / "outputs"
JOBS.mkdir(exist_ok=True)
OUT.mkdir(exist_ok=True)

MEDIA_ROUTER = MediaRouter()
MAX_REVIEW_ROUNDS = 3


def safe_id(job):
    return re.sub(r"[^a-zA-Z0-9_-]+", "_", str(job.get("id", "job")))[:80]


def media_result_dict(result):
    return {
        "ok": bool(result.ok),
        "provider": result.provider,
        "output": result.output_path,
        "error": result.error,
        "skipped": bool(result.skipped),
        "reason": getattr(result, "reason", None),
    }


def revise_content(job, plan, current_content, review):
    context = {
        "platform": job.get("platform", ""),
        "language": job.get("language", ""),
        "audience": job.get("audience", ""),
        "tone": job.get("tone", ""),
        "goal": job.get("goal", ""),
        "content_type": job.get("content_type", ""),
        "brand_voice": job.get("brand_voice", ""),
        "constraints": job.get("constraints", []),
        "deliverables": job.get("deliverables", []),
    }
    prompt = f"""
You are the Revision Agent for Aria Freelancer.
Return the COMPLETE revised content package, not a patch.

CLIENT BRIEF:
{job.get("brief", "")}

CONTEXT:
{json.dumps(context, ensure_ascii=False, indent=2)}

APPROVED PLAN:
{json.dumps(plan, ensure_ascii=False, indent=2)}

CURRENT CONTENT:
{current_content}

REVIEW:
{json.dumps(review, ensure_ascii=False, indent=2)}

Rules:
- Fix every critical and major issue.
- Complete every missing deliverable.
- Preserve the approved strategy.
- Match platform, language, audience and tone.
- Never invent statistics, sources or facts.
- Return only the complete final package in Markdown.
"""
    revised = generate(prompt).strip()
    if not revised:
        raise ValueError("Revision Agent returned empty content.")
    return revised


def build_media_plan(job, plan, content):
    prompt = f"""
You are Aria's Media Director.

Create a production-ready JSON specification for a short social-media
video based ONLY on the approved plan and final content below.

Return ONLY valid JSON:
{{
  "title": "...",
  "aspect_ratio": "9:16",
  "duration_seconds": 50,
  "visual_style": "photorealistic premium dermatology commercial",
  "music_prompt": "original instrumental suspense background, no vocals",
  "scenes": [
    {{
      "duration": 6,
      "visual_prompt": "...",
      "on_screen_text": "...",
      "narration": "..."
    }}
  ]
}}

Requirements:
- Persian narration and Persian on-screen text.
- Visual prompts in English.
- For a clinic advertisement, use realistic professional dermatology environments.
- Keep one main adult client visually consistent across scenes.
- Natural skin texture and realistic human anatomy.
- No diagnosis, guaranteed treatment or unsupported medical claims.
- Do not put text/logos inside generated images.
- Keep on-screen text short.
- Use 7 scenes for this test when practical.
- Music must be original instrumental suspense, no vocals.

APPROVED PLAN:
{json.dumps(plan, ensure_ascii=False, indent=2)}

FINAL CONTENT:
{content}
"""
    raw = generate(prompt).strip()
    match = re.search(r"\{.*\}", raw, flags=re.S)
    if not match:
        raise ValueError("Media Director did not return JSON.")
    spec = json.loads(match.group(0))
    if not isinstance(spec.get("scenes"), list) or not spec["scenes"]:
        raise ValueError("Media plan contains no scenes.")
    return spec


def produce_media(job, job_id, plan, content):
    media_dir = OUT / "media" / job_id
    media_dir.mkdir(parents=True, exist_ok=True)

    spec = build_media_plan(job, plan, content)
    scene_assets = []
    failures = []

    continuity = {
        "appearance": (
            "same adult Persian/Middle Eastern female client, "
            "natural facial proportions, medium-length dark hair, "
            "neutral elegant clinic clothing, realistic skin texture"
        )
    }
    reference_note = str(job.get("reference_note") or "")

    for index, scene in enumerate(spec["scenes"], start=1):
        duration = float(scene.get("duration", 6))
        visual_prompt = str(scene.get("visual_prompt", "")).strip()
        narration = str(scene.get("narration", "")).strip()

        print(f"[Media] Scene {index}: video generation")
        video = MEDIA_ROUTER.generate_video(
            prompt=visual_prompt,
            duration=max(4, min(int(round(duration)), 10)),
            aspect_ratio="9:16",
            scene=scene,
            continuity=continuity,
            real_reference_note=reference_note,
        )

        image_path = None
        if not video.ok:
            print(f"[Media] Scene {index}: video unavailable -> image fallback")
            image = MEDIA_ROUTER.generate_image(
                prompt=visual_prompt,
                aspect_ratio="9:16",
                scene=scene,
                continuity=continuity,
                real_reference_note=reference_note,
                qa_attempts=3,
            )
            if image.ok and image.output_path:
                image_path = image.output_path
            else:
                failures.append({
                    "scene": index,
                    "type": "visual",
                    "error": image.error or video.error,
                })
                print(f"[Media] Scene {index}: image generation failed -> {image.error}")
                continue

        voice_path = None
        if narration:
            print(f"[Media] Scene {index}: TTS")
            tts_path = media_dir / f"narration-scene-{index:02d}.mp3"
            tts = MEDIA_ROUTER.generate_tts(
                text=narration,
                language=job.get("language", "Persian"),
                job=job,
                output_path=str(tts_path),
            )
            if tts.ok:
                voice_path = tts.output_path
            else:
                failures.append({
                    "scene": index,
                    "type": "tts",
                    "error": tts.error,
                })
                print(f"[Media] Scene {index}: TTS failed -> {tts.error}")

        if video.ok or image_path:
            scene_assets.append({
                "index": index,
                "duration": duration,
                "video": video.output_path if video.ok else None,
                "image": image_path,
                "voice": voice_path,
                "text": scene.get("on_screen_text", ""),
            })

    if not scene_assets:
        raise RuntimeError(
            "No visual scene was generated. Check KREA_API_KEY/KREA_API_TOKEN, "
            "POLLINATIONS_API_KEY, HF_TOKEN and provider errors above."
        )

    print("[Media] Generating background music")
    music = MEDIA_ROUTER.generate_music(
        prompt=spec.get(
            "music_prompt",
            "dark cinematic suspense instrumental background music, no vocals",
        )
    )
    music_path = music.output_path if music.ok else None
    if not music.ok:
        print(f"[Media] Music unavailable: {music.error}")

    final_path = media_dir / f"{job_id}.mp4"
    assemble_video(
        scene_assets=scene_assets,
        music_path=music_path,
        output_path=final_path,
        aspect_ratio="9:16",
    )

    manifest = {
        "job_id": job_id,
        "media_plan": spec,
        "scene_assets": scene_assets,
        "music": media_result_dict(music),
        "final_video": str(final_path.relative_to(ROOT)),
        "failures": failures,
    }
    manifest_path = media_dir / "media-manifest.json"
    manifest_path.write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    return final_path, manifest


def process(job_file):
    job = json.loads(job_file.read_text(encoding="utf-8"))
    if job.get("status") == "completed":
        print(f"Skipping finalized job: {job_file.name}")
        return None

    brief = job.get("brief", "").strip()
    if not brief:
        raise ValueError("Job must contain a non-empty brief.")

    job["deliverables"] = job.get("deliverables") or [
        "Complete social media content package"
    ]
    job_id = safe_id(job)

    print(f"[Planner] Building content plan for {job_file.name}")
    plan = build_plan(job)

    print(f"[Generator] Generating content for {job_file.name}")
    result = generate_content(job, plan)

    review_history = []
    final_review = None
    manual_review = False

    for round_number in range(1, MAX_REVIEW_ROUNDS + 1):
        print(f"[Review] Starting review round {round_number}/{MAX_REVIEW_ROUNDS}")
        try:
            review = review_content(job=job, plan=plan, content=result)
        except Exception as exc:
            print(f"[Review] failed: {type(exc).__name__}: {exc}")
            manual_review = True
            break

        review["round"] = round_number
        review_history.append(review)
        final_review = review
        print(
            f"[Review] Round {round_number}: "
            f"status={review.get('status')} score={review.get('score')}"
        )

        if review.get("status") == "approved":
            print(f"[Review] Content approved on round {round_number}")
            break

        if review.get("status") == "needs_revision" and round_number < MAX_REVIEW_ROUNDS:
            print(f"[Revision] Revising content (revision {round_number})")
            result = revise_content(job, plan, result, review)
        else:
            manual_review = True
            break

    if manual_review or not final_review or final_review.get("status") != "approved":
        job["status"] = "needs_manual_review"
        job["review_history"] = review_history
        job_file.write_text(
            json.dumps(job, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        raise RuntimeError("Content did not reach an approved review state.")

    print("[Media] Content approved. Starting actual media production.")
    final_video, media_manifest = produce_media(
        job=job,
        job_id=job_id,
        plan=plan,
        content=result,
    )

    output_file = OUT / f"{job_id}.md"
    output_file.write_text(
        "\n".join([
            f"# {job.get('id', job_id)}",
            "",
            "## Content Plan",
            "",
            "```json",
            json.dumps(plan, ensure_ascii=False, indent=2),
            "```",
            "",
            "## Final Content",
            "",
            result,
            "",
            "## Review History",
            "",
            "```json",
            json.dumps(review_history, ensure_ascii=False, indent=2),
            "```",
            "",
            "## Final Video",
            "",
            f"`{final_video.relative_to(ROOT)}`",
            "",
            "## Media Manifest",
            "",
            "```json",
            json.dumps(media_manifest, ensure_ascii=False, indent=2),
            "```",
            "",
        ]),
        encoding="utf-8",
    )

    job["status"] = "completed"
    job["content_plan"] = plan
    job["review_history"] = review_history
    job["final_video"] = str(final_video.relative_to(ROOT))
    job["media_manifest"] = str(
        (OUT / "media" / job_id / "media-manifest.json").relative_to(ROOT)
    )
    job["output"] = str(output_file.relative_to(ROOT))

    job_file.write_text(
        json.dumps(job, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    print(f"SUCCESS {job_file.name} -> {output_file}")
    print(f"[Media] FINAL VIDEO -> {final_video}")
    return output_file


def main():
    for job_file in sorted(JOBS.glob("*.json")):
        try:
            process(job_file)
        except Exception as exc:
            print(
                f"FAILED {job_file.name}: "
                f"{type(exc).__name__}: {exc}"
            )


if __name__ == "__main__":
    main()
