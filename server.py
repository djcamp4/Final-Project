#!/usr/bin/env python3
"""
Talent Match Suite — local server
Serves the browser UI and proxies LLM scoring to Anthropic.

Usage:
    python3 server.py
    Open http://localhost:5000
"""

import json
import os
import sys
import hashlib
from pathlib import Path

BASE        = Path(__file__).resolve().parent
PROMPT_PATH = BASE / ".agents/skills/resume-scorer/prompts/score.md"
APP_DIR     = BASE / "app"

DIMENSION_WEIGHTS = {
    "required_skills":       0.25,
    "experience_and_tenure": 0.25,
    "achievements":          0.20,
    "responsibilities":      0.20,
    "preferred_skills":      0.10,
}


def _load_dotenv():
    for parent in [BASE, *BASE.parents]:
        env_file = parent / ".env"
        if env_file.exists():
            try:
                from dotenv import load_dotenv
                load_dotenv(env_file, override=True)
            except ImportError:
                for line in env_file.read_text().splitlines():
                    line = line.strip()
                    if line and not line.startswith("#") and "=" in line:
                        k, _, v = line.partition("=")
                        os.environ.setdefault(k.strip(), v.strip().strip('"').strip("'"))
            return


_load_dotenv()

try:
    import anthropic as _anthropic
except ImportError:
    print("Error: anthropic package not installed. Run: pip install anthropic flask")
    sys.exit(1)

try:
    from flask import Flask, request, jsonify, send_from_directory
except ImportError:
    print("Error: flask not installed. Run: pip install anthropic flask")
    sys.exit(1)

app = Flask(__name__)


@app.route("/")
def index():
    return send_from_directory(APP_DIR, "talent_match_suite.html")


@app.route("/api/score", methods=["POST"])
def api_score():
    data        = request.get_json(force=True) or {}
    resume_text = (data.get("resume_text") or "").strip()
    jd_text     = (data.get("jd_text") or "").strip()

    if not resume_text or not jd_text:
        return jsonify({"error": "resume_text and jd_text are required"}), 400

    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        return jsonify({"error": "ANTHROPIC_API_KEY not set — add it to .env"}), 500

    if not PROMPT_PATH.exists():
        return jsonify({"error": f"System prompt not found: {PROMPT_PATH}"}), 500

    prompt_text = PROMPT_PATH.read_text(encoding="utf-8")
    prompt_sha  = hashlib.sha256(PROMPT_PATH.read_bytes()).hexdigest()

    client   = _anthropic.Anthropic(api_key=api_key)
    user_msg = (
        "## Job Description\n\n"
        + jd_text
        + "\n\n---\n\n## Resume\n\n"
        + resume_text
    )

    try:
        response = client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=1024,
            temperature=0,
            system=[{
                "type": "text",
                "text": prompt_text,
                "cache_control": {"type": "ephemeral"},
            }],
            messages=[{"role": "user", "content": user_msg}],
        )
    except Exception as exc:
        return jsonify({"error": str(exc)}), 502

    raw = response.content[0].text.strip()
    if raw.startswith("```"):
        lines = raw.splitlines()
        raw = "\n".join(lines[1:-1] if lines[-1].strip() == "```" else lines[1:])

    try:
        result = json.loads(raw)
    except json.JSONDecodeError as exc:
        return jsonify({"error": f"Model returned invalid JSON: {exc}", "raw": raw}), 502

    result["prompt_sha256"] = prompt_sha

    dims      = result.get("dimensions", {})
    raw_score = sum(dims.get(k, 0) * w for k, w in DIMENSION_WEIGHTS.items())
    result["score"]          = round(raw_score)
    result["weighted_score"] = round(raw_score, 3)
    result["match_percent"]  = round(raw_score / 5 * 100)

    usage = response.usage
    result["_meta"] = {
        "model":                       "claude-sonnet-4-6",
        "temperature":                 0,
        "input_tokens":                usage.input_tokens,
        "output_tokens":               usage.output_tokens,
        "cache_creation_input_tokens": getattr(usage, "cache_creation_input_tokens", 0),
        "cache_read_input_tokens":     getattr(usage, "cache_read_input_tokens", 0),
    }

    return jsonify(result)


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    print(f"Talent Match Suite → http://localhost:{port}")
    app.run(host="127.0.0.1", port=port, debug=False)
