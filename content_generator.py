import json
from ai_router import generate


def generate_content(job, plan):
    brief = job.get("brief", "").strip()
    deliverables = job.get("deliverables", [])

    if not brief:
        raise ValueError("Job must contain a non-empty brief.")

    prompt = f"""You are the Content Generator for Aria Freelancer.

Your job is to turn an approved Content Plan into a complete,
client-ready content package.

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
    "constraints": job.get("constraints", [])
}, ensure_ascii=False, indent=2)}

APPROVED CONTENT PLAN:
{json.dumps(plan, ensure_ascii=False, indent=2)}

REQUIRED DELIVERABLES:
{json.dumps(deliverables, ensure_ascii=False, indent=2)}

GENERATION RULES:
1. Follow the approved Content Plan.
2. Do not create a different strategy or replace the plan.
3. Complete every requested deliverable.
4. Keep the content natural, specific and non-repetitive.
5. Match the requested platform, audience, language and tone.
6. Never invent statistics, sources or factual claims.
7. For psychology/health content, avoid diagnosis, treatment promises
   and unsupported medical claims.
8. Make the result directly usable by the client.
9. Clearly organize the final result with Markdown headings.
10. Return ONLY the final content package.

Generate the complete client-ready package now.
"""

    return generate(prompt).strip()
