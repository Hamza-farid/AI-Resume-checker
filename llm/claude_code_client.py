"""
🖥️ CLAUDE CODE CLIENT (uses your Claude Code subscription, not an API key)

WHAT
  • Runs the Claude Code CLI in headless mode (`claude -p`) and returns JSON (LLMResponse)
  • Same generate_json() as ClaudeClient → the rest of the app doesn't know the difference

AUTH
  • .env  claude=sk-ant-oat...  (from `claude setup-token`) → passed as CLAUDE_CODE_OAUTH_TOKEN
  • Laptop already logged in to Claude Code → also works

THE COMMAND
  claude.exe -p
     --model claude-sonnet-5          → Sonnet 5
     --effort medium                  → from config
     --system-prompt-file <tmp file>  → our fixed rules (file: too long for a command line)
     --json-schema <schema>           → CLI forces the answer shape (structured_output)
     --tools ""                       → ALL tools off (no file reading, no bash)
     --no-session-persistence         → nothing saved to Claude Code history
     --output-format json             → one JSON result
  stdin  → user message (HR form + resume)
  cwd    → empty temp folder (never sees our project files)

⚠️ KNOW THIS
  • Token expires (30-90 days) → re-run `claude setup-token`, update .env
  • Streamlit Cloud has no Claude Code CLI → for going live use an API key (LLM_PROVIDER=claude)
  • Anthropic's terms limit subscription tokens for unattended/automated services → your call

USED BY
  • llm/factory.py → core/evaluator.py
"""

import json
import os
import shutil
import subprocess
import tempfile
import time
from pathlib import Path

import config
from llm.base import LLMClient, LLMError, LLMResponse
from logger import get_logger

log = get_logger(__name__)


def _find_exe() -> str | None:
    """claude.exe directly (not the .cmd/.ps1 shim) → no 8k command-line limit on Windows."""
    if config.CLAUDE_CODE_EXE and Path(config.CLAUDE_CODE_EXE).exists():
        return config.CLAUDE_CODE_EXE
    npm_exe = Path(os.path.expandvars(r"%APPDATA%\npm\node_modules\@anthropic-ai\claude-code\bin\claude.exe"))
    if npm_exe.exists():
        return str(npm_exe)
    return shutil.which("claude.exe") or shutil.which("claude")


class ClaudeCodeClient(LLMClient):
    name = "claude_code"

    def __init__(self):
        self._exe = _find_exe()
        if not self._exe:
            raise LLMError("Claude Code CLI not found. Install it (npm i -g @anthropic-ai/claude-code) or use an API key.")
        self._env = dict(os.environ)
        token = config.CLAUDE_API_KEY or ""
        if token.startswith("sk-ant-oat"):
            self._env["CLAUDE_CODE_OAUTH_TOKEN"] = token
        log.info(f"🖥️ Claude Code CLI: {self._exe}")

    def _run_once(self, cmd: list[str], user_message: str) -> dict:
        try:
            proc = subprocess.run(
                cmd,
                input=user_message,
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                env=self._env,
                cwd=tempfile.gettempdir(),  # empty-ish folder: CLI never sees our project
                timeout=config.CLAUDE_CODE_TIMEOUT_SEC,
            )
        except subprocess.TimeoutExpired as e:
            raise TimeoutError(f"no answer after {config.CLAUDE_CODE_TIMEOUT_SEC:.0f}s") from e
        except OSError as e:
            raise LLMError(f"Could not start Claude Code CLI: {e}") from e

        try:
            out = json.loads(proc.stdout)
        except json.JSONDecodeError as e:
            log.error(f"🧩 CLI output is not JSON | exit={proc.returncode} | stdout={proc.stdout[:300]!r} | stderr={proc.stderr[:300]!r}")
            raise RuntimeError(f"CLI output was not JSON (exit {proc.returncode})") from e

        if out.get("is_error"):
            status = out.get("api_error_status")
            detail = str(out.get("result") or out.get("subtype"))[:300]
            log.error(f"🌩️ Claude Code error | status={status} | subtype={out.get('subtype')} | {detail}")
            if status == 401 or "401" in detail or "auth" in detail.lower():
                raise LLMError("Claude Code login failed or the token expired. Run `claude setup-token` and update .env.")
            if status == 429:
                raise LLMError("Claude Code usage limit reached. Please wait and try again.")
            raise RuntimeError(f"Claude Code returned an error: {detail}")
        return out

    def generate_json(self, system_prompt: str, user_message: str, schema: dict) -> LLMResponse:
        # System prompt goes in a temp file (too long for a command line)
        with tempfile.NamedTemporaryFile("w", suffix=".md", delete=False, encoding="utf-8") as f:
            f.write(system_prompt)
            system_file = f.name

        cmd = [
            self._exe, "-p",
            "--model", config.CLAUDE_MODEL,
            "--effort", config.CLAUDE_EFFORT,
            "--system-prompt-file", system_file,
            "--json-schema", json.dumps(schema, separators=(",", ":")),
            "--tools", "",
            "--no-session-persistence",
            "--output-format", "json",
        ]

        log.info(f"🖥️ Sending to Claude Code | model={config.CLAUDE_MODEL} | effort={config.CLAUDE_EFFORT} | timeout={config.CLAUDE_CODE_TIMEOUT_SEC:.0f}s")
        started = time.perf_counter()
        attempts = 1 + config.CLAUDE_MAX_RETRIES
        out = None
        try:
            for attempt in range(1, attempts + 1):
                try:
                    out = self._run_once(cmd, user_message)
                    break
                except LLMError:
                    raise  # auth / limit problems: retrying won't help
                except (TimeoutError, RuntimeError) as e:
                    log.warning(f"🔁 Attempt {attempt}/{attempts} failed: {e}")
                    if attempt == attempts:
                        if isinstance(e, TimeoutError):
                            raise LLMError("The AI took too long to answer. Please try again.") from e
                        raise LLMError("Claude Code failed to answer. See the logs for details.") from e
                except Exception as e:
                    log.exception(f"💥 Unexpected error while running Claude Code: {e}")
                    raise LLMError("Unexpected error while calling the AI. See the logs for details.") from e
        finally:
            try:
                os.unlink(system_file)
            except OSError:
                pass

        latency = time.perf_counter() - started
        usage = out.get("usage") or {}
        cost = float(out.get("total_cost_usd") or 0.0)

        log.info(
            f"📊 Done in {latency:.1f}s | stop={out.get('stop_reason')} | in={usage.get('input_tokens', 0):,} "
            f"out={usage.get('output_tokens', 0):,} cache_read={usage.get('cache_read_input_tokens', 0):,} "
            f"| ~${cost:.4f} (covered by subscription) | session={out.get('session_id')}"
        )

        data = out.get("structured_output")
        if not isinstance(data, dict):
            try:
                data = json.loads(out.get("result") or "")
            except (json.JSONDecodeError, TypeError) as e:
                log.error(f"🧩 No structured output | result starts: {str(out.get('result'))[:300]!r}")
                raise LLMError("The AI answer was not valid JSON. Please try again.") from e

        return LLMResponse(
            data=data,
            model=config.CLAUDE_MODEL,
            stop_reason=str(out.get("stop_reason") or out.get("subtype")),
            input_tokens=int(usage.get("input_tokens") or 0),
            output_tokens=int(usage.get("output_tokens") or 0),
            cache_read_tokens=int(usage.get("cache_read_input_tokens") or 0),
            cache_write_tokens=int(usage.get("cache_creation_input_tokens") or 0),
            latency_s=latency,
            cost_usd=cost,
            request_id=out.get("session_id"),
        )
