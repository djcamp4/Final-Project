#!/usr/bin/env python3
"""
Consistency Check — verifies scorer output is stable across N runs.

Usage:
    python3 consistency_check.py <resume_file> <job_description_file> [--runs N] [--model MODEL]

Checks:
  - Score variance ≤ 1 point
  - Confidence agreement ≥ 70%
  - Matched-requirements overlap ≥ 80%
  - Gaps overlap ≥ 70%

See references/scoring_anchors.md for threshold rationale.
"""

import sys
import os
import json
import argparse
import statistics
from pathlib import Path
from collections import Counter

# Load .env
def _load_dotenv():
    here = Path(__file__).resolve()
    for parent in [here.parent, *here.parents]:
        env_file = parent / ".env"
        if env_file.exists():
            try:
                from dotenv import load_dotenv
                load_dotenv(env_file)
                return
            except ImportError:
                for line in env_file.read_text().splitlines():
                    line = line.strip()
                    if line and not line.startswith("#") and "=" in line:
                        k, _, v = line.partition("=")
                        os.environ.setdefault(k.strip(), v.strip().strip('"').strip("'"))
                return

_load_dotenv()

try:
    import anthropic
except ImportError:
    print("Error: anthropic package not installed. Run: pip install anthropic")
    sys.exit(1)

# Reuse scoring logic from score.py
sys.path.insert(0, str(Path(__file__).parent))
from score import load_prompt, score_resume, DIMENSION_WEIGHTS


DEFAULT_MODEL = "claude-sonnet-4-6"
DEFAULT_RUNS = 5


# ---------------------------------------------------------------------------
# Overlap helpers
# ---------------------------------------------------------------------------

def _normalize(items: list[str]) -> set[str]:
    return {s.lower().strip() for s in items if s.strip()}


def list_overlap(lists: list[list[str]]) -> float:
    """
    Fraction of unique items that appear in ≥ 80% of runs.
    Returns 1.0 if all lists are empty.
    """
    if not any(lists):
        return 1.0
    all_items = set()
    for lst in lists:
        all_items |= _normalize(lst)
    if not all_items:
        return 1.0
    threshold = 0.8 * len(lists)
    counts = Counter()
    for lst in lists:
        for item in _normalize(lst):
            counts[item] += 1
    passing = sum(1 for item in all_items if counts[item] >= threshold)
    return passing / len(all_items)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(description="Check scorer consistency across multiple runs")
    parser.add_argument("resume_file", help="Path to a clean_resume_*.txt file")
    parser.add_argument("job_description", help="Path to job description text file")
    parser.add_argument("--runs", type=int, default=DEFAULT_RUNS, help=f"Number of runs (default: {DEFAULT_RUNS})")
    parser.add_argument("--model", default=DEFAULT_MODEL)
    args = parser.parse_args()

    resume_path = Path(args.resume_file).resolve()
    jd_path = Path(args.job_description).resolve()

    if not resume_path.exists():
        print(f"Error: {resume_path} not found")
        sys.exit(1)
    if not jd_path.exists():
        print(f"Error: {jd_path} not found")
        sys.exit(1)

    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        print("Error: ANTHROPIC_API_KEY not set.")
        sys.exit(1)

    system_prompt, prompt_sha = load_prompt()
    resume_text = resume_path.read_text(encoding="utf-8")
    jd_text = jd_path.read_text(encoding="utf-8")

    print(f"Consistency check: {resume_path.name}")
    print(f"  Model:  {args.model}")
    print(f"  Runs:   {args.runs}")
    print(f"  Prompt: {prompt_sha[:16]}...\n")

    client = anthropic.Anthropic(api_key=api_key)
    results = []

    for i in range(1, args.runs + 1):
        print(f"  Run {i}/{args.runs} ...", end=" ", flush=True)
        try:
            r = score_resume(
                client=client,
                resume_text=resume_text,
                jd_text=jd_text,
                system_prompt=system_prompt,
                prompt_sha=prompt_sha,
                model=args.model,
            )
            results.append(r)
            dims = r.get("dimensions", {})
            dim_str = " ".join(f"{k[:4]}={v}" for k, v in dims.items())
            print(f"score={r.get('score','?')} ({r.get('weighted_score','?')})  [{dim_str}]")
        except Exception as exc:
            print(f"ERROR: {exc}")

    if not results:
        print("\nNo successful runs — cannot evaluate consistency.")
        sys.exit(1)

    # ---------------------------------------------------------------------------
    # Analysis
    # ---------------------------------------------------------------------------
    scores = [r["score"] for r in results if isinstance(r.get("score"), int)]
    weighted_scores = [r["weighted_score"] for r in results if isinstance(r.get("weighted_score"), float)]
    confidences = [r.get("confidence", "") for r in results]
    matched_lists = [r.get("matched_requirements", []) for r in results]
    gap_lists = [r.get("gaps", []) for r in results]

    # Per-dimension variance
    dim_variances = {}
    for dim in DIMENSION_WEIGHTS:
        dim_scores = [r["dimensions"][dim] for r in results if isinstance(r.get("dimensions", {}).get(dim), int)]
        dim_variances[dim] = (max(dim_scores) - min(dim_scores)) if len(dim_scores) > 1 else 0

    score_variance = (max(scores) - min(scores)) if len(scores) > 1 else 0
    weighted_variance = round(max(weighted_scores) - min(weighted_scores), 3) if len(weighted_scores) > 1 else 0
    most_common_conf = Counter(confidences).most_common(1)[0][0] if confidences else "?"
    conf_agreement = confidences.count(most_common_conf) / len(confidences) if confidences else 0
    matched_overlap = list_overlap(matched_lists)
    gap_overlap = list_overlap(gap_lists)

    checks = {
        "composite_score_variance":  (score_variance,    "≤ 1",    score_variance <= 1),
        "weighted_score_variance":   (weighted_variance,  "≤ 1.0",  weighted_variance <= 1.0),
        "confidence_agreement":      (conf_agreement,     "≥ 0.70", conf_agreement >= 0.70),
        "matched_requirements_overlap": (matched_overlap, "≥ 0.80", matched_overlap >= 0.80),
        "gap_overlap":               (gap_overlap,        "≥ 0.70", gap_overlap >= 0.70),
    }
    for dim, var in dim_variances.items():
        checks[f"dim_variance_{dim}"] = (var, "≤ 1", var <= 1)

    print("\n=== Consistency Report ===")
    print(f"  Composite scores:  {scores}  (mean={statistics.mean(scores):.2f}, range={score_variance})")
    if weighted_scores:
        print(f"  Weighted scores:   {[round(w,3) for w in weighted_scores]}  (range={weighted_variance})")
    print(f"  Confidence:        {dict(Counter(confidences))}")
    print(f"\n  Per-dimension variance (max–min across {len(results)} runs):")
    for dim, var in dim_variances.items():
        status = "ok" if var <= 1 else "FAIL"
        print(f"    {dim:<24}  range={var}  [{status}]")

    print()
    all_pass = True
    for metric, (value, threshold, ok) in checks.items():
        status = "PASS" if ok else "FAIL"
        if not ok:
            all_pass = False
        fmt = f"{value:.2f}" if isinstance(value, float) else str(value)
        print(f"  [{status}] {metric}: {fmt} (threshold {threshold})")

    print()
    if all_pass:
        print("Result: ALL CHECKS PASSED — prompt is stable.")
    else:
        print("Result: CHECKS FAILED — review prompts/score.md for ambiguity.")
        sys.exit(1)


if __name__ == "__main__":
    main()
