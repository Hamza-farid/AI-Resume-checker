"""
🧩 JSON SCHEMA

WHAT
  • The exact shape of the AI's answer (every field + its type)

WHY
  • Claude API forces this shape → no missing or misspelled fields
  • Our code (scores, charts, report) can trust the answer blindly

FIELD ORDER (important!)
  evidence → summary → confidence → score
  • AI writes top to bottom
  • So it looks at the PROOF first, THEN picks the number
  • → more accurate + more consistent scores

WHAT THE AI RETURNS
  candidate_snapshot → headline, title, years, seniority
  role_match         → skills checklist ✅🟡❌ + score   (30%)
  sections (×7)      → evidence quotes + summary + score (70%)   (no pros/cons per section)
  pros / cons (overall), interview_questions
  red_flags          → type · evidence · detail · ask · severity (🔴 high / 🟡 medium / ⚪ verify)
  analytics          → timeline, gaps, skills, bullets (for charts)
  overall_summary (2 short lines) + key_points (3-4 tiny points), recommendation

NOT HERE
  • Final score → Python calculates it (Milestone 5)
  • 1-10 range check → Python checks it (API can't)

USED BY
  • llm/claude_client.py (Milestone 4)
"""

from prompts.sections_registry import SECTION_KEYS

CONFIDENCE = ["high", "medium", "low"]
SKILL_STATUS = ["found", "partial", "missing"]
EXPERIENCE_FIT = ["below", "meets", "exceeds", "unclear"]
SENIORITY = ["entry", "junior", "mid", "senior", "lead", "unknown"]
SKILL_CATEGORY = ["technical", "tool", "domain", "soft", "language"]
RED_FLAG_TYPES = [  # meanings in prompts/base/flags.md
    "manipulation_attempt", "experience_mismatch", "impossible_dates", "impossible_skill_claim",  # 🔴 high
    "overlapping_roles", "title_inflation", "education_irregularity", "unrealistic_numbers",      # 🟡 medium
    "copied_job_description", "keyword_stuffing",
    "needs_verification", "other",                                                                # ⚪ verify
]
FLAG_SEVERITY = ["high", "medium", "verify"]
RECOMMENDATION = ["strong_match", "good_match", "possible_match", "weak_match"]


def _obj(properties: dict) -> dict:
    return {
        "type": "object",
        "properties": properties,
        "required": list(properties.keys()),
        "additionalProperties": False,
    }


def _list(item: dict) -> dict:
    return {"type": "array", "items": item}


def _enum(values: list[str]) -> dict:
    return {"type": "string", "enum": values}


STR = {"type": "string"}
INT = {"type": "integer"}
NUM = {"type": "number"}
BOOL = {"type": "boolean"}
STR_LIST = _list(STR)

_SKILL_CHECK = _list(_obj({"skill": STR, "evidence": STR, "status": _enum(SKILL_STATUS)}))

_SECTION = _obj(
    {
        "applicable": BOOL,
        "evidence": STR_LIST,  # exact quotes → checked by core/evidence.py
        "summary": STR,
        "confidence": _enum(CONFIDENCE),
        "score": INT,  # 1-10, or 0 when not applicable (range checked in Python)
    }
)


def build_schema() -> dict:
    return _obj(
        {
            "candidate_snapshot": _obj(
                {
                    "headline": STR,
                    "latest_title": STR,
                    "years_relevant_experience": NUM,
                    "seniority_estimate": _enum(SENIORITY),
                }
            ),
            "role_match": _obj(
                {
                    "must_have": _SKILL_CHECK,
                    "nice_to_have": _SKILL_CHECK,
                    "experience_level_fit": _enum(EXPERIENCE_FIT),
                    "other_requirements": STR,
                    "summary": STR,
                    "confidence": _enum(CONFIDENCE),
                    "score": INT,
                }
            ),
            "sections": _obj({key: _SECTION for key in SECTION_KEYS}),
            "pros": STR_LIST,
            "cons": STR_LIST,
            "red_flags": _list(
                _obj(
                    {
                        "type": _enum(RED_FLAG_TYPES),
                        "evidence": STR,  # exact quote that shows the problem
                        "detail": STR,    # what does not add up, with numbers
                        "ask": STR,       # polite interview question
                        "severity": _enum(FLAG_SEVERITY),
                    }
                )
            ),
            "hr_instruction_flags": STR_LIST,
            "interview_questions": _list(
                _obj({"question": STR, "reason": STR, "section": _enum(["role_match", *SECTION_KEYS, "general"])})
            ),
            "analytics": _obj(
                {
                    "career_timeline": _list(
                        _obj({"title": STR, "company": STR, "start": STR, "end": STR, "relevant_to_role": BOOL})
                    ),
                    "employment_gaps": _list(_obj({"from": STR, "to": STR, "months": INT})),
                    "skills_inventory": _list(
                        _obj({"skill": STR, "category": _enum(SKILL_CATEGORY), "proven": BOOL})
                    ),
                    "bullets_total": INT,
                    "bullets_with_numbers": INT,
                    "education_list": _list(_obj({"degree": STR, "field": STR, "institution": STR, "end_year": STR})),
                    "certifications_list": _list(_obj({"name": STR, "year": STR})),
                    "languages_spoken": _list(_obj({"language": STR, "level": STR})),
                }
            ),
            "overall_summary": STR,  # max 2 short sentences
            "key_points": STR_LIST,  # 3-4 very short points (trimmed to 4 in Python)
            "recommendation": _enum(RECOMMENDATION),
        }
    )
