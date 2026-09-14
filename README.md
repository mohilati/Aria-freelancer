# Aria Freelancer v1

Low-cost AI content freelancer for Persian-speaking small businesses.

## Service
A client provides a business brief. Aria produces post ideas, captions, a content calendar, and story ideas.

## Workflow
1. Put a client job in `jobs/*.json`.
2. GitHub Actions runs Aria.
3. Aria writes the deliverable to `outputs/`.
4. A human reviews it before delivery.

## Cost strategy
Use a Gemini API model available on the account's free tier and GitHub Actions. Do not add paid billing before real revenue.

## Human-controlled
Payment, client accounts, identity verification, and final delivery approval remain human-controlled.
