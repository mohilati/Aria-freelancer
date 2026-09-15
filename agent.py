import json
import re
from pathlib import Path
from ai_router import generate

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
    context = {k: job.get(k, "") for k in (
        "platform", "language", "audience", "tone", "goal", "content_type", "brand_voice"
    )}
    context["constraints"] = job.get("constraints", [])
    context["review_required"] = job.get("review_required", True)
    prompt = f"""CLIENT BRIEF:
{brief}

CONTENT CONTEXT:
{json.dumps(context, ensure_ascii=False, indent=2)}

DELIVERABLES:
{json.dumps(deliverables, ensure_ascii=False, indent=2)}

Create the complete client-ready package.
Write naturally, match the audience/tone/platform/goal, complete every deliverable,
avoid repetition, keep it practical, and never invent factual claims.
For health businesses, avoid diagnosis, treatment promises and unsupported medical claims.
Clearly structure the final answer with headings.
Return ONLY the final deliverable.
"""
    result = generate(prompt)
    safe_id = re.sub(r"[^a-zA-Z0-9_-]+", "_", str(job.get("id", job_file.stem)))[:80]
    output_file = OUT / f"{safe_id}.md"
    output_file.write_text(result + "\n", encoding="utf-8")
    job["status"] = "completed"
    job["output"] = str(output_file.relative_to(ROOT))
    job_file.write_text(json.dumps(job, ensure_ascii=False, indent=2), encoding="utf-8")
    return output_file

def main():
    for job_file in sorted(JOBS.glob("*.json")):
        try:
            job = json.loads(job_file.read_text(encoding="utf-8"))
            if job.get("status") == "completed":
                print(f"Skipping completed job: {job_file.name}")
                continue
            output = process(job_file)
            print(f"SUCCESS {job_file.name} -> {output}")
        except Exception as exc:
            print(f"FAILED {job_file.name}: {type(exc).__name__}: {exc}")

if __name__ == "__main__":
    main()
