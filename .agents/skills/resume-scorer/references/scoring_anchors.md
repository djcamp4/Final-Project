# Scoring Anchors — Calibration Guide

Use these examples to spot-check model output for calibration drift.
Each anchor describes what a score of that level looks like in practice.

---

## Score 5 — Exceptional match

**Profile:** Candidate meets or exceeds every listed requirement. Has the
exact technologies, years of experience, domain knowledge, and any required
certifications. The resume contains concrete accomplishments (metrics,
scale, impact) that validate the skill claims.

**Example signals:**
- "5 years Python, FastAPI, PostgreSQL" for a role requiring exactly that stack
- Led a team of the size the JD requests
- Holds the specific certification listed as required

**Expected gaps list:** empty or trivially small ("no Kubernetes cert, but
extensive Kubernetes experience documented")

---

## Score 4 — Strong match

**Profile:** Meets most hard requirements. One or two gaps exist but are
in areas that a short onboarding period or light training could bridge.
Strong accomplishments in the core responsibilities of the role.

**Example signals:**
- Has 4 of 5 required technologies; missing one that is common/learnable
- Slightly below the preferred years of experience but has equivalent scope
- No formal management title but documented team-lead experience

**Expected gaps list:** 1-2 items, each clearly trainable

---

## Score 3 — Adequate match

**Profile:** Meets the core requirements of the role (the "must-haves")
but is missing several "nice-to-have" items or has depth gaps in one key
area. Could do the job but would need a longer ramp.

**Example signals:**
- Backend engineer applying for a full-stack role; weak on frontend
- Correct domain but different technology stack (e.g., MySQL vs. PostgreSQL)
- Correct level but at a much smaller company scale than the role demands

**Expected gaps list:** 2-4 items, at least one non-trivial

---

## Score 2 — Partial match

**Profile:** Demonstrates some relevant experience but falls short of the
minimum bar in one or more hard requirements. Significant re-skilling or
domain learning would be needed.

**Example signals:**
- Junior-level background for a senior role with minimal supervision
- Related but distinct domain (data analyst for a data engineering role)
- Missing a required certification with no documented equivalent experience

**Expected gaps list:** several items including at least one hard requirement

---

## Score 1 — Poor match

**Profile:** The resume does not meaningfully satisfy the role requirements.
The candidate's background is in a different field, at a very different level,
or lacks the foundational skills the role assumes.

**Example signals:**
- Marketing professional applying for a software engineering role
- No programming experience for a coding-required position
- Administrative background for a technical research scientist role

**Expected gaps list:** most or all listed requirements

---

## Consistency check thresholds

When running `consistency_check.py`, acceptable variance across N runs:

| Metric | Acceptable |
|--------|-----------|
| Score variance | ≤ 1 point across all runs |
| Confidence agreement | ≥ 70% of runs same confidence level |
| Matched requirements overlap | ≥ 80% of items appear in ≥ 80% of runs |
| Gap overlap | ≥ 70% of items appear in ≥ 70% of runs |

If variance exceeds these thresholds, review the prompt in `prompts/score.md`
for ambiguous language.
