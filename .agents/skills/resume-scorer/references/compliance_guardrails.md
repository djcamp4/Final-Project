# Compliance Guardrails

This document defines the legal and ethical constraints for the resume
scoring pipeline. These rules are sourced from U.S. EEOC guidelines and
general fair-hiring best practices.

---

## Protected characteristics — never score on these

The following attributes must NEVER influence the score, the gap analysis,
or the summary rationale:

| Category | Examples |
|----------|---------|
| Race / color | Name inference, school demographics |
| National origin | Country of origin, accent, visa status |
| Sex / gender | Name-based inference, pronoun use, maternity leave |
| Age | Graduation year inference, length of career |
| Disability | Physical limitations, medical history |
| Religion | Religious institution affiliations |
| Marital / family status | Spouse mentions, parental leave gaps |
| Military status | Beyond directly relevant skills/clearances |

---

## Employment gaps

- A gap in employment history is NOT a negative signal unless the job
  description explicitly requires continuous, uninterrupted experience
  (e.g., security clearance recency requirements).
- Do not speculate about the reason for a gap.

---

## School / credential bias

- Do not treat Ivy League or brand-name universities as inherently superior
  unless the job description explicitly requires a specific credential tier.
- Assess the qualification (degree, certification), not the granting institution.

---

## Address / location inference

- Do not infer demographics from a candidate's city, zip code, or region.
- Geographic preferences expressed in the job description (e.g., "must be
  within 50 miles") are legitimate — flag location as a potential gap only
  if it is an explicit hard requirement in the JD.

---

## Model output auditing

Every scorer output includes:
- `prompt_sha256`: hash of the system prompt at time of scoring
- `confidence`: self-reported confidence level

These fields allow reviewers to detect prompt drift over time and identify
low-confidence decisions that warrant human review.

---

## Human-in-the-loop requirement

Scores of **2 or below** MUST be reviewed by a human recruiter before any
rejection decision is communicated to the candidate. The AI score is advisory,
not dispositive.
