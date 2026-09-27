"""
📥 REPORT

WHAT
  • build_markdown() → one readable .md report HR can download, save, or share

INSIDE THE REPORT
  ⭐ final score + label + recommendation
  🧮 marks sheet (the 30 + 70 math, every number visible)
  🎯 role match checklist · 📊 each section with evidence (✅ verified quotes) · 💪 pros / 🔧 cons
  💬 interview questions · 🚩 flags · 🔎 audit trail (model, prompt version)

USED BY
  • frontend/results.py (download button)
"""

from datetime import datetime

from core.scoring import RECOMMENDATION_LABEL, ScoreResult
from prompts.prompt_builder import JobContext

STATUS_ICON = {"found": "✅", "partial": "🟡", "missing": "❌"}
QUOTE_ICON = {"verified": "✅", "close": "🟡", "not_found": "⚠️"}


def section_quotes(sec: dict) -> list[tuple[str, str]]:
    """(quote, status) pairs. Older results made before the quote check get status '' (no icon)."""
    checks = sec.get("evidence_check")
    if checks:
        return [(c["quote"], c["status"]) for c in checks]
    return [(q, "") for q in sec.get("evidence", [])]


def build_markdown(data: dict, score: ScoreResult, job: JobContext, meta: dict, resume_name: str) -> str:
    rm = data["role_match"]
    snap = data["candidate_snapshot"]
    lines = [
        f"# 📋 Resume Evaluation: {job.role}",
        f"_File: {resume_name} · {datetime.now():%Y-%m-%d %H:%M} · AI-assisted advice, the final decision is made by HR_",
        "",
        f"## ⭐ Final score: {score.final_10} / 10  ({score.final_100} / 100) · {score.label}",
        f"**AI recommendation:** {RECOMMENDATION_LABEL.get(data['recommendation'], data['recommendation'])}",
        "",
        f"🧑‍💼 {snap['headline']} · {snap['years_relevant_experience']:g} yrs relevant · {snap['seniority_estimate']}",
        "",
        data["overall_summary"],
        *[f"- {p}" for p in data.get("key_points", [])],
        "",
        "## 🧮 Marks sheet",
        "| Section | Priority | Max | AI score | Marks got |",
        "|---|---|---|---|---|",
    ]
    for r in score.rows:
        if r.applicable:
            lines.append(f"| {r.emoji} {r.label} | {r.priority.title()} | {r.value} | {r.ai_score}/10 | {r.marks_got:.1f} |")
        else:
            lines.append(f"| {r.emoji} {r.label} | {r.priority.title()} | - | N/A | not counted |")
    lines += [
        f"| **Total** | | **{score.total_max}** | | **{score.total_got}** |",
        "",
        f"- 📊 Sections = {score.total_got} ÷ {score.total_max} × 70 = **{score.sections_marks} / 70**",
        f"- 🎯 Role Match = {score.role_score} × 3 = **{score.role_marks} / 30**",
        f"- ⭐ Final = **{score.final_100} / 100**",
        "",
        f"## 🎯 Role Match: {score.role_score}/10 ({rm['experience_level_fit']} experience level)",
        rm["summary"],
    ]
    for title, key in [("Must-have", "must_have"), ("Nice-to-have", "nice_to_have")]:
        if rm[key]:
            lines += ["", f"**{title} skills**"]
            lines += [f"- {STATUS_ICON.get(i['status'], '•')} **{i['skill']}**: {i['evidence']}" for i in rm[key]]

    lines += ["", "## 📊 Sections"]
    for r in score.rows:
        sec = data["sections"][r.key]
        head = f"{r.ai_score}/10" if r.applicable else "N/A"
        lines += ["", f"### {r.emoji} {r.label}: {head} ({sec['confidence']} confidence)", sec["summary"]]
        lines += [f"- 📌 {QUOTE_ICON.get(status, '')} \"{quote}\"".replace("  ", " ") for quote, status in section_quotes(sec)]

    lines += ["", "## 💪 Pros"] + [f"- {x}" for x in data["pros"]]
    lines += ["", "## 🔧 Cons"] + [f"- {x}" for x in data["cons"]]

    if data["interview_questions"]:
        lines += ["", "## 💬 Interview questions"]
        lines += [f"{n}. **{q['question']}**  \n   _Why: {q['reason']}_" for n, q in enumerate(data["interview_questions"], 1)]

    if data["red_flags"]:
        sev_icon = {"high": "🔴 High", "medium": "🟡 Medium", "verify": "⚪ Verify"}
        lines += ["", "## 🚩 Red flags", "_Things to ask about. Not proof of lying; flags never change a score by themselves._"]
        for f in data["red_flags"]:
            lines.append(f"- **{sev_icon.get(f.get('severity'), '🟡 Medium')} · {f['type'].replace('_', ' ')}**: {f['detail']}")
            if f.get("evidence"):
                lines.append(f"  - 📌 \"{f['evidence']}\"")
            if f.get("ask"):
                lines.append(f"  - 💬 Ask: {f['ask']}")
    if data["hr_instruction_flags"]:
        lines += ["", "## ⚖️ HR notes NOT applied (fairness)"] + [f"- {x}" for x in data["hr_instruction_flags"]]

    lines += [
        "",
        "## 🔎 Audit trail",
        f"- Provider / model: `{meta.get('provider')}` / `{meta.get('model')}` · effort `{meta.get('effort')}`",
        f"- Prompt: `{meta.get('prompt_version')}` · fingerprint `{meta.get('prompt_fingerprint')}`",
        f"- Priorities: " + ", ".join(f"{r.label} = {r.priority}" for r in score.rows),
        f"- Request / session ID: `{meta.get('request_id')}`",
    ]
    return "\n".join(lines)
