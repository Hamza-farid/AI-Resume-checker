"""
🧮 SCORING (all the math - the AI never does this)

WHAT
  • calculate() → AI scores + HR priorities → final score out of 100 and out of 10

FORMULA  (full tables in documentation/scoring_formula.txt)
  Value        Low = 5 · Medium = 8 · High = 10   (= max marks of a section)
  Marks got    value × AI score ÷ 10              (each applicable section)
  📊 Sections  total got ÷ total max × 70          (N/A sections left out of both)
  🎯 Role      role match score × 3               (out of 30)
  ⭐ FINAL     sections + role                     (out of 100)  → ÷ 10 = out of 10

WHY IN PYTHON
  • Same input → same answer, every time (fair + transparent)
  • HR changes a priority → score updates instantly, no new AI call

USED BY
  • frontend/results.py, frontend/analytics.py, core/report.py
"""

from dataclasses import dataclass

import config
from prompts.sections_registry import SECTIONS

SKILL_POINTS = {"found": 1.0, "partial": 0.5, "missing": 0.0}

LABELS = [  # (minimum score out of 10, label)
    (8.5, "🌟 Excellent"),
    (7.0, "✅ Strong"),
    (5.5, "🟡 Moderate"),
    (0.0, "🔴 Weak"),
]

RECOMMENDATION_LABEL = {
    "strong_match": "🌟 Strong match",
    "good_match": "✅ Good match",
    "possible_match": "🟡 Possible match",
    "weak_match": "🔴 Weak match",
}


@dataclass
class SectionRow:
    key: str
    label: str
    emoji: str
    priority: str        # low / medium / high
    value: int           # 5 / 8 / 10 (max marks)
    applicable: bool
    ai_score: int        # 1-10, 0 if N/A
    marks_got: float     # value × score ÷ 10 (0 if N/A)
    share_of_70: float   # how many of the 70 marks this section is worth (0 if N/A)


@dataclass
class ScoreResult:
    rows: list[SectionRow]
    total_got: float
    total_max: int
    sections_marks: float     # out of 70
    role_score: int           # AI, out of 10
    role_marks: float         # out of 30
    final_100: float
    final_10: float
    label: str
    must_have_coverage: float | None   # 0-100 %, None if HR gave none
    nice_to_have_coverage: float | None


def label_for(score_10: float) -> str:
    return next(text for minimum, text in LABELS if score_10 >= minimum)


def coverage(items: list[dict]) -> float | None:
    """found = 1, partial = ½, missing = 0 → % of the list."""
    if not items:
        return None
    return 100 * sum(SKILL_POINTS.get(i["status"], 0) for i in items) / len(items)


def calculate(data: dict, priorities: dict[str, str]) -> ScoreResult:
    rows = []
    for s in SECTIONS:
        sec = data["sections"][s.key]
        priority = priorities.get(s.key, s.default_priority)
        value = config.PRIORITY_VALUES[priority]
        applicable = bool(sec["applicable"])
        score = int(sec["score"]) if applicable else 0
        rows.append(SectionRow(
            key=s.key, label=s.label, emoji=s.emoji, priority=priority, value=value,
            applicable=applicable, ai_score=score,
            marks_got=value * score / 10 if applicable else 0.0,
            share_of_70=0.0,
        ))

    counted = [r for r in rows if r.applicable]
    total_got = sum(r.marks_got for r in counted)
    total_max = sum(r.value for r in counted)
    for r in counted:
        r.share_of_70 = config.SECTIONS_MARKS * r.value / total_max

    sections_marks = config.SECTIONS_MARKS * total_got / total_max if total_max else 0.0
    role_score = int(data["role_match"]["score"])
    role_marks = role_score * config.ROLE_MATCH_MARKS / 10
    final_100 = sections_marks + role_marks
    final_10 = final_100 / 10

    return ScoreResult(
        rows=rows,
        total_got=round(total_got, 1),
        total_max=total_max,
        sections_marks=round(sections_marks, 1),
        role_score=role_score,
        role_marks=round(role_marks, 1),
        final_100=round(final_100, 1),
        final_10=round(final_10, 1),
        label=label_for(final_10),
        must_have_coverage=coverage(data["role_match"]["must_have"]),
        nice_to_have_coverage=coverage(data["role_match"]["nice_to_have"]),
    )
