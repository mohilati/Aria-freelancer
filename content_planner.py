import json
from ai_router import generate

def build_plan(job):
    brief = job.get("brief", "").strip()
    if not brief:
        raise ValueError("Job must contain a non-empty brief.")
    context = {k: job.get(k, "") for k in (
        "platform", "language", "audience", "tone", "goal",
        "content_type", "brand_voice"
    )}
    context["constraints"] = job.get("constraints", [])
    prompt = f"""You are the Content Planner for Aria Freelancer.
CLIENT BRIEF:
{brief}
CONTEXT:
{json.dumps(context, ensure_ascii=False, indent=2)}

Create a practical content plan.
Return ONLY valid JSON with exactly these keys:
{{"content_goal":"...","audience_angle":"...","core_message":"...","content_pillars":["..."],"formats":["..."],"hooks":["..."],"call_to_action":"...","calendar":[{{"day":1,"topic":"...","format":"...","hook":"..."}}]}}
Rules: match platform/audience/tone/goal; be specific and non-repetitive; never invent statistics, sources, facts or claims; for health content avoid diagnosis, treatment promises and unsupported medical claims.
"""
    raw = generate(prompt).strip()
    if raw.startswith("```"):
        raw = raw.replace("```json", "", 1).replace("```", "", 1).strip()
    plan = json.loads(raw)
    plan["planner"] = "aria-content-planner-v1"
    return plan
