"""
🏗️ PROMPT BUILDER

WHAT
  • Joins all prompt .md files into ONE system prompt
  • Turns the HR form + resume into the user message
  • Checks the HR form (role, language, limits)

WHY
  • Rules live in .md files → easy to edit, no code change
  • Fixed part and changing part stay separate → cheaper (cache)

FLOW
  prompts/base/*.md  ─┐
  prompts/sections/*.md ─┴─► build_system_prompt()  ─► 🧠 System prompt  (FIXED, cached)

  HR form ─► validate_job() ─┐
  resume Markdown ───────────┴─► build_user_message() ─► 📨 User message (CHANGES every time)

USED BY
  • tests/test_milestone3.py   (preview, no AI call)
  • llm/claude_client.py       (Milestone 4, real AI call)
"""

import hashlib
import re
from dataclasses import dataclass, field
from datetime import date
from functools import lru_cache

import config
from logger import get_logger
from prompts.sections_registry import SECTIONS

log = get_logger(__name__)

PROMPT_VERSION = "v1.2"
# v1.1: no per-section pros/cons, key_points, exact quotes, gaps only in analytics, <file_info>
# v1.2: flags.md (12 red-flag types, severity, evidence, interview question) + today's date

# Order of the base files inside the system prompt
BASE_FILES = ["role.md", "fairness.md", "security.md", "scoring_rules.md", "role_match.md", "flags.md"]

EXPERIENCE_LEVELS = [
    "Fresher / Entry (0-1 yrs)",
    "Junior (1-3 yrs)",
    "Mid-level (3-5 yrs)",
    "Senior (5-8 yrs)",
    "Lead / Expert (8+ yrs)",
]

_LANGUAGE_OK = re.compile(r"^[A-Za-zÀ-ɏ؀-ۿऀ-ॿ ]+$")  # letters + spaces only


class JobContextError(ValueError):
    """A problem with the HR form that we can explain in plain words."""


@dataclass
class JobContext:
    """Everything HR fills in the form."""

    role: str
    experience_level: str
    must_have_skills: list[str] = field(default_factory=list)
    nice_to_have_skills: list[str] = field(default_factory=list)
    report_language: str = "English"
    job_description: str = ""
    extra_notes: str = ""
    priorities: dict[str, str] = field(
        default_factory=lambda: {s.key: s.default_priority for s in SECTIONS}
    )  # section key -> "low" | "medium" | "high"


def validate_job(job: JobContext) -> JobContext:
    """Checks the HR form. Raises JobContextError with a friendly message."""
    job.role = job.role.strip()
    if not job.role:
        raise JobContextError("Please enter the job role.")
    if len(job.role) > 100:
        raise JobContextError("Job role is too long (max 100 characters).")

    job.report_language = job.report_language.strip() or "English"
    if len(job.report_language) > config.MAX_CUSTOM_LANGUAGE_CHARS or not _LANGUAGE_OK.match(job.report_language):
        raise JobContextError(
            f"Report language must be letters and spaces only (max {config.MAX_CUSTOM_LANGUAGE_CHARS})."
        )

    if len(job.extra_notes) > config.MAX_NOTES_CHARS:
        raise JobContextError(f"Extra notes are too long (max {config.MAX_NOTES_CHARS} characters).")
    if len(job.job_description) > config.MAX_JOB_DESCRIPTION_CHARS:
        raise JobContextError(f"Job description is too long (max {config.MAX_JOB_DESCRIPTION_CHARS} characters).")

    for s in SECTIONS:
        p = job.priorities.get(s.key, s.default_priority).lower()
        if p not in config.PRIORITY_VALUES:
            raise JobContextError(f"Priority for {s.label} must be Low, Medium, or High.")
        job.priorities[s.key] = p

    job.must_have_skills = [x.strip() for x in job.must_have_skills if x.strip()]
    job.nice_to_have_skills = [x.strip() for x in job.nice_to_have_skills if x.strip()]
    return job


# ─────────────────────────── system prompt (fixed) ───────────────────────────

def _read(path) -> str:
    return path.read_text(encoding="utf-8").strip()


@lru_cache(maxsize=1)
def build_system_prompt() -> str:
    base_dir = config.PROMPTS_DIR / "base"
    sections_dir = config.PROMPTS_DIR / "sections"

    parts = [_read(base_dir / name) for name in BASE_FILES]

    rubrics = [_read(sections_dir / f"{s.key}.md") for s in SECTIONS]
    parts.append("# Section rubrics\n\nScore every one of these 7 sections.\n\n" + "\n\n".join(rubrics))

    parts.append(_read(base_dir / "output_format.md"))

    prompt = "\n\n---\n\n".join(parts)
    log.info(f"🧠 System prompt built | {PROMPT_VERSION} | {len(prompt):,} chars | fingerprint={_fingerprint(prompt)}")
    return prompt


def _fingerprint(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()[:10]


def system_prompt_fingerprint() -> str:
    """Short code saved with every report, so we always know which prompt text scored it."""
    return _fingerprint(build_system_prompt())


# ─────────────────────────── user message (changes) ───────────────────────────

def _bullets(items: list[str]) -> str:
    return "\n".join(f"- {i}" for i in items) if items else "(none given)"


# What the parser's reading method tells us about the ORIGINAL file's layout (for the ATS judgement)
_LAYOUT_NOTES = {
    "Method 1 (classic)": "Standard PDF layout (plain text, possibly columns or simple tables).",
    "Method 2 (ignore boxes)": "Designed PDF with coloured boxes, sidebars or graphics (e.g. Canva-style). "
                               "Basic ATS systems often misread this kind of layout.",
    "Method 3 (layout)": "Complex PDF layout; the reading order of columns may be mixed in the text below.",
    "MarkItDown": "Standard Word document.",
    "MarkItDown + unwrap layout tables": "Word document that uses tables to build columns (fake columns). "
                                         "Some ATS systems read tables poorly.",
}


def describe_file(file_type: str, method: str, pages: int | None) -> str:
    """Plain-language description of the original file, sent to the AI as <file_info>."""
    layout = _LAYOUT_NOTES.get(method, "Unknown layout.")
    page_text = f", {pages} page(s)" if pages else ""
    return (
        f"Original file: {file_type.upper()}{page_text}. Layout: {layout}\n"
        "The resume text below was converted from that file by the app. Leftovers of the conversion "
        "(stray icon letters, repeated or scrambled numbers from stat boxes, broken tables) are not the candidate's fault."
    )


def build_user_message(job: JobContext, resume_markdown: str, file_info: str = "") -> str:
    priorities = "\n".join(
        f"- {s.key} ({s.label}): {job.priorities[s.key].upper()}" for s in SECTIONS
    )

    return f"""<job_context>
Role: {job.role}
Experience level required: {job.experience_level}
Report language: {job.report_language}
Today's date: {date.today().isoformat()}

Must-have skills:
{_bullets(job.must_have_skills)}

Nice-to-have skills:
{_bullets(job.nice_to_have_skills)}

Section priorities (where HR wants more detail; they never change a score):
{priorities}

Job description:
{job.job_description.strip() or "(not provided)"}

Additional HR notes:
{job.extra_notes.strip() or "(none)"}
</job_context>

<file_info>
{file_info or "(not available)"}
</file_info>

<resume>
{resume_markdown}
</resume>

Evaluate this resume for the job in <job_context>. Follow your rubrics and fairness rules, and write all text in {job.report_language}."""
