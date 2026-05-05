# resume-scorer

Stage 2 of the resume scoring pipeline. Uses the Claude API to score
extracted resumes against a job description.

## Quick start

```bash
export ANTHROPIC_API_KEY=sk-ant-...

# Score all extracted resumes
python3 scripts/score.py assets/extracted/ job_description.txt

# Check consistency (run the scorer N times on one resume)
python3 scripts/consistency_check.py \
    assets/extracted/clean_resume_jane_smith.txt \
    job_description.txt --runs 5
```

## Output

Each scoring run produces:
- `assets/extracted/scores/score_<name>.json` — full result per candidate
- `assets/extracted/scores/summary.json` — combined leaderboard

### Score JSON schema

```json
{
  "score": 1-5,
  "confidence": "low|medium|high",
  "matched_requirements": ["..."],
  "gaps": ["..."],
  "summary": "Plain-English rationale",
  "prompt_sha256": "SHA-256 of prompts/score.md",
  "candidate": "Name",
  "resume_file": "clean_resume_*.txt",
  "jd_sha256": "SHA-256 of job description",
  "_meta": {
    "model": "claude-...",
    "input_tokens": 0,
    "output_tokens": 0,
    "cache_read_input_tokens": 0,
    "scored_at": "ISO-8601"
  }
}
```

## Key files

| File | Purpose |
|------|---------|
| `prompts/score.md` | System prompt — SHA-stamped into every output |
| `references/compliance_guardrails.md` | Legal/bias rules |
| `references/scoring_anchors.md` | Human calibration guide + consistency thresholds |

## Prompt integrity

The `prompt_sha256` field in every output lets you detect prompt drift
between scoring runs. If you edit `prompts/score.md`, run the consistency
check before using new scores in production.

## Install dependencies

```bash
pip install anthropic python-dotenv
```
