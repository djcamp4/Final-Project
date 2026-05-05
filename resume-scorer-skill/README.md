# resume-scorer skill

Stage 2 of the Applicant Scoring pipeline. Takes clean `.txt` files from
the `resume-extractor` skill and scores each one against a job description
using a locked LLM rubric.

## Quick start

```bash
# 1. Run hw4 resume-extractor first
python3 .agents/skills/resume-extractor/scripts/extract.py assets/

# 2. Score the clean output
python3 .agents/skills/resume-scorer/scripts/score.py \
    assets/extracted/ \
    "Senior Backend Engineer: 5+ yrs Python, Django, PostgreSQL required..."

# 3. Open the ranked report
open assets/extracted/scored/scoring_report.csv
```

## Pipeline

```
raw uploads (PDF/DOCX/HTML)
      │
      ▼
resume-extractor            ← hw4-DanCampbell skill
  • strips hidden text
  • detects injection
  • classifies: extract / review / refuse
  • outputs: clean .txt + extraction_report.csv
      │
      ▼  (extract-action files only; review needs human sign-off)
resume-scorer               ← this skill
  • locked system prompt (prompts/score.md)
  • temperature = 0 for determinism
  • weighted math done in script, not by model
  • outputs: .score.json per file + scoring_report.csv
      │
      ▼
recruiter reviews ranked shortlist
```

## Consistency guarantee

The scoring prompt (`prompts/score.md`) is the single source of truth.
Its SHA-256 is stamped into every `.score.json` output. If you change
the prompt, re-run the full batch — mixed prompt versions in one CSV
are not comparable.

Run `scripts/consistency_check.py` after any prompt change to verify
scores are stable (target: range ≤ 1 point on any dimension across 3 runs).

## Environment

```bash
pip install anthropic
export ANTHROPIC_API_KEY=sk-ant-...
```

## File structure

```
.agents/skills/resume-scorer/
├── SKILL.md                       ← skill description (Claude Code picks this up)
├── README.md                      ← this file
├── prompts/
│   └── score.md                   ← locked LLM system prompt
├── references/
│   └── scoring_anchors.md         ← human-readable scoring guide for spot-checks
└── scripts/
    ├── score.py                   ← main scoring script
    └── consistency_check.py       ← variance testing after prompt changes
```
