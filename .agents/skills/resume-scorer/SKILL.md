# resume-scorer

Stage 2 of the applicant-scoring pipeline. Takes clean `.txt` files from
the extractor and scores each one against a job description using Claude.
Only call this skill after `resume-extractor` has cleared the files —
never score a `review` or `refuse` file without human sign-off.

## When to use

- After `resume-extractor` has produced `.txt` files with `action = extract`.
- When the user wants a ranked shortlist or a match score for a batch of applicants.
- For a single candidate when the user asks "how well does this resume match?"

## When NOT to use

- On raw, unextracted files — always run the extractor first.
- On files the extractor flagged as `review` or `refuse` without human approval.
- To make a final hiring decision — the score is advisory, not dispositive.
- When the job description is absent or fewer than ~50 words.

## Inputs

- A directory of `clean_resume_*.txt` files (extractor output).
- A job description text file.
- Optional: `--model` to override the Claude model (default: claude-sonnet-4-6).

## Outputs

- `<extracted_dir>/scores/score_<name>.json` — one per candidate.
- `<extracted_dir>/scores/summary.json` — combined leaderboard.

### Score JSON schema

```json
{
  "score": 1-5,
  "confidence": "low|medium|high",
  "matched_requirements": ["..."],
  "gaps": ["..."],
  "summary": "2-3 sentence rationale",
  "prompt_sha256": "SHA-256 of prompts/score.md",
  "candidate": "Name",
  "resume_file": "clean_resume_*.txt",
  "jd_sha256": "SHA-256 of job description",
  "_meta": { "model": "...", "input_tokens": 0, "cache_read_input_tokens": 0, ... }
}
```

## Step-by-step

1. Ensure the extractor has run and `extracted/` contains `.txt` files.
2. Score the batch:
   ```
   python3 .agents/skills/resume-scorer/scripts/score.py \
       assets/extracted/ job_description.txt
   ```
3. Read `summary.json` and report the leaderboard to the user.
4. For any score ≤ 2, flag for human review before any rejection is communicated.
5. After prompt edits, run the consistency check:
   ```
   python3 .agents/skills/resume-scorer/scripts/consistency_check.py \
       assets/extracted/clean_resume_<name>.txt job_description.txt
   ```

## Prompt integrity

Every output includes `prompt_sha256` — the SHA-256 of `prompts/score.md`
at scoring time. If scores from two runs have different SHA values, the
prompt changed between runs and results are not directly comparable.

## Compliance

All scoring is constrained by `references/compliance_guardrails.md`.
The model is instructed to score only on skills, experience, and
qualifications — never on protected characteristics. Human review is
required before any rejection decision for scores ≤ 2.
