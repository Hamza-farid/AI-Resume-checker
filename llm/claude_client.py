"""
🤖 CLAUDE CLIENT

WHAT
  • Sends the prompt to Claude and returns JSON (as an LLMResponse)

SETTINGS (all in config.py, can be changed from .env)
  model        claude-sonnet-5
  effort       medium      → how deeply it thinks (low / medium / high)
  thinking     adaptive    → Claude decides how much to think per resume
  max_tokens   32000       → upper limit, bill is only for real tokens
  timeout      180 sec     → per try
  retries      1           → SDK retries busy / server / network errors
  format       JSON schema → API forces the answer shape
  cache        system prompt cached → repeat calls are cheaper
  ❌ temperature / top_p / top_k → removed on Sonnet 5 (would cause an error)

FLOW
  prompt ─► stream request ─► final message ─► check stop_reason ─► parse JSON ─► LLMResponse
                  │
                  └─ any error ─► log full details ─► LLMError (friendly message)

USED BY
  • llm/factory.py → core/evaluator.py (Milestone 4)
"""

import json
import time

import anthropic

import config
from llm.base import LLMClient, LLMError, LLMResponse
from logger import get_logger

log = get_logger(__name__)

# Cache pricing vs normal input price
_CACHE_READ_FACTOR = 0.1
_CACHE_WRITE_FACTOR = 1.25


class ClaudeClient(LLMClient):
    name = "claude"

    def __init__(self):
        if not config.CLAUDE_API_KEY:
            raise LLMError("API key not found. Add a line like  claude=sk-ant-api...  to your .env file.")
        if config.CLAUDE_API_KEY.startswith("sk-ant-oat"):
            log.error("🔑 .env has a Claude Code subscription token (sk-ant-oat...), not an API key")
            raise LLMError(
                "This is a Claude Code token (from `claude setup-token`), not an API key. "
                "Create one at console.anthropic.com → API Keys."
            )
        self._client = anthropic.Anthropic(
            api_key=config.CLAUDE_API_KEY,
            timeout=config.CLAUDE_TIMEOUT_SEC,
            max_retries=config.CLAUDE_MAX_RETRIES,
        )

    def generate_json(self, system_prompt: str, user_message: str, schema: dict) -> LLMResponse:
        request = dict(
            model=config.CLAUDE_MODEL,
            max_tokens=config.CLAUDE_MAX_TOKENS,
            thinking={"type": "adaptive"},
            output_config={
                "effort": config.CLAUDE_EFFORT,
                "format": {"type": "json_schema", "schema": schema},
            },
            # Fixed system prompt + cache marker → repeat calls reuse it (cheaper)
            system=[{"type": "text", "text": system_prompt, "cache_control": {"type": "ephemeral"}}],
            messages=[{"role": "user", "content": user_message}],
        )

        log.info(f"🤖 Sending to {config.CLAUDE_MODEL} | effort={config.CLAUDE_EFFORT} | timeout={config.CLAUDE_TIMEOUT_SEC:.0f}s")
        started = time.perf_counter()

        try:
            with self._client.messages.stream(**request) as stream:
                message = stream.get_final_message()
        except anthropic.AuthenticationError as e:
            log.error(f"🔑 Authentication failed: {e}")
            raise LLMError("The API key is invalid. Check the `claude` value in your .env file.") from e
        except anthropic.PermissionDeniedError as e:
            log.error(f"🚫 Permission denied: {e}")
            raise LLMError("This API key is not allowed to use this model.") from e
        except anthropic.NotFoundError as e:
            log.error(f"🔎 Not found (wrong model name?): {e}")
            raise LLMError(f"Model '{config.CLAUDE_MODEL}' was not found. Check CLAUDE_MODEL in config.") from e
        except anthropic.RateLimitError as e:
            log.error(f"⏳ Rate limited: {e}")
            raise LLMError("Too many requests right now. Please wait a minute and try again.") from e
        except anthropic.BadRequestError as e:
            log.error(f"🧾 Bad request: {e}")
            raise LLMError("The request was rejected by the API. See the logs for details.") from e
        except anthropic.APITimeoutError as e:
            log.error(f"⌛ Timed out after {config.CLAUDE_TIMEOUT_SEC:.0f}s (+{config.CLAUDE_MAX_RETRIES} retry): {e}")
            raise LLMError("The AI took too long to answer. Please try again.") from e
        except anthropic.APIConnectionError as e:
            log.error(f"📡 Connection error: {e}")
            raise LLMError("Could not reach the Claude API. Check your internet connection.") from e
        except anthropic.APIStatusError as e:
            log.error(f"🌩️ API error {e.status_code}: {e}")
            raise LLMError(f"Claude API error ({e.status_code}). Please try again later.") from e
        except Exception as e:
            log.exception(f"💥 Unexpected error while calling Claude: {e}")
            raise LLMError("Unexpected error while calling the AI. See the logs for details.") from e

        latency = time.perf_counter() - started
        request_id = getattr(message, "_request_id", None)
        usage = message.usage
        cache_read = usage.cache_read_input_tokens or 0
        cache_write = usage.cache_creation_input_tokens or 0

        cost = (
            usage.input_tokens * config.PRICE_INPUT_PER_M
            + cache_read * config.PRICE_INPUT_PER_M * _CACHE_READ_FACTOR
            + cache_write * config.PRICE_INPUT_PER_M * _CACHE_WRITE_FACTOR
            + usage.output_tokens * config.PRICE_OUTPUT_PER_M
        ) / 1_000_000

        log.info(
            f"📊 Done in {latency:.1f}s | stop={message.stop_reason} | in={usage.input_tokens:,} "
            f"out={usage.output_tokens:,} cache_read={cache_read:,} cache_write={cache_write:,} "
            f"| ~${cost:.4f} | request_id={request_id}"
        )

        if message.stop_reason == "refusal":
            log.warning(f"🛑 Claude declined | details={getattr(message, 'stop_details', None)}")
            raise LLMError("The AI declined to evaluate this resume. Check the file and try again.")
        if message.stop_reason == "max_tokens":
            log.error(f"✂️ Answer cut off at max_tokens={config.CLAUDE_MAX_TOKENS}")
            raise LLMError("The AI answer was cut off (too long). Increase CLAUDE_MAX_TOKENS and try again.")

        text = next((b.text for b in message.content if b.type == "text"), None)
        if not text:
            log.error(f"📭 No text block in answer | stop={message.stop_reason}")
            raise LLMError("The AI returned an empty answer. Please try again.")

        try:
            data = json.loads(text)
        except json.JSONDecodeError as e:
            log.error(f"🧩 JSON parse failed: {e} | first 300 chars: {text[:300]}")
            raise LLMError("The AI answer was not valid JSON. Please try again.") from e

        return LLMResponse(
            data=data,
            model=message.model,
            stop_reason=message.stop_reason,
            input_tokens=usage.input_tokens,
            output_tokens=usage.output_tokens,
            cache_read_tokens=cache_read,
            cache_write_tokens=cache_write,
            latency_s=latency,
            cost_usd=cost,
            request_id=request_id,
        )
