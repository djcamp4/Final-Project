# Applicant Scoring with Agentic AI

A two-stage pipeline that extracts resume text and scores it against a job
description. Supports Anthropic (Claude), OpenAI (GPT-4o),
and Google Gemini.

---

## Pipeline overview

```
assets/
├── sample_resumes/     ← drop PDF, DOCX, or TXT resumes here
│   ├── jane_smith.txt
│   └── bob_jones.txt
└── extracted/          ← auto-created by Stage 1
    ├── clean_resume_jane_smith.txt
    ├── clean_resume_bob_jones.txt
    └── scores/         ← auto-created by Stage 2
        ├── score_jane_smith.json
        ├── score_bob_jones.json
        └── summary.json
```

---

## Setup

```bash
pip3 install -r requirements.txt
```

Create a `.env` file at the repo root with at least one API key:

```
ANTHROPIC_API_KEY=sk-ant-...   # https://console.anthropic.com
OPENAI_API_KEY=sk-...          # https://platform.openai.com  (optional)
GOOGLE_API_KEY=...             # https://aistudio.google.com  (optional)
```

Only providers with a key configured will appear in the browser UI.

---

## Browser UI (recommended)

```bash
PORT=5001 python3 server.py
# Open http://localhost:5001
```

Upload resumes in the left panel, paste a job description, choose an AI
provider, and click **Start Matching Run**. The resume extractor runs in the
browser first, then the selected AI scores each file that passes.

> Port 5000 is blocked by macOS AirPlay Receiver — use 5001 or higher.
> If 5001 is taken: `PORT=5002 python3 server.py`

---

## Command-line

```bash
# Stage 1 — extract (no AI)
python3 .agents/skills/resume-extractor/scripts/extract.py assets/

# Stage 2 — score (AI API)
python3 .agents/skills/resume-scorer/scripts/score.py \
    assets/extracted/ job_description.txt

# Consistency check (run after any prompt changes)
python3 .agents/skills/resume-scorer/scripts/consistency_check.py \
    assets/extracted/clean_resume_jane_smith.txt \
    job_description.txt
```

---

## Resume Scorer — Stage 2 detail

### Scoring dimensions

Scores are a weighted composite across five dimensions (each rated 1–5):

| Dimension | Weight | What it measures |
|-----------|--------|-----------------|
| Required Skills | 25% | Must-have technical skills and certifications |
| Experience & Tenure | 25% | Years of relevant experience and seniority |
| Achievements | 20% | Measurable accomplishments and impact |
| Responsibilities | 20% | How well past duties match the job |
| Preferred Skills | 10% | Nice-to-have skills listed in the JD |

The weighted average is the final score (shown as X.X / 5).

### Score JSON schema

```json
{
  "score": "1-5",
  "weighted_score": 3.75,
  "confidence": "low|medium|high",
  "matched_requirements": ["..."],
  "gaps": ["..."],
  "summary": "Plain-English rationale",
  "prompt_sha256": "SHA-256 of prompts/score.md",
  "candidate": "Name",
  "resume_file": "clean_resume_*.txt",
  "jd_sha256": "SHA-256 of job description",
  "_meta": {
    "provider": "anthropic|openai|google",
    "model": "claude-sonnet-4-6",
    "input_tokens": 0,
    "output_tokens": 0,
    "temperature": 0
  }
}
```

### Key files

| File | Purpose |
|------|---------|
| `.agents/skills/resume-scorer/prompts/score.md` | System prompt — SHA-stamped into every output |
| `.agents/skills/resume-scorer/references/compliance_guardrails.md` | Legal/bias rules |
| `.agents/skills/resume-scorer/references/scoring_anchors.md` | Calibration guide + consistency thresholds |

### Prompt integrity

The `prompt_sha256` field in every output lets you detect prompt drift between
scoring runs. If you edit `prompts/score.md`, run the consistency check before
using new scores in production. The scoring prompt is identical regardless of
which AI provider is selected.

### Compliance

Scores are advisory only — the pipeline never makes hire/no-hire
recommendations. Candidates scoring 2 or below must be reviewed by a human
before any rejection decision is communicated. The model is instructed never
to score on protected characteristics (age, gender, race, nationality,
disability, religion, employment gaps, school prestige, or address).

---

## Project structure

```
.agents/skills/
├── resume-extractor/               Stage 1 — deterministic text extraction
│   ├── SKILL.md
│   ├── scripts/extract.py
│   └── references/detection_rules.md
└── resume-scorer/                  Stage 2 — AI scoring
    ├── SKILL.md
    ├── prompts/score.md            System prompt (SHA-locked)
    ├── scripts/
    │   ├── score.py
    │   └── consistency_check.py
    └── references/
        ├── compliance_guardrails.md
        └── scoring_anchors.md
app/
    talent_match_suite.html         Browser UI
server.py                           Local server (serves UI, proxies API calls)
requirements.txt
INSTRUCTIONS.txt                    End-user guide
```
