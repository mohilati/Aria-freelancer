import json
import re
from pathlib import Path

from ai_router import generate
from content_planner import build_plan
from content_generator import generate_content
from review_agent import review_content


ROOT = Path(__file__).parent
JOBS = ROOT / "jobs"
OUT = ROOT / "outputs"

JOBS.mkdir(exist_ok=True)
OUT.mkdir(exist_ok=True)

MAX_REVIEW_ROUNDS = 3


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
4. Preserve useful parts of the current content when they already satisfy
   the brief.
5. Do not remove completed deliverables just to fix another issue.
6. Return the FULL content package, not only the changed sections.
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
    job = json.loads(job_file.read_text(encoding="utf-8"))

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

    # ============================================================
    # Stage 1: Content Planner
    # ============================================================

    print(f"[Planner] Building content plan for {job_file.name}")

    plan = build_plan(job)

    # ============================================================
    # Stage 2: Initial Content Generation
    # ============================================================

    print(f"[Generator] Generating initial content for {job_file.name}")

    result = generate_content(job, plan)

    # ============================================================
    # Stage 3-5: Review + Revision Loop
    #
    # Maximum:
    #   Round 1 = Generate -> Review
    #   Round 2 = Revision -> Review
    #   Round 3 = Revision -> Review
    # ============================================================

    review_history = []
    revision_count = 0
    final_review = None

        manual_review_required = False
    review_error = None

    for round_number in range(1, MAX_REVIEW_ROUNDS + 1):

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
                f"[Review] Review Agent failed on round "
                f"{round_number}: {review_error}"
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

        # --------------------------------------------------------
        # Approved
        # --------------------------------------------------------

        if review.get("status") == "approved":

            print(
                f"[Review] Content approved on round "
                f"{round_number}"
            )

            break

        # --------------------------------------------------------
        # Needs revision
        # --------------------------------------------------------

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

        print(
            f"[Review] Starting review round "
            f"{round_number}/{MAX_REVIEW_ROUNDS}"
        )

        review = review_content(
            job=job,
            plan=plan,
            content=result,
        )

        review["round"] = round_number
        review_history.append(review)

        final_review = review

        print(
            f"[Review] Round {round_number}: "
            f"status={review.get('status')} "
            f"score={review.get('score')}"
        )

        # --------------------------------------------------------
        # Approved
        # --------------------------------------------------------

        if review.get("status") == "approved":
            print(
                f"[Review] Content approved on round "
                f"{round_number}"
            )
            break

        # --------------------------------------------------------
        # Needs revision
        # --------------------------------------------------------

        if round_number < MAX_REVIEW_ROUNDS:

            revision_count += 1

            print(
                f"[Revision] Revising content "
                f"(revision {revision_count})"
            )

            result = revise_content(
                job=job,
                plan=plan,
                current_content=result,
                review=review,
            )

        else:

            print(
                "[Review] Maximum review rounds reached. "
                "Manual review required."
            )

    # ============================================================
    # Prepare safe output filename
    # ============================================================

    safe_id = re.sub(
        r"[^a-zA-Z0-9_-]+",
        "_",
        str(job.get("id", job_file.stem)),
    )[:80]

    output_file = OUT / f"{safe_id}.md"

    # ============================================================
    # Build output document
    # ============================================================

    output_parts = []

    output_parts.append("# Content Plan\n\n")
    output_parts.append(
        json.dumps(
            plan,
            ensure_ascii=False,
            indent=2,
        )
    )
    output_parts.append("\n\n")

    # ------------------------------------------------------------
    # Review history
    # ------------------------------------------------------------

    output_parts.append("# Review History\n\n")

    for review in review_history:

        round_number = review.get("round", "?")

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

        output_parts.append("\n\n")

    # ------------------------------------------------------------
    # Final content
    # ------------------------------------------------------------

        # ------------------------------------------------------------
    # Final status
    # ------------------------------------------------------------

    output_parts.append("# Final Status\n\n")

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
    output_parts.append(result)
    output_parts.append("\n")

    output_file.write_text(
        "".join(output_parts),
        encoding="utf-8",
    )

    # ============================================================
    # Update Job Metadata
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

            # Jobs that are already finished should not
            # be processed again automatically.

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
                f"FAILED {job_file.name}: "
                f"{type(exc).__name__}: {exc}"
            )


if __name__ == "__main__":
    main()
