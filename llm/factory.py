"""
🏭 LLM FACTORY

WHAT
  • get_llm() → gives the AI client chosen in config.LLM_PROVIDER

WHY
  • The rest of the app never imports Claude / Claude Code / Gemini directly
  • Switch AI = change LLM_PROVIDER in config / .env (1 line)

FLOW
  LLM_PROVIDER = "auto"         ─► key sk-ant-oat... → ClaudeCodeClient
                                   key sk-ant-api... → ClaudeClient
  LLM_PROVIDER = "claude"       ─► ClaudeClient       (API key, for going live)
  LLM_PROVIDER = "claude_code"  ─► ClaudeCodeClient   (Claude Code subscription token)
  LLM_PROVIDER = "gemini"       ─► later: add llm/gemini_client.py + 2 lines below

USED BY
  • core/evaluator.py (Milestone 4)
"""

import config
from llm.base import LLMClient, LLMError
from logger import get_logger

log = get_logger(__name__)

_client: LLMClient | None = None  # created once, reused for every resume


def _resolve_provider() -> str:
    provider = (config.LLM_PROVIDER or "auto").lower()
    if provider != "auto":
        return provider
    key = config.CLAUDE_API_KEY or ""
    return "claude_code" if key.startswith("sk-ant-oat") else "claude"


def get_llm() -> LLMClient:
    global _client
    if _client is not None:
        return _client

    provider = _resolve_provider()
    if provider == "claude":
        from llm.claude_client import ClaudeClient

        _client = ClaudeClient()
    elif provider == "claude_code":
        from llm.claude_code_client import ClaudeCodeClient

        _client = ClaudeCodeClient()
    # elif provider == "gemini":
    #     from llm.gemini_client import GeminiClient
    #     _client = GeminiClient()
    else:
        raise LLMError(f"Unknown LLM_PROVIDER '{config.LLM_PROVIDER}'. Use 'auto', 'claude' or 'claude_code'.")

    log.info(f"🔌 LLM provider ready: {_client.name}")
    return _client
