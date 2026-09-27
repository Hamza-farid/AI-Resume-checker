"""
🎯 EVALUATOR (joins all the pieces for ONE resume)

WHAT
  • evaluate_resume() → HR form + resume Markdown → checked AI evaluation + saved JSON

FLOW
  HR form ─► validate_job()                 (prompts/prompt_builder.py)
                 │
  resume ────────┴─► build prompts           (system + user message)
                         │
                         ▼
                 get_llm().generate_json()   (llm/ → Claude)
                         │
                         ▼
                 🔧 check scores             (1-10, N/A = 0, fix + log)
                 ✂️ key points max 4 · pros / cons max 8 each
                 📌 check evidence           (every quote really in the resume? core/evidence.py)
                         │
                         ▼
                 💾 save_result()            (results/result_<name>.json)

NOT HERE
  • Final score (30 + 70 math) → core/scoring.py (Milestone 5)

USED BY
  • tests/test_milestone4.py, app.py
"""

from dataclasses import asdict, dataclass, field
from datetime import datetime
from pathlib import Path

import config
from core.evidence import check_evidence
from core.storage import save_result
from llm.base import LLMError, LLMResponse
from llm.factory import get_llm
from logger import get_logger
from prompts.prompt_builder import (
    PROMPT_VERSION,
    JobContext,
    JobContextError,
    build_system_prompt,
    build_user_message,
    system_prompt_fingerprint,
    validate_job,
)
from prompts.schema import build_schema
from prompts.sections_registry import SECTIONS

log = get_logger(__name__)


class EvaluationError(Exception):
    """Any problem during evaluation, with a message safe to show the user."""


@dataclass
class EvaluationResult:
    data: dict                  # the AI's JSON (after score checks)
    llm: LLMResponse
    job: JobContext
    meta: dict = field(default_factory=dict)        # provider, model, tokens, cost... (also in the saved JSON)
    fixes: list[str] = field(default_factory=list)  # scores we had to correct
    saved_path: Path | None = None


def _clamp(value, low: int, high: int) -> int:
    try:
        return max(low, min(high, int(value)))
    except (TypeError, ValueError):
        return low


def _check_scores(data: dict) -> list[str]:
    """API guarantees the JSON shape, not the number range. Fix anything outside 1-10."""
    fixes = []

    rm = data["role_match"]
    fixed = _clamp(rm["score"], 1, 10)
    if fixed != rm["score"]:
        fixes.append(f"Role Match: {rm['score']} → {fixed}")
        rm["score"] = fixed

    for s in SECTIONS:
        sec = data["sections"][s.key]
        fixed = _clamp(sec["score"], 1, 10) if sec["applicable"] else 0
        if fixed != sec["score"]:
            fixes.append(f"{s.label}: {sec['score']} → {fixed}")
            sec["score"] = fixed

    for f in fixes:
        log.warning(f"🔧 Score fixed | {f}")
    return fixes


MAX_KEY_POINTS = 4
MAX_PROS_CONS = 8  # prompt asks for 3-8 of each; Python makes sure it never goes above 8


def evaluate_resume(
    job: JobContext, resume_markdown: str, resume_name: str, file_info: str = ""
) -> EvaluationResult:
    """One resume in → checked evaluation out. Raises EvaluationError with a friendly message.
    file_info: plain-language description of the original file (prompt_builder.describe_file)."""
    try:
        job = validate_job(job)
    except JobContextError as e:
        raise EvaluationError(str(e)) from e

    log.info(f"🎯 Evaluating '{resume_name}' | role='{job.role}' | language={job.report_language}")

    try:
        system_prompt = build_system_prompt()
        user_message = build_user_message(job, resume_markdown, file_info)
        schema = build_schema()
    except OSError as e:
        log.error(f"📂 Could not read prompt files: {e}")
        raise EvaluationError("Prompt files are missing or unreadable. See the logs.") from e

    try:
        response = get_llm().generate_json(system_prompt, user_message, schema)
    except LLMError as e:
        raise EvaluationError(str(e)) from e

    try:
        fixes = _check_scores(response.data)
        response.data["key_points"] = list(response.data.get("key_points", []))[:MAX_KEY_POINTS]
        for key in ("pros", "cons"):
            response.data[key] = list(response.data.get(key, []))[:MAX_PROS_CONS]
        evidence_counts = check_evidence(response.data, resume_markdown)
    except (KeyError, TypeError) as e:
        log.error(f"🧩 AI answer is missing expected fields: {e}")
        raise EvaluationError("The AI answer was incomplete. Please try again.") from e

    badge = "✅" if evidence_counts["not_found"] == 0 else "⚠️"
    log.info(
        f"{badge} Evidence check | verified={evidence_counts['verified']} close={evidence_counts['close']} "
        f"not_found={evidence_counts['not_found']}"
    )

    payload = {
        "meta": {
            "resume": resume_name,
            "evaluated_at": datetime.now().isoformat(timespec="seconds"),
            "provider": get_llm().name,
            "model": response.model,
            "effort": config.CLAUDE_EFFORT,
            "prompt_version": PROMPT_VERSION,
            "prompt_fingerprint": system_prompt_fingerprint(),
            "latency_s": round(response.latency_s, 1),
            "input_tokens": response.input_tokens,
            "output_tokens": response.output_tokens,
            "cache_read_tokens": response.cache_read_tokens,
            "cache_write_tokens": response.cache_write_tokens,
            "cost_usd": round(response.cost_usd, 4),
            "request_id": response.request_id,
            "score_fixes": fixes,
            "evidence_check": evidence_counts,
            "file_info": file_info,
        },
        "job": asdict(job),
        "evaluation": response.data,
    }
    saved = save_result(resume_name, payload)

    log.info(f"🏁 Finished '{resume_name}' | role match={response.data['role_match']['score']}/10")
    return EvaluationResult(
        data=response.data, llm=response, job=job, meta=payload["meta"], fixes=fixes, saved_path=saved
    )
