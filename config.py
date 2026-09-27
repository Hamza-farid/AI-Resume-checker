"""
⚙️ App configuration - every setting lives here.

Secrets are read in this order (first match wins):
  1. Streamlit Cloud secrets  (st.secrets)  -> used after deployment
  2. Local .env file          (os.environ)  -> used on your laptop

The API key variable is named `claude` (same as in your .env).
"""

import os
from pathlib import Path

from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent
load_dotenv(BASE_DIR / ".env")


def _get_secret(name: str, default: str | None = None) -> str | None:
    """Read a value from Streamlit secrets first, then from .env / environment."""
    try:
        import streamlit as st

        if name in st.secrets:
            return str(st.secrets[name])
    except Exception:
        # No secrets.toml on the laptop -> that's fine, use .env instead
        pass
    return os.getenv(name, default)


# 🔑 Secrets
CLAUDE_API_KEY = _get_secret("claude")

# 🔐 Login (all 3 must match to get in) - put these in .env / Streamlit secrets
APP_USERNAME = _get_secret("APP_USERNAME")
APP_PASSWORD = _get_secret("APP_PASSWORD")
APP_ACCESS_KEY = _get_secret("APP_ACCESS_KEY")
JWT_SECRET = _get_secret("JWT_SECRET")  # signs the login token; empty → a random one each server start
SESSION_MINUTES = int(_get_secret("SESSION_MINUTES", "10"))  # auto-logout after this many minutes
MAX_LOGIN_ATTEMPTS = 5   # wrong tries before a short lock
LOGIN_LOCK_SECONDS = 60

# 🤖 AI settings
# "auto"        → key starts with sk-ant-oat → claude_code, sk-ant-api → claude
# "claude"      → Claude API directly (needs an API key from console.anthropic.com)
# "claude_code" → Claude Code CLI (uses the `claude setup-token` subscription token)
# later: "gemini"
LLM_PROVIDER = _get_secret("LLM_PROVIDER", "auto")
CLAUDE_CODE_EXE = _get_secret("CLAUDE_CODE_EXE", "")  # empty → found automatically
CLAUDE_CODE_TIMEOUT_SEC = float(_get_secret("CLAUDE_CODE_TIMEOUT_SEC", "300"))  # CLI is slower than the API
CLAUDE_MODEL = _get_secret("CLAUDE_MODEL", "claude-sonnet-5")
CLAUDE_EFFORT = _get_secret("CLAUDE_EFFORT", "medium")               # low | medium | high | xhigh | max
CLAUDE_MAX_TOKENS = int(_get_secret("CLAUDE_MAX_TOKENS", "32000"))   # upper limit, includes thinking
CLAUDE_TIMEOUT_SEC = float(_get_secret("CLAUDE_TIMEOUT_SEC", "180")) # 3 min per try
CLAUDE_MAX_RETRIES = int(_get_secret("CLAUDE_MAX_RETRIES", "1"))     # SDK retries busy/server/network errors

# 💰 Price per 1M tokens (Sonnet 5) - only used to show the cost of each call
PRICE_INPUT_PER_M = float(_get_secret("PRICE_INPUT_PER_M", "2.0"))
PRICE_OUTPUT_PER_M = float(_get_secret("PRICE_OUTPUT_PER_M", "10.0"))

# 📁 Paths
LOGS_DIR = BASE_DIR / "logs"
PROCESSED_DIR = BASE_DIR / "processed"  # extracted resume text (.md) saved here for checking
PROMPTS_DIR = BASE_DIR / "prompts"
PROMPT_PREVIEW_DIR = BASE_DIR / "prompt_previews"  # full prompts saved here by tests (no AI call)
RESULTS_DIR = BASE_DIR / "results"  # AI's JSON answers saved here for checking

# ⚖️ Scoring (Python does all the math, never the AI)
ROLE_MATCH_MARKS = 30  # out of 100 - how well the candidate fits HR's requirements
SECTIONS_MARKS = 70    # out of 100 - shared by the 7 sections using Low / Medium / High
PRIORITY_VALUES = {"low": 5, "medium": 8, "high": 10}

# 🌐 Report language (HR can also type a custom one)
REPORT_LANGUAGES = ["English", "Urdu", "Roman Urdu", "Arabic", "Hindi", "Spanish", "French"]
MAX_CUSTOM_LANGUAGE_CHARS = 30

# 📝 HR form limits (keeps prompts short and safe)
MAX_NOTES_CHARS = 500
MAX_JOB_DESCRIPTION_CHARS = 6000

# 📄 Upload rules
ALLOWED_EXTENSIONS = ["pdf", "docx"]
MAX_UPLOAD_MB = 10
MIN_TEXT_CHARS = 150  # less text than this -> probably a scanned (image-only) PDF

# 📝 Logging
LOG_LEVEL = _get_secret("LOG_LEVEL", "INFO")  # DEBUG shows more detail

# 🏷️ Brand (change these 2 lines to rename the product)
APP_NAME = "Fair Resume Evaluator"
APP_TAGLINE = "Your AI hiring agent: reads every resume by the same rules, shows proof for every score"
