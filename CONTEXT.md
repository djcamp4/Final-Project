# Project Context

This is a two-stage applicant scoring pipeline built in Claude.ai.

## Stage 1 — resume-extractor (already built)
- Source: https://github.com/djcamp4/hw4-DanCampbell
- Copy the .agents/skills/resume-extractor folder from that repo into this one
- Do not modify the hw4-DanCampbell repo

## Stage 2 — resume-scorer (files in this repo)
- Locked system prompt: .agents/skills/resume-scorer/prompts/score.md
- 5 scoring dimensions: required_skills (25%), preferred_skills (10%),
  achievements (20%), responsibilities (20%), experience_and_tenure (25%)
- Temperature = 0 for consistency
- SHA-256 of prompt stamped into every output for auditability
- Legal/bias guardrails from Resume_AI.pdf in references/compliance_guardrails.md

## Browser UI
- app/talent_match_suite.html
- Three-panel interface: Resume Input | Define Matching Run | View Ranked Results
- hw4 extractor logic ported to JavaScript runs before any LLM call
- Calls claude-sonnet-4-6 via Anthropic API for scoring

## What Claude Code should NOT do
- Modify hw4-DanCampbell repo
- Change the scoring weights
- Change the system prompt without running consistency_check.py first
- Make final hire/no-hire recommendations — output is advisory only
