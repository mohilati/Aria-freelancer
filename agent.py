import json
import os
import re
from pathlib import Path

import httpx


BASE = os.getenv(
    "GEMINI_BASE_URL",
    "https://generativelanguage.googleapis.com/v1beta",
)

MODEL = os.getenv(
    "GEMINI_MODEL",
    "gemini-2.5-flash",
)

API_KEY = os.getenv("GEMINI_API_KEY", "")

ROOT = Path(__file__).parent
JOBS = ROOT / "jobs"
OUT = ROOT / "outputs"

JOBS.mkdir(exist_ok=True)
OUT.mkdir(exist_ok=True)


SYSTEM = """
You are Aria Freelancer, a professional AI content specialist.

Create useful, accurate, natural Persian or English marketing content.

Rules:
- Never invent facts.
- Never invent prices.
- Never invent credentials.
- Never invent testimonials.
- Never invent citations or sources.
- Never make medical diagnosis claims.
- Never promise treatment results.
- For health-related businesses, keep content educational and safe.
- Flag health-related content for human review when appropriate.
- Follow the client's requested tone and audience.
- Return only the requested deliverable.
"""


def call_gemini(prompt: str) -> str:
    if not API_KEY:
        raise RuntimeError("GEMINI_API_KEY is missing")

    url = f"{BASE}/models/{MODEL}:generateContent"

    headers = {
        "Content-Type": "application/json",
        "x-goog-api-key": API_KEY,
    }

    payload = {
        "system_instruction": {
            "parts": [
                {
                    "text": SYSTEM
                }
            ]
        },
        "contents": [
            {
                "role": "user",
                "parts": [
                    {
                        "text": prompt
                    }
                ]
            }
        ],
        "generationConfig": {
            "temperature": 0.7,
            "maxOutputTokens": 4000,
        },
    }

    with httpx.Client(timeout=60) as client:
        response = client.post(
            url,
            headers=headers,
            json=payload,
        )

        response.raise_for_status()

        data = response.json()

    try:
        return (
            data["candidates"][0]["content"]["parts"][0]["text"]
            .strip()
        )
    except (KeyError, IndexError, TypeError) as exc:
        raise RuntimeError(
            f"Unexpected Gemini response: {json.dumps(data, ensure_ascii=False)[:2000]}"
        ) from exc


def process(job_file: Path) -> Path:
    job = json.loads(
        job_file.read_text(encoding="utf-8")
    )

    brief = job.get("brief", "").strip()

    if not brief:
        raise ValueError(
            "Job must contain a non-empty brief."
        )

    deliverables = job.get(
        "deliverables",
        [
            "10 social-media post ideas with hooks",
            "10 ready-to-publish captions",
            "7-day content calendar",
        ],
    )

    prompt = f"""
CLIENT BRIEF:
{brief}

DELIVERABLES:
{json.dumps(deliverables, ensure_ascii=False, indent=2)}

Create the complete client-ready package.

Requirements:
- Write naturally.
- Match the requested audience and tone.
- Make every requested deliverable complete.
- Avoid repetition.
- Do not invent factual claims.
- For health-related content, avoid diagnosis,
  treatment promises, or unsupported medical claims.
- Structure the final answer clearly with headings.
"""

    result = call_gemini(prompt)

    safe_id = re.sub(
        r"[^a-zA-Z0-9_-]+",
        "_",
        str(job.get("id", job_file.stem)),
    )[:80]

    output_file = OUT / f"{safe_id}.md"

    output_file.write_text(
        result + "\n",
        encoding="utf-8",
    )

    job["status"] = "completed"
    job["output"] = str(
        output_file.relative_to(ROOT)
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
    job_files = sorted(
        JOBS.glob("*.json")
    )

    if not job_files:
        print("No jobs found.")
        return

    for job_file in job_files:
        try:
            job = json.loads(
                job_file.read_text(
                    encoding="utf-8"
                )
            )

            if job.get("status") == "completed":
                print(
                    f"Skipping completed job: {job_file.name}"
                )
                continue

            print(
                f"Processing {job_file.name}..."
            )

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
