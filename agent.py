import json
import re
from pathlib import Path

from content_planner import build_plan
from content_generator import generate_content
from review_agent import review_content

ROOT = Path(__file__).parent
JOBS = ROOT / "jobs"
OUT = ROOT / "outputs"

JOBS.mkdir(exist_ok=True)
OUT.mkdir(exist_ok=True)


def process(job_file):
    job = json.loads(job_file.read_text(encoding="utf-8"))

    brief = job.get("brief", "").strip()
    if not brief:
        raise ValueError("Job must contain a non-empty brief.")

    deliverables = job.get("deliverables", [
        "10 social-media post ideas with hooks",
        "10 ready-to-publish captions",
        "7-day content calendar",
    ])

    job["deliverables"] = deliverables

    # Stage 1: Content Planner
    plan = build_plan(job)

    # Stage 2: Content Generator
    result = generate_content(job, plan)

    # Stage 3: Review Agent
    review = review_content(job, plan, result)

    safe_id = re.sub(
        r"[^a-zA-Z0-9_-]+",
        "_",
        str(job.get("id", job_file.stem))
    )[:80]

    output_file = OUT / f"{safe_id}.md"

    output_file.write_text(
        "# Content Plan\n\n"
        + json.dumps(plan, ensure_ascii=False, indent=2)
        + "\n\n# Review\n\n"
        + json.dumps(review, ensure_ascii=False, indent=2)
        + "\n\n# Final Deliverable\n\n"
        + result
        + "\n",
        encoding="utf-8"
    )

    job["status"] = "completed"
    job["output"] = str(output_file.relative_to(ROOT))
    job["content_plan"] = plan
    job["review"] = review

    job_file.write_text(
        json.dumps(job, ensure_ascii=False, indent=2),
        encoding="utf-8"
    )

    return output_file


def main():
    for job_file in sorted(JOBS.glob("*.json")):
        try:
            job = json.loads(
                job_file.read_text(encoding="utf-8")
            )

            if job.get("status") == "completed":
                print(f"Skipping completed job: {job_file.name}")
                continue

            output = process(job_file)
            print(f"SUCCESS {job_file.name} -> {output}")

        except Exception as exc:
            print(
                f"FAILED {job_file.name}: "
                f"{type(exc).__name__}: {exc}"
            )


if __name__ == "__main__":
    main()
