import json
from ai_router import generate


def review_content(job, plan, content):
    """Review generated content and return a structured QA decision."""
    prompt = f"""You are the Review Agent for Aria Freelancer.

Your job is quality assurance only. Do not rewrite the content.
Evaluate the generated package against the client brief and approved plan.

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
  "status": "approved" or "needs_revision",
  "score": 0,
  "issues": [
    {{"severity": "critical|major|minor", "category": "...", "description": "..."}}
  ],
  "missing_deliverables": [],
  "revision_instructions": []
}}

Scoring guidance: 90-100 is normally approval territory; 75-89 requires revision when issues materially affect client readiness; below 75 requires revision. A critical safety/compliance issue always requires revision regardless of score.
"""

    raw = generate(prompt).strip()

    try:
        review = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise ValueError(f"Review Agent returned invalid JSON: {exc}") from exc

    if review.get("status") not in {"approved", "needs_revision"}:
        raise ValueError("Review Agent returned an invalid status.")

    try:
        score = int(review.get("score"))
    except (TypeError, ValueError) as exc:
        raise ValueError("Review Agent returned an invalid score.") from exc

    if not 0 <= score <= 100:
        raise ValueError("Review Agent score must be between 0 and 100.")

    review["score"] = score
    review.setdefault("issues", [])
    review.setdefault("missing_deliverables", [])
    review.setdefault("revision_instructions", [])
    review["reviewer"] = "aria-review-agent-v1"
    return review
