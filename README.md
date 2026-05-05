# Applicant Scoring with Agentic AI

A two-stage pipeline that extracts resume text and scores it against a job
description using the Claude API.

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

## Setup

```bash
pip install -r requirements.txt
```

Create a `.env` file at the repo root with your Anthropic API key:
```
ANTHROPIC_API_KEY=sk-ant-...
```
Get your key at [console.anthropic.com](https://console.anthropic.com) → API Keys.

## Browser UI (recommended)

```bash
python3 server.py
# Open http://localhost:5001
```

Upload resumes in the left panel, paste a job description, and click **Start Matching Run**. The resume extractor runs in the browser first, then Claude scores each file that passes.

> If port 5001 is taken, set a different port: `PORT=5002 python3 server.py`

## Command-line

```bash
# Stage 1 — extract (no AI)
python3 .agents/skills/resume-extractor/scripts/extract.py assets/

# Stage 2 — score (Claude API)
python3 .agents/skills/resume-scorer/scripts/score.py \
    assets/extracted/ job_description.txt

# Consistency check (run after any prompt changes)
python3 .agents/skills/resume-scorer/scripts/consistency_check.py \
    assets/extracted/clean_resume_jane_smith.txt \
    job_description.txt
```

## Project structure

```
.agents/skills/
├── resume-extractor/     Stage 1 — text extraction (no AI)
└── resume-scorer/        Stage 2 — LLM scoring (Claude API)
    ├── prompts/score.md                System prompt (SHA-locked)
    └── references/
        ├── compliance_guardrails.md    Legal/bias rules
        └── scoring_anchors.md         Calibration guide
app/
    talent_match_suite.html   Browser UI
assets/
    sample_resumes/           Input resumes
    extracted/                Cleaned text + JSON scores
job_description.txt           Target job description
server.py                     Local server (serves UI, proxies API calls)
requirements.txt
```
