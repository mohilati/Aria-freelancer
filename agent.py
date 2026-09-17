import json
import re
from pathlib import Path

from ai_router import generate
from content_planner import build_plan
from content_generator import generate_content
from review_agent import review_content
from media_router import MediaRouter


ROOT = Path(__file__).parent
JOBS = ROOT / "jobs"
OUT = ROOT / "outputs"

JOBS.mkdir(exist_ok=True)
OUT.mkdir(exist_ok=True)

MEDIA_ROUTER = MediaRouter()

MAX_REVIEW_ROUNDS = 3


def safe_id(job):
    return re.sub(
        r"[^a-zA-Z0-9_-]+",
        "_",
        str(job.get("id", "job")),
    )[:80]


def generate_cover_image(job, job_id, prompt=None):
    """Best-effort image generation."""
    if prompt is None:
        brief = job.get("brief", "").strip()
        if not brief:
            return None

        prompt = (
            f"A clean, professional Instagram cover image representing "
            f"this business/brief: {brief}. "
            f"Minimal, on-brand, no text overlay."
        )

    result = MEDIA_ROUTER.generate_image(prompt=prompt)

    if result.ok and result.output_path:
        return result.output_path

    print(f"[Media][Image] skipped: {result.error}")
    return None


def run_media_test(job, job_id):
    """
    Execute the optional full media test defined by job['media_test'].

    Tests:
      - image
      - video
      - tts
      - music

    Every provider is best-effort. A failed media provider does not kill
    the content job.
    """
    config = job.get("media_test")

    if not isinstance(config, dict):
        return None

    if not config.get("enabled", False):
        return None

    print("=" * 60)
    print(f"[MediaTest] Starting full media test: {job_id}")
    print("=" * 60)

    results = {
        "enabled": True,
        "image": None,
        "video": None,
        "tts": None,
        "music": None,
    }

    # ------------------------------------------------------------
    # IMAGE
    # ------------------------------------------------------------
    image_cfg = config.get("image", {})
    image_prompt = image_cfg.get("prompt")

    if image_prompt:
        print("[MediaTest][Image] generating...")
        try:
            result = MEDIA_ROUTER.generate_image(
                prompt=image_prompt
            )

            results["image"] = {
                "ok": result.ok,
                "provider": result.provider,
                "output": result.output_path,
                "error": result.error,
                "skipped": result.skipped,
            }

            if result.ok:
                print(
                    f"[MediaTest][Image] SUCCESS -> "
                    f"{result.output_path}"
                )
            else:
                print(
                    f"[MediaTest][Image] FAILED/SKIPPED -> "
                    f"{result.error}"
                )

        except Exception as exc:
            results["image"] = {
                "ok": False,
                "provider": "none",
                "output": None,
                "error": f"{type(exc).__name__}: {exc}",
                "skipped": True,
            }
            print(f"[MediaTest][Image] ERROR -> {exc}")

    # ------------------------------------------------------------
    # VIDEO
    # ------------------------------------------------------------
    video_cfg = config.get("video", {})
    video_prompt = video_cfg.get("prompt")

    if video_prompt:
        print("[MediaTest][Video] generating...")
        try:
            result = MEDIA_ROUTER.generate_video(
                prompt=video_prompt
            )

            results["video"] = {
                "ok": result.ok,
                "provider": result.provider,
                "output": result.output_path,
                "error": result.error,
                "skipped": result.skipped,
            }

            if result.ok:
                print(
                    f"[MediaTest][Video] SUCCESS -> "
                    f"{result.output_path}"
                )
            else:
                print(
                    f"[MediaTest][Video] FAILED/SKIPPED -> "
                    f"{result.error}"
                )

        except Exception as exc:
            results["video"] = {
                "ok": False,
                "provider": "none",
                "output": None,
                "error": f"{type(exc).__name__}: {exc}",
                "skipped": True,
            }
            print(f"[MediaTest][Video] ERROR -> {exc}")

    # ------------------------------------------------------------
    # TTS
    # ------------------------------------------------------------
    tts_cfg = config.get("tts", {})
    tts_text = tts_cfg.get("text")

    if tts_text:
        print("[MediaTest][TTS] generating...")
        try:
            result = MEDIA_ROUTER.generate_tts(
                text=tts_text
            )

            results["tts"] = {
                "ok": result.ok,
                "provider": result.provider,
                "output": result.output_path,
                "error": result.error,
                "skipped": result.skipped,
            }

            if result.ok:
                print(
                    f"[MediaTest][TTS] SUCCESS -> "
                    f"{result.output_path}"
                )
            else:
                print(
                    f"[MediaTest][TTS] FAILED/SKIPPED -> "
                    f"{result.error}"
                )

        except Exception as exc:
            results["tts"] = {
                "ok": False,
                "provider": "none",
                "output": None,
                "error": f"{type(exc).__name__}: {exc}",
                "skipped": True,
            }
            print(f"[MediaTest][TTS] ERROR -> {exc}")

    # ------------------------------------------------------------
    # MUSIC
    # ------------------------------------------------------------
    music_cfg = config.get("music", {})
    music_prompt = music_cfg.get("prompt")

    if music_prompt:
        print("[MediaTest][Music] generating...")
        try:
            result = MEDIA_ROUTER.generate_music(
                prompt=music_prompt
            )

            results["music"] = {
                "ok": result.ok,
                "provider": result.provider,
                "output": result.output_path,
                "error": result.error,
                "skipped": result.skipped,
            }

            if result.ok:
                print(
                    f"[MediaTest][Music] SUCCESS -> "
                    f"{result.output_path}"
                )
            else:
                print(
                    f"[MediaTest][Music] FAILED/SKIPPED -> "
                    f"{result.error}"
                )

        except Exception as exc:
            results["music"] = {
                "ok": False,
                "provider": "none",
                "output": None,
                "error": f"{type(exc).__name__}: {exc}",
                "skipped": True,
            }
            print(f"[MediaTest][Music] ERROR -> {exc}")

    # ------------------------------------------------------------
    # SUMMARY
    # ------------------------------------------------------------
    successful = sum(
        1
        for item in results.values()
        if isinstance(item, dict) and item.get("ok")
    )

    results["successful_count"] = successful
    results["total_tests"] = 4

    print("=" * 60)
    print(
        f"[MediaTest] Finished: "
        f"{successful}/4 media types generated successfully."
    )
    print("=" * 60)

    return results


