import json
import re
from ai_router import generate


MAX_REVIEW_RETRIES = 2


def _extract_json(raw):
    """Try to extract a JSON object from an LLM response."""

    raw = raw.strip()

    # Normal JSON
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        pass

    # Remove markdown code fences
    cleaned = re.sub(
        r"^```(?:json)?\s*|\s*```$",
        "",
        raw,
        flags=re.IGNORECASE | re.DOTALL,
    ).strip()

    try:
        return json.loads(cleaned)
    except json.JSONDecodeError:
        pass

    # Extract the first JSON object
    match = re.search(r"\{.*\}", cleaned, flags=re.DOTALL)

    if match:
        candidate = match.group(0)

        try:
            return json.loads(candidate)
        except json.JSONDecodeError:
            pass

    return None


def _build_prompt(job, plan, content, strict=False):
    strict_instruction = ""

    if strict:
        strict_instruction = """
IMPORTANT:
Your previous response was not valid JSON.

Return ONLY a single valid JSON object.
Do not use Markdown.
Do not use ```json fences.
Do not add explanations before or after the JSON.
Use double quotes for all JSON keys and string values.
Ensure the JSON can be parsed directly by Python json.loads().
"""

    return f"""You are the Review Agent for Aria Freelancer.

Your job is quality assurance only. Do not rewrite the content.
Evaluate the generated package against the client brief and approved plan.

{strict_instruction}

CLIENT BRIEF:
{job.get('brief', '').strip()}

CONTENT CONTEXT:
{json.dumps({
    'platform': job.get('platform', ''),
    'language': job.get('language', ''),
    'audience': job.get('audience', ''),
    'tone': job.get('tone', ''),
    'goal': job.get('goal', ''),
    'content_type': job.get('content_type', ''),
    'brand_voice': job.get('brand_voice', ''),
    'constraints': job.get('constraints', []),
    'deliverables': job.get('deliverables', [])
}, ensure_ascii=False, indent=2)}

APPROVED CONTENT PLAN:
{json.dumps(plan, ensure_ascii=False, indent=2)}

GENERATED CONTENT:
{content}

REVIEW CRITERIA:
1. Brief alignment.
2. Plan alignment.
3. Completeness: every requested deliverable is present.
4. Platform, language, audience and tone fit.
5. Specificity and usefulness.
6. Repetition and internal inconsistency.
7. Unsupported facts, statistics or sources.
8. For psychology/health content: no diagnosis, treatment promises or unsupported medical claims.
9. No obvious placeholder text or broken formatting.

Return ONLY valid JSON in exactly this shape:

{{
  "status": "approved",
  "score": 0,
  "issues": [
    {{
      "severity": "critical",
      "category": "string",
      "description": "string"
    }}
  ],
  "missing_deliverables": [],
  "revision_instructions": []
}}

Scoring guidance:
90-100 is normally approval territory.
75-89 requires revision when issues materially affect client readiness.
Below 75 requires revision.
A critical safety/compliance issue always requires revision regardless of score.
"""


def review_content(job, plan, content):
    """Review generated content and return a structured QA decision."""

    last_raw = ""

    for attempt in range(1, MAX_REVIEW_RETRIES + 2):

        strict = attempt > 1

        prompt = _build_prompt(
            job=job,
            plan=plan,
            content=content,
            strict=strict,
        )

        print(
            f"[Review Agent] Request attempt "
            f"{attempt}/{MAX_REVIEW_RETRIES + 1}"
        )

        raw = generate(prompt).strip()
        last_raw = raw

        review = _extract_json(raw)

        if review is None:
            print(
                f"[Review Agent] Invalid JSON on attempt {attempt}"
            )
            continue

        # Validate status
        if review.get("status") not in {
            "approved",
            "needs_revision",
        }:
            print(
                f"[Review Agent] Invalid status on attempt {attempt}"
            )
            continue

        # Validate score
        try:
            score = int(review.get("score"))
        except (TypeError, ValueError):
            print(
                f"[Review Agent] Invalid score on attempt {attempt}"
            )
            continue

        if not 0 <= score <= 100:
            print(
                f"[Review Agent] Score outside 0-100 "
                f"on attempt {attempt}"
            )
            continue

        review["score"] = score
        review.setdefault("issues", [])
        review.setdefault("missing_deliverables", [])
        review.setdefault("revision_instructions", [])
        review["reviewer"] = "aria-review-agent-v1"
        review["attempt"] = attempt

        print(
            f"[Review Agent] Valid review received "
            f"on attempt {attempt}"
        )

        return review

    raise ValueError(
        "Review Agent failed to return valid JSON "
        f"after {MAX_REVIEW_RETRIES + 1} attempts. "
        f"Last response: {last_raw[:500]}"
        )
