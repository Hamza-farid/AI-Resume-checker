"""
🔌 LLM BASE (the "rules" every AI client must follow)

WHAT
  • LLMClient  → the one function every AI must have: generate_json()
  • LLMResponse → the same answer shape from every AI
  • LLMError   → one error type the app knows how to show

WHY
  • The app only talks to LLMClient, never to Claude/Gemini directly
  • Switch AI = add a new client file, change 1 line in config ✅

FLOW
  core/evaluator.py ─► LLMClient.generate_json() ─► LLMResponse
                              ▲
              ClaudeClient ───┤   (llm/claude_client.py)
              GeminiClient ───┘   (later, llm/gemini_client.py)

USED BY
  • llm/claude_client.py, llm/factory.py, core/evaluator.py (Milestone 4)
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass


class LLMError(Exception):
    """An AI problem we can show to the user in plain words (details go to the logs)."""


@dataclass
class LLMResponse:
    data: dict               # the parsed JSON answer
    model: str
    stop_reason: str
    input_tokens: int
    output_tokens: int       # includes thinking tokens
    cache_read_tokens: int
    cache_write_tokens: int
    latency_s: float
    cost_usd: float
    request_id: str | None


class LLMClient(ABC):
    name: str = "base"

    @abstractmethod
    def generate_json(self, system_prompt: str, user_message: str, schema: dict) -> LLMResponse:
        """Send the prompt, get back JSON that matches `schema`. Raises LLMError on any problem."""
