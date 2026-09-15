# Aria Freelancer v2

AI content freelancer with automatic AI provider failover.

Provider order:
1. Gemini
2. OpenRouter
3. Cerebras

Required GitHub Actions secrets:
- GEMINI_API_KEY
- OPENROUTER_API_KEY
- CEREBRAS_API_KEY

Optional job fields:
platform, language, audience, tone, goal, content_type, brand_voice, constraints, review_required.

The original brief/deliverables/status/output workflow remains compatible.
