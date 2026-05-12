#!/usr/bin/env python3
"""
Stage 2 — Resume Scorer (LLM, Claude API)
Scores each extracted resume against a job description.

Usage:
    python3 score.py <extracted_dir> <job_description_file> [--model MODEL]

Outputs:
    <extracted_dir>/scores/score_<stem>.json  — one per resume
    <extracted_dir>/scores/summary.json       — all results combined

Requires:
    ANTHROPIC_API_KEY in environment or .env file
"""

import sys
import os
import json
import hashlib
import argparse
from pathlib import Path
from datetime import datetime, timezone

# Load .env from repo root (walk up from this script)
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
                # Manually parse a minimal .env
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


# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------

SKILLS_DIR = Path(__file__).resolve().parents[1]
PROMPT_PATH = SKILLS_DIR / "prompts" / "score.md"
DEFAULT_MODEL = "claude-sonnet-4-6"

DIMENSION_WEIGHTS = {
    "required_skills":      0.25,
    "experience_and_tenure": 0.25,
    "achievements":         0.20,
    "responsibilities":     0.20,
    "preferred_skills":     0.10,
}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def sha256_file(path: Path) -> str:
    h = hashlib.sha256(path.read_bytes())
    return h.hexdigest()


def sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode()).hexdigest()


def load_prompt() -> tuple[str, str]:
    """Return (prompt_text, sha256)."""
    if not PROMPT_PATH.exists():
        raise FileNotFoundError(f"System prompt not found: {PROMPT_PATH}")
    text = PROMPT_PATH.read_text(encoding="utf-8")
    return text, sha256_file(PROMPT_PATH)


def parse_llm_json(raw: str) -> dict:
    """Extract JSON from LLM response (strip accidental markdown fences)."""
    raw = raw.strip()
    if raw.startswith("```"):
        lines = raw.splitlines()
        raw = "\n".join(lines[1:-1] if lines[-1].strip() == "```" else lines[1:])
    return json.loads(raw)


# ---------------------------------------------------------------------------
# Scoring
# ---------------------------------------------------------------------------

def compute_weighted_score(dimensions: dict) -> tuple[int, float]:
    """Return (rounded integer score, raw float) from dimension scores."""
    raw = sum(dimensions[k] * w for k, w in DIMENSION_WEIGHTS.items())
    return round(raw), round(raw, 3)