def revise_content(job, plan, current_content, review):
    """Revise the current content using Review Agent feedback."""
    brief = job.get("brief", "").strip()

    prompt = f"""You are the Revision Agent for Aria Freelancer.

Your job is to revise an existing generated content package so that it
fully satisfies the client brief and the approved Content Plan.

Do NOT create a new strategy.
Do NOT ignore the approved plan.
Do NOT provide a partial patch.
Return the COMPLETE revised content package.

CLIENT BRIEF:
{brief}

CONTENT CONTEXT:
{json.dumps({
    "platform": job.get("platform", ""),
    "language": job.get("language", ""),
    "audience": job.get("audience", ""),
    "tone": job.get("tone", ""),
    "goal": job.get("goal", ""),
    "content_type": job.get("content_type", ""),
    "brand_voice": job.get("brand_voice", ""),
    "constraints": job.get("constraints", []),
    "deliverables": job.get("deliverables", [])
}, ensure_ascii=False, indent=2)}

APPROVED CONTENT PLAN:
{json.dumps(plan, ensure_ascii=False, indent=2)}

CURRENT GENERATED CONTENT:
{current_content}

REVIEW AGENT FEEDBACK:
{json.dumps(review, ensure_ascii=False, indent=2)}

REVISION RULES:
1. Fix every critical and major issue identified by the Review Agent.
2. Complete every missing deliverable.
3. Preserve the approved Content Plan.
4. Preserve useful parts of the current content.
5. Do not remove completed deliverables.
6. Return the FULL content package.
7. Match the requested platform, language, audience and tone.
8. Never invent statistics, sources or factual claims.
9. For psychology/health content, avoid diagnosis, treatment promises and
   unsupported medical claims.
10. Remove placeholder text and broken formatting.
11. Make the final result directly usable by the client.
12. Clearly organize the final result with Markdown headings.
13. Return ONLY the complete revised content package.

Produce the complete revised package now.
"""

    revised = generate(prompt).strip()

    if not revised:
        raise ValueError("Revision Agent returned empty content.")

    return revised


