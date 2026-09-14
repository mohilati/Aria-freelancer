import json, os, re
from pathlib import Path
import httpx

BASE = os.getenv("GEMINI_BASE_URL", "https://generativelanguage.googleapis.com/v1beta")
MODEL = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")
API_KEY = os.getenv("GEMINI_API_KEY", "")
ROOT = Path(__file__).parent
JOBS, OUT = ROOT/"jobs", ROOT/"outputs"
JOBS.mkdir(exist_ok=True); OUT.mkdir(exist_ok=True)

SYSTEM = """You are Aria Freelancer, a professional AI content specialist.
Create useful, accurate, natural Persian or English marketing content.
Never invent facts, prices, credentials, testimonials, citations, medical claims, or guarantees.
For health-related businesses, avoid diagnosis/treatment claims and flag content for human review.
Follow the client's requested tone and audience. Return only the requested deliverable."""

def call_gemini(prompt):
    if not API_KEY:
        raise RuntimeError("GEMINI_API_KEY is missing")
    url = f"{BASE}/models/{MODEL}:generateContent?key={API_KEY}"
    payload = {
        "system_instruction": {"parts": [{"text": SYSTEM}]},
        "contents": [{"role": "user", "parts": [{"text": prompt}]}],
        "generationConfig": {"temperature": 0.7, "maxOutputTokens": 4000},
    }
    with httpx.Client(timeout=60) as client:
        r = client.post(url, json=payload)
        r.raise_for_status()
        data = r.json()
    return data["candidates"][0]["content"]["parts"][0]["text"].strip()

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
    prompt = f"""CLIENT BRIEF:
{brief}

DELIVERABLES:
{json.dumps(deliverables, ensure_ascii=False, indent=2)}

Create the complete client-ready package. Structure it clearly with headings.
Silently check relevance, factual safety, variety, language quality, and completeness."""
    result = call_gemini(prompt)
    safe_id = re.sub(r"[^a-zA-Z0-9_-]+", "_", str(job.get("id", job_file.stem)))[:80]
    out = OUT / f"{safe_id}.md"
    out.write_text(result + "\n", encoding="utf-8")
    job["status"] = "completed"
    job["output"] = str(out.relative_to(ROOT))
    job_file.write_text(json.dumps(job, ensure_ascii=False, indent=2), encoding="utf-8")
    return out

def main():
    for jf in sorted(JOBS.glob("*.json")):
        try:
            job = json.loads(jf.read_text(encoding="utf-8"))
            if job.get("status") == "completed":
                continue
            print(f"Processing {jf.name}...")
            print(process(jf))
        except Exception as e:
            print(f"FAILED {jf.name}: {type(e).__name__}: {e}")

if __name__ == "__main__":
    main()