def score_resume(
    client: anthropic.Anthropic,
    resume_text: str,
    jd_text: str,
    system_prompt: str,
    prompt_sha: str,
    model: str,
) -> dict:
    """Call the Claude API and return the parsed score dict."""

    user_message = (
        "## Job Description\n\n"
        + jd_text.strip()
        + "\n\n---\n\n## Resume\n\n"
        + resume_text.strip()
    )

    response = client.messages.create(
        model=model,
        max_tokens=1024,
        temperature=0,
        system=[
            {
                "type": "text",
                "text": system_prompt,
                "cache_control": {"type": "ephemeral"},
            }
        ],
        messages=[{"role": "user", "content": user_message}],
    )

    raw_text = response.content[0].text
    result = parse_llm_json(raw_text)
    result["prompt_sha256"] = prompt_sha

    # Compute weighted composite — math lives here, not in the prompt
    dims = result.get("dimensions", {})
    score, weighted_score = compute_weighted_score(dims)
    result["score"] = score
    result["weighted_score"] = weighted_score

    usage = response.usage
    result["_meta"] = {
        "model": model,
        "temperature": 0,
        "input_tokens": usage.input_tokens,
        "output_tokens": usage.output_tokens,
        "cache_creation_input_tokens": getattr(usage, "cache_creation_input_tokens", 0),
        "cache_read_input_tokens": getattr(usage, "cache_read_input_tokens", 0),
        "scored_at": datetime.now(timezone.utc).isoformat(),
    }

    return result


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(description="Score resumes against a job description")
    parser.add_argument("extracted_dir", help="Directory containing clean_resume_*.txt files")
    parser.add_argument("job_description", help="Path to job description text file")
    parser.add_argument("--model", default=DEFAULT_MODEL, help=f"Claude model (default: {DEFAULT_MODEL})")
    parser.add_argument("--dry-run", action="store_true", help="Print what would be done without calling the API")
    args = parser.parse_args()

    extracted_dir = Path(args.extracted_dir).resolve()
    jd_path = Path(args.job_description).resolve()

    if not extracted_dir.is_dir():
        print(f"Error: {extracted_dir} is not a directory")
        sys.exit(1)
    if not jd_path.exists():
        print(f"Error: job description not found: {jd_path}")
        sys.exit(1)

    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key and not args.dry_run:
        print("Error: ANTHROPIC_API_KEY not set. Add it to .env or export it.")
        sys.exit(1)

    system_prompt, prompt_sha = load_prompt()
    jd_text = jd_path.read_text(encoding="utf-8")
    jd_sha = sha256_text(jd_text)

    resumes = sorted(extracted_dir.glob("clean_resume_*.txt"))
    if not resumes:
        print(f"No clean_resume_*.txt files found in {extracted_dir}")
        sys.exit(0)

    scores_dir = extracted_dir / "scores"
    scores_dir.mkdir(exist_ok=True)

    print(f"Scoring {len(resumes)} resume(s) with {args.model}")
    print(f"  System prompt SHA: {prompt_sha[:16]}...")
    print(f"  JD SHA:            {jd_sha[:16]}...\n")

    if args.dry_run:
        for r in resumes:
            print(f"  [dry-run] would score {r.name}")
        return

    client = anthropic.Anthropic(api_key=api_key)
    all_results = []

    for resume_path in resumes:
        resume_text = resume_path.read_text(encoding="utf-8")
        stem = resume_path.stem  # e.g. clean_resume_jane
        candidate_name = stem.replace("clean_resume_", "").replace("_", " ").title()

        print(f"  Scoring: {resume_path.name} ...", end=" ", flush=True)
        try:
            result = score_resume(
                client=client,
                resume_text=resume_text,
                jd_text=jd_text,
                system_prompt=system_prompt,
                prompt_sha=prompt_sha,
                model=args.model,
            )
            result["candidate"] = candidate_name
            result["resume_file"] = resume_path.name
            result["jd_sha256"] = jd_sha

            out_path = scores_dir / f"score_{stem.replace('clean_resume_', '')}.json"
            out_path.write_text(json.dumps(result, indent=2), encoding="utf-8")

            score = result.get("score", "?")
            weighted = result.get("weighted_score", "?")
            conf = result.get("confidence", "?")
            dims = result.get("dimensions", {})
            dim_str = "  ".join(f"{k[:4]}={v}" for k, v in dims.items())
            cache_read = result["_meta"].get("cache_read_input_tokens", 0)
            cache_tag = f" [cache hit: {cache_read} tok]" if cache_read else ""
            print(f"score={score}/5 ({weighted})  {conf}  [{dim_str}]{cache_tag}")
            all_results.append(result)

        except Exception as exc:
            print(f"ERROR: {exc}")
            all_results.append({"resume_file": resume_path.name, "error": str(exc)})

    # Write combined summary
    summary = {
        "scored_at": datetime.now(timezone.utc).isoformat(),
        "model": args.model,
        "prompt_sha256": prompt_sha,
        "jd_sha256": jd_sha,
        "results": all_results,
    }
    summary_path = scores_dir / "summary.json"
    summary_path.write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print(f"\nSummary written to {summary_path}")

    # Print leaderboard
    scored = [r for r in all_results if "score" in r]
    if scored:
        scored.sort(key=lambda r: r.get("weighted_score", 0), reverse=True)
        print("\n=== Leaderboard ===")
        dim_keys = list(DIMENSION_WEIGHTS.keys())
        header = f"  {'Name':<24}  {'Score':>5}  {'Weighted':>8}  " + \
                 "  ".join(f"{k[:4]:>4}" for k in dim_keys)
        print(header)
        print("  " + "-" * (len(header) - 2))
        for r in scored:
            name = r.get("candidate", r["resume_file"])[:24]
            dims = r.get("dimensions", {})
            dim_vals = "  ".join(f"{dims.get(k,'?'):>4}" for k in dim_keys)
            print(f"  {name:<24}  {r['score']:>5}  {r.get('weighted_score',0):>8.3f}  {dim_vals}")


if __name__ == "__main__":
    main()