def process(job_file):
    job = json.loads(
        job_file.read_text(encoding="utf-8")
    )

    brief = job.get("brief", "").strip()

    if not brief:
        raise ValueError("Job must contain a non-empty brief.")

    deliverables = job.get(
        "deliverables",
        [
            "10 social-media post ideas with hooks",
            "10 ready-to-publish captions",
            "7-day content calendar",
        ],
    )

    job["deliverables"] = deliverables

    job_id = safe_id(job)

    # ============================================================
    # Stage 1: Content Planner
    # ============================================================
    print(f"[Planner] Building content plan for {job_file.name}")
    plan = build_plan(job)

    # ============================================================
    # Stage 2: Content Generator
    # ============================================================
    print(f"[Generator] Generating content for {job_file.name}")
    result = generate_content(job, plan)

    # ============================================================
    # Stage 3-5: Review + Revision
    # ============================================================
    review_history = []
    revision_count = 0
    final_review = None
    manual_review_required = False
    review_error = None

    for round_number in range(
        1,
        MAX_REVIEW_ROUNDS + 1,
    ):
        print(
            f"[Review] Starting review round "
            f"{round_number}/{MAX_REVIEW_ROUNDS}"
        )

        try:
            review = review_content(
                job=job,
                plan=plan,
                content=result,
            )

        except Exception as exc:
            review_error = str(exc)

            print(
                f"[Review] Review Agent failed: "
                f"{review_error}"
            )

            manual_review_required = True

            review = {
                "round": round_number,
                "status": "manual_review",
                "score": None,
                "issues": [
                    {
                        "severity": "critical",
                        "category": "review_agent_failure",
                        "description": review_error,
                    }
                ],
                "missing_deliverables": [],
                "revision_instructions": [],
                "reviewer": "aria-review-agent-v1",
            }

            review_history.append(review)
            final_review = review
            break

        review["round"] = round_number
        review_history.append(review)
        final_review = review

        print(
            f"[Review] Round {round_number}: "
            f"status={review.get('status')} "
            f"score={review.get('score')}"
        )

        if review.get("status") == "approved":
            print(
                f"[Review] Content approved on round "
                f"{round_number}"
            )
            break

        if review.get("status") == "needs_revision":
            if round_number < MAX_REVIEW_ROUNDS:
                revision_count += 1

                print(
                    f"[Revision] Revising content "
                    f"(revision {revision_count})"
                )

                try:
                    result = revise_content(
                        job=job,
                        plan=plan,
                        current_content=result,
                        review=review,
                    )

                except Exception as exc:
                    review_error = str(exc)

                    print(
                        f"[Revision] Revision Agent failed: "
                        f"{review_error}"
                    )

                    manual_review_required = True

                    review_history.append({
                        "round": round_number,
                        "status": "manual_review",
                        "score": None,
                        "issues": [
                            {
                                "severity": "critical",
                                "category": "revision_agent_failure",
                                "description": review_error,
                            }
                        ],
                        "missing_deliverables": [],
                        "revision_instructions": [],
                        "reviewer": "aria-revision-agent-v1",
                    })

                    break

            else:
                print(
                    "[Review] Maximum review rounds reached. "
                    "Manual review required."
                )

                manual_review_required = True
                break

    # ============================================================
    # Stage 6: Optional FULL Media Test
    # ============================================================
    media_results = run_media_test(
        job=job,
        job_id=job_id,
    )

    # ============================================================
    # Stage 7: Legacy/default cover image
    #
    # Only run this when full media test is NOT enabled.
    # This prevents generating the image twice.
    # ============================================================
    cover_image_path = None

    if not (
        isinstance(job.get("media_test"), dict)
        and job["media_test"].get("enabled", False)
    ):
        cover_image_path = generate_cover_image(
            job,
            job_id,
        )

    # ============================================================
    # Output filename
    # ============================================================
    output_file = OUT / f"{job_id}.md"

    output_parts = []

    # ============================================================
    # Media Test Report
    # ============================================================
    if media_results is not None:
        output_parts.append(
            "# Media Test Results\n\n"
        )

        output_parts.append(
            "```json\n"
        )

        output_parts.append(
            json.dumps(
                media_results,
                ensure_ascii=False,
                indent=2,
            )
        )

        output_parts.append(
            "\n```\n\n"
        )

    # ============================================================
    # Cover
    # ============================================================
    if cover_image_path:
        output_parts.append(
            f"![cover]({cover_image_path})\n\n"
        )

    # ============================================================
    # Content Plan
    # ============================================================
    output_parts.append(
        "# Content Plan\n\n"
    )

    output_parts.append(
        json.dumps(
            plan,
            ensure_ascii=False,
            indent=2,
        )
    )

    output_parts.append(
        "\n\n"
    )

    # ============================================================
    # Review History
    # ============================================================
    output_parts.append(
        "# Review History\n\n"
    )

    for review in review_history:
        round_number = review.get(
            "round",
            "?",
        )

        output_parts.append(
            f"## Review Round {round_number}\n\n"
        )

        output_parts.append(
            json.dumps(
                review,
                ensure_ascii=False,
                indent=2,
            )
        )

        output_parts.append(
            "\n\n"
        )

    # ============================================================
    # Final Status
    # ============================================================
    output_parts.append(
        "# Final Status\n\n"
    )

    if manual_review_required:
        output_parts.append(
            "Status: MANUAL_REVIEW_REQUIRED\n\n"
        )

        if review_error:
            output_parts.append(
                f"Reason: {review_error}\n\n"
            )

    else:
        output_parts.append(
            "Status: COMPLETED\n\n"
        )

    # ============================================================
    # Final Content
    # ============================================================
    output_parts.append(result)
    output_parts.append("\n")

    output_file.write_text(
        "".join(output_parts),
        encoding="utf-8",
    )

    # ============================================================
    # Job Metadata
    # ============================================================
    final_status = (
        "completed"
        if final_review
        and final_review.get("status") == "approved"
        else "needs_manual_review"
    )

    job["status"] = final_status

    job["output"] = str(
        output_file.relative_to(ROOT)
    )

    job["content_plan"] = plan
    job["review"] = final_review
    job["review_history"] = review_history
    job["review_rounds"] = len(review_history)
    job["revision_count"] = revision_count

    job["cover_image"] = (
        str(cover_image_path)
        if cover_image_path
        else None
    )

    job["media_results"] = media_results

    job["final_review_status"] = (
        final_review.get("status")
        if final_review
        else "unknown"
    )

    job_file.write_text(
        json.dumps(
            job,
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )

    return output_file


def main():
    for job_file in sorted(
        JOBS.glob("*.json")
    ):
        try:
            job = json.loads(
                job_file.read_text(
                    encoding="utf-8"
                )
            )

            if job.get("status") in {
                "completed",
                "needs_manual_review",
            }:
                print(
                    f"Skipping finalized job: "
                    f"{job_file.name}"
                )
                continue

            output = process(job_file)

            print(
                f"SUCCESS {job_file.name} -> {output}"
            )

        except Exception as exc:
            print(
                f"FAILED {job_f
