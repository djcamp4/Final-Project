#!/usr/bin/env python3
"""
Talent Match Suite — local server
Supports Anthropic, OpenAI, and Google Gemini.

Usage:
    python3 server.py
    Open http://localhost:5001

API keys go in .env — only providers with a key configured will appear in the UI.
    ANTHROPIC_API_KEY=sk-ant-...
    OPENAI_API_KEY=sk-...
    GOOGLE_API_KEY=...
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

PROVIDERS = {
    "anthropic": {
        "label":   "Anthropic — Claude Sonnet",
        "key_env": "ANTHROPIC_API_KEY",
        "model":   "claude-sonnet-4-6",
    },
    "openai": {
        "label":   "OpenAI — GPT-4o",
        "key_env": "OPENAI_API_KEY",
        "model":   "gpt-4o",
    },
    "google": {
        "label":   "Google — Gemini 1.5 Pro",
        "key_env": "GOOGLE_API_KEY",
        "model":   "gemini-1.5-pro",
    },
}


# ---------------------------------------------------------------------------
# .env loader
# ---------------------------------------------------------------------------

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
    from flask import Flask, request, jsonify, send_from_directory
except ImportError:
    print("Error: flask not installed. Run: pip3 install -r requirements.txt")
    sys.exit(1)

app = Flask(__name__)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def get_available_providers():
    """Return providers that have an API key configured."""
    return [
        {"id": pid, "label": p["label"]}
        for pid, p in PROVIDERS.items()
        if os.environ.get(p["key_env"])
    ]


def parse_llm_json(raw: str) -> dict:
    raw = raw.strip()
    if raw.startswith("```"):
        lines = raw.splitlines()
        raw = "\n".join(lines[1:-1] if lines[-1].strip() == "```" else lines[1:])
    return json.loads(raw)


# ---------------------------------------------------------------------------
# Provider scoring functions
# ---------------------------------------------------------------------------

def score_anthropic(prompt_text, user_msg, model):
    try:
        import anthropic as _anthropic
    except ImportError:
        raise RuntimeError("anthropic not installed — run: pip3 install anthropic")

    client   = _anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])
    response = client.messages.create(
        model=model,
        max_tokens=1024,
        temperature=0,
        system=[{
            "type": "text",
            "text": prompt_text,
            "cache_control": {"type": "ephemeral"},
        }],
        messages=[{"role": "user", "content": user_msg}],
    )
    raw   = response.content[0].text
    usage = response.usage
    meta  = {
        "input_tokens":                usage.input_tokens,
        "output_tokens":               usage.output_tokens,
        "cache_creation_input_tokens": getattr(usage, "cache_creation_input_tokens", 0),
        "cache_read_input_tokens":     getattr(usage, "cache_read_input_tokens", 0),
    }
    return raw, meta


def score_openai(prompt_text, user_msg, model):
    try:
        from openai import OpenAI
    except ImportError:
        raise RuntimeError("openai not installed — run: pip3 install openai")

    client   = OpenAI(api_key=os.environ["OPENAI_API_KEY"])
    response = client.chat.completions.create(
        model=model,
        temperature=0,
        messages=[
            {"role": "system", "content": prompt_text},
            {"role": "user",   "content": user_msg},
        ],
    )
    raw   = response.choices[0].message.content
    usage = response.usage
    meta  = {
        "input_tokens":  usage.prompt_tokens,
        "output_tokens": usage.completion_tokens,
    }
    return raw, meta


def score_google(prompt_text, user_msg, model):
    try:
        import google.generativeai as genai
    except ImportError:
        raise RuntimeError("google-generativeai not installed — run: pip3 install google-generativeai")

    genai.configure(api_key=os.environ["GOOGLE_API_KEY"])
    gmodel   = genai.GenerativeModel(model, system_instruction=prompt_text)
    response = gmodel.generate_content(
        user_msg,
        generation_config=genai.GenerationConfig(temperature=0),
    )
    raw  = response.text
    meta = {
        "input_tokens":  response.usage_metadata.prompt_token_count,
        "output_tokens": response.usage_metadata.candidates_token_count,
    }
    return raw, meta


SCORE_FNS = {
    "anthropic": score_anthropic,
    "openai":    score_openai,
    "google":    score_google,
}


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------

@app.route("/")
def index():
    return send_from_directory(APP_DIR, "talent_match_suite.html")


@app.route("/api/providers")
def api_providers():
    return jsonify({"providers": get_available_providers()})


@app.route("/api/score", methods=["POST"])
def api_score():
    data        = request.get_json(force=True) or {}
    resume_text = (data.get("resume_text") or "").strip()
    jd_text     = (data.get("jd_text") or "").strip()
    # Provider is set in .env (AI_PROVIDER=anthropic/openai/google)
    # Falls back to the first provider that has a key configured.
    default = os.environ.get("AI_PROVIDER", "anthropic").lower()
    provider_id = (data.get("provider") or default).lower()

    if not resume_text or not jd_text:
        return jsonify({"error": "resume_text and jd_text are required"}), 400

    if provider_id not in PROVIDERS:
        return jsonify({"error": f"Unknown provider: {provider_id}"}), 400

    provider = PROVIDERS[provider_id]
    if not os.environ.get(provider["key_env"]):
        return jsonify({"error": f"{provider['key_env']} not set in .env"}), 500

    if not PROMPT_PATH.exists():
        return jsonify({"error": f"System prompt not found: {PROMPT_PATH}"}), 500

    prompt_text = PROMPT_PATH.read_text(encoding="utf-8")
    prompt_sha  = hashlib.sha256(PROMPT_PATH.read_bytes()).hexdigest()

    user_msg = (
        "## Job Description\n\n"
        + jd_text
        + "\n\n---\n\n## Resume\n\n"
        + resume_text
    )

    try:
        raw, usage_meta = SCORE_FNS[provider_id](prompt_text, user_msg, provider["model"])
    except Exception as exc:
        return jsonify({"error": str(exc)}), 502

    try:
        result = parse_llm_json(raw)
    except json.JSONDecodeError as exc:
        return jsonify({"error": f"Model returned invalid JSON: {exc}", "raw": raw}), 502

    result["prompt_sha256"] = prompt_sha

    dims      = result.get("dimensions", {})
    raw_score = sum(dims.get(k, 0) * w for k, w in DIMENSION_WEIGHTS.items())
    result["score"]          = round(raw_score)
    result["weighted_score"] = round(raw_score, 3)
    result["match_percent"]  = round(raw_score / 5 * 100)

    result["_meta"] = {
        "provider":    provider_id,
        "model":       provider["model"],
        "temperature": 0,
        **usage_meta,
    }

    return jsonify(result)


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    port      = int(os.environ.get("PORT", 5001))
    available = get_available_providers()
    print(f"Talent Match Suite → http://localhost:{port}")
    print(f"Providers available: {', '.join(p['label'] for p in available) or 'none — check .env'}")
    # Use 0.0.0.0 so the server is reachable inside Docker / Cloud Run.
    # Locally it still binds to all interfaces but only responds on localhost.
    app.run(host="0.0.0.0", port=port, debug=False)
