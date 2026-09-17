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


def media_result_dict(result):
    return {
        "ok": bool(result.ok),
        "provider": result.provider,
        "output": result.output_path,
        "error": result.error,
        "skipped": bool(result.skipped),
    }


def generate_cover_image(job, job_id, prompt=None):
    """Best-effort cover image generation."""
    if prompt is None:
        brief = job.get("brief", "").strip()
        if not brief:
            return None

        prompt = (
            "A clean, professional Instagram cover image "
            "representing this business/content brief: "
            f"{brief}. Minimal, modern, professional composition, "
            "no text overlay."
        )

    try:
        result = MEDIA_ROUTER.generate_image(prompt=prompt)
    except Exception as exc:
        print(
            f"[Media][Image] error: "
            f"{type(exc).__name__}: {exc}"
        )
        return None

    if result.ok and result.output_path:
        return result.output_path

    print(f"[Media][Image] skipped: {result.error}")
    return None


def run_media_test(job, job_id):
    """Run the optional full media test: image, video, TTS, music."""
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

    image_prompt = config.get("image", {}).get("prompt")
    if image_prompt:
        print("[MediaTest][Image] generating...")
        try:
            result = MEDIA_ROUTER.generate_image(
                prompt=image_prompt
            )
            results["image"] = media_result_dict(result)
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

    video_prompt = config.get("video", {}).get("prompt")
    if video_prompt:
        print("[MediaTest][Video] generating...")
        try:
            result = MEDIA_ROUTER.generate_video(
                prompt=video_prompt
            )
            results["video"] = media_result_dict(result)
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

    tts_text = config.get("tts", {}).get("text")
    if tts_text:
        print("[MediaTest][TTS] generating...")
        try:
            result = MEDIA_ROUTER.generate_tts(text=tts_text)
            results["tts"] = media_result_dict(result)
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

    music_prompt = config.get("music", {}).get("prompt")
    if music_prompt:
        print("[MediaTest][Music] generating...")
        try:
            result = MEDIA_ROUTER.generate_music(
                prompt=music_prompt
            )
            results["music"] = media_result_dict(result)
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

    successful = sum(
        1
        for key in ("image", "video", "tts", "music")
        if (
            isinstance(results.get(key), dict)
            and results[key].get("ok")
        )
    )

    results["successful_count"] = successful
    results["total_tests"] = 4

    print("=" * 60)
    print(
        "[MediaTest] Finished: "
        f"{successful}/4 media types succeeded."
    )
    print("=" * 60)

    return results


def revise_content(job, plan, current_content, review):
    """Revise content using Review Agent feedback."""
    brief = job.get("brief", "").strip()

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

Your job is to revise an existing generated content package
so that it fully satisfies the client brief and approved
Content Plan.

Do NOT create a new strategy.
Do NOT ignore the approved plan.
Do NOT provide a partial patch.

Return the COMPLETE revised content package.

CLIENT BRIEF:
{brief}

CONTENT CONTEXT:
{json.dumps(context, ensure_ascii=False, indent=2)}

APPROVED CONTENT PLAN:
{json.dumps(plan, ensure_ascii=False, indent=2)}

CURRENT GENERATED CONTENT:
{current_content}

REVIEW AGENT FEEDBACK:
{json.dumps(review, ensure_ascii=False, indent=2)}

REVISION RULES:
1. Fix every critical and major issue.
2. Complete every missing deliverable.
3. Preserve the approved Content Plan.
4. Preserve useful parts of the current content.
5. Do not remove completed deliverables.
6. Return the FULL content package.
7. Match platform, language, audience and tone.
8. Never invent statistics, sources or factual claims.
9. For psychology/health content, avoid diagnosis,
   treatment promises and unsupported medical claims.
10. Remove placeholder text and broken formatting.
11. Make the result directly usable by the client.
12. Organize with Markdown headings.
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

    media_only = bool(job.get("media_only", False))
    media_enabled = (
        isinstance(job.get("media_test"), dict)
        and job["media_test"].get("enabled", False)
    )

    if media_only and media_enabled:
        print(
            f"[MediaOnly] Running media test "
            f"for {job_file.name}"
        )

        media_results = run_media_test(
            job=job,
            job_id=job_id,
        )

        output_file = OUT / f"{job_id}.md"

        output_parts = [
            "# Aria Media Stack Test\n\n",
            "```json\n",
            json.dumps(
                media_results,
                ensure_ascii=False,
                indent=2,
            ),
            "\n```\n",
        ]

        output_file.write_text(
            "".join(output_parts),
            encoding="utf-8",
        )

        job["status"] = (
            "completed"
            if (
                media_results
                and media_results.get("successful_count", 0) > 0
            )
            else "needs_manual_review"
        )

        job["output"] = str(
            output_file.relative_to(ROOT)
        )
        job["media_results"] = media_results

        job_file.write_text(
            json.dumps(
                job,
                ensure_ascii=False,
                indent=2,
            ),
            encoding="utf-8",
        )

        return output_file

    print(
        f"[Planner] Building content plan "
        f"for {job_file.name}"
    )
    plan = build_plan(job)

    print(
        f"[Generator] Generating content "
        f"for {job_file.name}"
    )
    result = generate_content(job, plan)

    review_history = []
    revision_count = 0
    final_review = None
    manual_review_required = False
    review_error = None

    for round_number in range(1, MAX_REVIEW_ROUNDS + 1):
        print(
            "[Review] Starting review round "
            f"{round_number}/{MAX_REVIEW_ROUNDS}"
        )

        try:
            review = review_content(
                job=job,
                plan=plan,
                content=result,
            )
        except Exception as exc:
            review_error = (
                f"{type(exc).__name__}: {exc}"
            )

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
                "[Review] Content approved "
                f"on round {round_number}"
            )
            break

        if review.get("status") == "needs_revision":
            if round_number < MAX_REVIEW_ROUNDS:
                revision_count += 1

                print(
                    "[Revision] Revising content "
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
                    review_error = (
                        f"{type(exc).__name__}: {exc}"
                    )

                    print(
                        "[Revision] Revision Agent failed: "
                        f"{review_error}"
                    )

                    manual_review_required = True

                    review_history.append(
                        {
                            "round": round_number,
                            "status": "manual_review",
                            "score": None,
                            "issues": [
                                {
                                    "severity": "critical",
                                    "category": (
                                        "revision_agent_failure"
                                    ),
                                    "description": review_error,
                                }
                            ],
                            "missing_deliverables": [],
                            "revision_instructions": [],
                            "reviewer": (
                                "aria-revision-agent-v1"
                            ),
                        }
                    )

                    break
            else:
                print(
                    "[Review] Maximum review rounds reached. "
                    "Manual review required."
                )
                manual_review_required = True
                break

    media_results = run_media_test(
        job=job,
        job_id=job_id,
    )

    cover_image_path = None

    if not media_enabled:
        cover_image_path = generate_cover_image(
            job,
            job_id,
        )

    output_file = OUT / f"{job_id}.md"
    output_parts = []

    if media_results is not None:
        output_parts.append(
            "# Media Test Results\n\n"
        )
        output_parts.append("```json\n")
        output_parts.append(
            json.dumps(
                media_results,
                ensure_ascii=False,
                indent=2,
            )
        )
        output_parts.append("\n```\n\n")

    if cover_image_path:
        output_parts.append(
            f"![cover]({cover_image_path})\n\n"
        )

    output_parts.append("# Content Plan\n\n")
    output_parts.append(
        json.dumps(
            plan,
            ensure_ascii=False,
            indent=2,
        )
    )
    output_parts.append("\n\n")

    output_parts.append("# Review History\n\n")
    output_parts.append("```json\n")
    output_parts.append(
        json.dumps(
            review_history,
            ensure_ascii=False,
            indent=2,
        )
    )
    output_parts.append("\n```\n\n")

    final_status = (
        "completed"
        if (
            final_review
            and final_review.get("status") == "approved"
            and not manual_review_required
        )
        else "needs_manual_review"
    )

    output_parts.append("# Final Status\n\n")
    output_parts.append(
        f"**{final_status}**\n\n"
    )

    output_parts.append("# Final Content\n\n")
    output_parts.append(result)
    output_parts.append("\n")

    output_file.write_text(
        "".join(output_parts),
        encoding="utf-8",
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
    for job_file in sorted(JOBS.glob("*.json")):
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
                    "Skipping finalized job: "
                    f"{job_file.name}"
                )
                continue

            output = process(job_file)

            print(
                f"SUCCESS {job_file.name} "
                f"-> {output}"
            )

        except Exception as exc:
            print(
                f"FAILED {job_file.name}: "
                f"{type(exc).__name__}: {exc}"
            )


if __name__ == "__main__":
    main()
