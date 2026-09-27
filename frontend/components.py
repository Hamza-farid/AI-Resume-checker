"""
🧱 COMPONENTS (small HTML building blocks for a clean, modern look)

WHAT
  • step()        → numbered step title  ("① Job details")
  • hero()        → big score ring + label + recommendation + 30/70 split
  • meters()      → 7 section rows: name · priority · bar · score · marks
  • kpis()        → row of analytics tiles
  • items()       → pros / cons / questions / flags as cards
  • pills()       → small colored tags (skills ✅🟡❌, priorities)
  • brand()       → one-line header (logo + name + AI AGENT)
  • guide_intro() · how_it_works() · WHAT_YOU_GET → content of the 📖 guide sidebar

SAFETY
  • EVERY text from the AI or the resume goes through esc() → a resume can never inject HTML/JS
  • st.html also cleans HTML (DOMPurify)

USED BY
  • app.py, frontend/form.py, frontend/results.py, frontend/analytics.py
"""

from html import escape

from core.scoring import RECOMMENDATION_LABEL, ScoreResult

STATUS_CLASS = {"found": "good", "partial": "warn", "missing": "crit"}
STATUS_ICON = {"found": "✅", "partial": "🟡", "missing": "❌"}
PRIORITY_CLASS = {"high": "accent", "medium": "", "low": ""}
RECO_CLASS = {"strong_match": "good", "good_match": "good", "possible_match": "warn", "weak_match": "crit"}


def esc(value) -> str:
    return escape(str(value if value is not None else ""), quote=True)


def label_class(score_10: float) -> str:
    return "good" if score_10 >= 7 else "warn" if score_10 >= 5.5 else "crit"


def step(num: int, title: str, note: str = "") -> str:
    note_html = f"<span class='rv-step-note'>{esc(note)}</span>" if note else ""
    return (f"<div class='rv-step'><span class='rv-step-num'>{num}</span>"
            f"<span class='rv-step-title'>{esc(title)}</span>{note_html}</div>")


def pill(text: str, kind: str = "") -> str:
    return f"<span class='rv-pill {kind}'>{esc(text)}</span>"


def _ring(score_10: float, color: str, track: str) -> str:
    """Score ring drawn with CSS (st.html strips SVG)."""
    pct = max(0.0, min(100.0, score_10 * 10))
    return f"""
<div class="rv-ring" style="background: conic-gradient({color} {pct:.1f}%, {track} 0)">
  <div class="rv-ring-hole"><div><div class="rv-ring-num">{score_10:.1f}</div><div class="rv-ring-of">out of 10</div></div></div>
</div>"""


def hero(score: ScoreResult, data: dict, role: str, resume_name: str, tok: dict) -> str:
    snap = data["candidate_snapshot"]
    reco = data["recommendation"]
    role_pct = 100 * score.role_marks / 30
    sec_pct = 100 * score.sections_marks / 70
    return f"""
<div class="rv-hero">
  {_ring(score.final_10, tok['accent'], tok['track'])}
  <div>
    {pill(score.label, label_class(score.final_10))}
    {pill(RECOMMENDATION_LABEL.get(reco, reco), RECO_CLASS.get(reco, ''))}
    {pill(f"{score.final_100} / 100")}
    <h3>{esc(snap['headline'])}</h3>
    <p>{esc(data['overall_summary'])}</p>
    {key_points(data.get('key_points', []))}
    <p style="font-size:.8rem;color:var(--rv-muted)">📄 {esc(resume_name)} · 🎯 {esc(role)} ·
       {esc(snap['latest_title'])} · {esc(f"{snap['years_relevant_experience']:g}")} yrs relevant</p>
  </div>
  <div class="rv-split">
    <div class="rv-split-row">🎯 Role Match &nbsp;<b>{score.role_marks} / 30</b>
      <div class="rv-bar"><span style="width:{role_pct:.0f}%"></span></div></div>
    <div class="rv-split-row">📊 Sections &nbsp;<b>{score.sections_marks} / 70</b>
      <div class="rv-bar"><span style="width:{sec_pct:.0f}%"></span></div></div>
    <div class="rv-split-row" style="font-size:.78rem;color:var(--rv-muted)">
      AI advice only · HR makes the final decision</div>
  </div>
</div>"""


def meters(score: ScoreResult) -> str:
    rows = []
    for r in score.rows:
        prio = pill(r.priority.title(), PRIORITY_CLASS[r.priority])
        if r.applicable:
            bar = f"<div class='rv-bar' title='{r.ai_score}/10'><span style='width:{r.ai_score * 10}%'></span></div>"
            score_html = f"<div class='rv-meter-score'>{r.ai_score}<span style='font-size:.75rem;color:var(--rv-muted)'> /10</span></div>"
            marks = f"<div class='rv-meter-marks'>{r.marks_got:.1f} of {r.value} pts</div>"
        else:
            bar = "<div class='rv-na'>Not in resume · not counted</div>"
            score_html = "<div class='rv-meter-score' style='color:var(--rv-muted)'>N/A</div>"
            marks = "<div class='rv-meter-marks'>—</div>"
        rows.append(
            f"<div class='rv-meter'><div class='rv-meter-name'>{r.emoji} {esc(r.label)} {prio}</div>"
            f"{bar}{score_html}{marks}</div>"
        )
    return f"<div class='rv-meters'>{''.join(rows)}</div>"


def formula(score: ScoreResult) -> str:
    return (
        "<div class='rv-formula'>"
        f"📊 <b>Sections</b> = {score.total_got} ÷ {score.total_max} × 70 = <b>{score.sections_marks} / 70</b><br>"
        f"🎯 <b>Role Match</b> = {score.role_score} × 3 = <b>{score.role_marks} / 30</b><br>"
        f"⭐ <b>Final</b> = {score.sections_marks} + {score.role_marks} = <b>{score.final_100} / 100</b> → "
        f"<b>{score.final_10} / 10</b>"
        "</div>"
    )


def kpis(tiles: list[tuple[str, str, str]]) -> str:
    cells = "".join(
        f"<div class='rv-kpi'><div class='rv-kpi-label'>{esc(label)}</div>"
        f"<div class='rv-kpi-value'>{esc(value)}</div><div class='rv-kpi-note'>{esc(note)}</div></div>"
        for label, value, note in tiles
    )
    return f"<div class='rv-kpis'>{cells}</div>"


def items(entries: list[tuple[str, str]], kind: str = "") -> str:
    """entries = [(main text, small text)]"""
    return "".join(
        f"<div class='rv-item {kind}'>{esc(main)}{f'<small>{esc(small)}</small>' if small else ''}</div>"
        for main, small in entries
    )


def heading(text: str) -> str:
    return f"<div class='rv-h'>{esc(text)}</div>"


def skill_pills(skills: list[dict]) -> str:
    return "".join(
        pill(f"{STATUS_ICON.get(s['status'], '•')} {s['skill']}", STATUS_CLASS.get(s["status"], "")) for s in skills
    )


SEVERITY = {  # icon, label, card color
    "high": ("🔴", "High", "crit"),
    "medium": ("🟡", "Medium", "warn"),
    "verify": ("⚪", "Verify", ""),
}
SEVERITY_ORDER = {"high": 0, "medium": 1, "verify": 2}


def flag_summary(counts: dict[str, int]) -> str:
    return "".join(
        pill(f"{SEVERITY[s][0]} {counts[s]} {SEVERITY[s][1]}", SEVERITY[s][2]) for s in ("high", "medium", "verify") if counts[s]
    )


def flag_cards(flags: list[dict]) -> str:
    """One card per flag: severity + type · what doesn't add up · 📌 quote · 💬 question to ask.
    Works with older results too (they only have type + detail)."""
    cards = []
    for f in flags:
        icon, label, kind = SEVERITY.get(f.get("severity", "medium"), SEVERITY["medium"])
        title = f"{icon} {label} · {f['type'].replace('_', ' ').capitalize()}"
        quote = f"<div class='rv-quote{' warn' if kind else ''}'>“{esc(f['evidence'])}”</div>" if f.get("evidence") else ""
        ask = f"<small>💬 Ask: {esc(f['ask'])}</small>" if f.get("ask") else ""
        cards.append(
            f"<div class='rv-item {kind}'><b>{esc(title)}</b><div style='margin:.25rem 0'>{esc(f['detail'])}</div>"
            f"{quote}{ask}</div>"
        )
    return "".join(cards)


def key_points(points: list[str]) -> str:
    """3-4 tiny bullet points under the 2-line summary (max 4 shown)."""
    if not points:
        return ""
    return "<ul class='rv-points'>" + "".join(f"<li>{esc(p)}</li>" for p in points[:4]) + "</ul>"


QUOTE_BADGE = {
    "verified": ("✅", "Found word for word in the resume"),
    "close": ("🟡", "Close match: slightly reworded or joined lines"),
    "not_found": ("⚠️", "Not found in the resume: check this quote"),
}


def quotes(checked: list[tuple[str, str]]) -> str:
    """checked = [(quote, status)] from core/report.section_quotes. status '' = older result, no badge."""
    out = []
    for quote, status in checked:
        icon, tip = QUOTE_BADGE.get(status, ("", ""))
        badge = f"<span class='rv-quote-badge' title='{esc(tip)}'>{icon}</span>" if icon else ""
        kind = " warn" if status == "not_found" else ""
        out.append(f"<div class='rv-quote{kind}'>{badge}“{esc(quote)}”</div>")
    return "".join(out)


# ─────────────────────────── product / onboarding blocks ───────────────────────────

def brand(name: str) -> str:
    """One-line header: logo + name + AI AGENT badge. Everything else lives in the guide popup."""
    return (
        "<div class='rv-brand'><div class='rv-logo'>🎯</div>"
        f"<p class='rv-title'>{esc(name)}<span class='rv-badge'>AI AGENT</span></p></div>"
    )


TRUST = ["⚖️ Same rules for everyone", "📌 Proof for every score", "🧮 Math you can check", "👤 HR makes the final call"]


def guide_intro(tagline: str) -> str:
    trust = "".join(pill(t, "accent") for t in TRUST)
    return f"<p class='rv-sub' style='font-size:.95rem'>{esc(tagline)}</p><div class='rv-trust'>{trust}</div>"


HOW_STEPS = [
    ("📄", "1 · Reads the resume", "PDF or Word → clean text. Tables, columns and Canva designs handled. Images ignored."),
    ("🧠", "2 · AI checks it like a senior recruiter",
     "Fixed rubric for 7 sections + your requirements checklist. Quotes the resume as proof. Ignores name, gender, age, photo."),
    ("🧮", "3 · Python does the math", "Role Match (30 pts) + Sections (70 pts) = score out of 100. Same input → same score."),
    ("📋", "4 · You decide", "Clear report, strengths, weak spots, red flags, interview questions. Download and share."),
]


def how_it_works(compact: bool = False, side: bool = False) -> str:
    cells = "".join(
        f"<div class='rv-how-step'><div class='rv-how-icon'>{icon}</div><div>"
        f"<div class='rv-how-title'>{esc(title)}</div><div class='rv-how-text'>{esc(text)}</div></div></div>"
        for icon, title, text in HOW_STEPS
    )
    kind = " side" if side else " compact" if compact else ""
    return f"<div class='rv-how{kind}'>{cells}</div>"


def explain(html_text: str) -> str:
    """Small blue explainer box. Only for our own fixed text (not escaped, may contain <b>)."""
    return f"<div class='rv-explain'>{html_text}</div>"


WHAT_YOU_GET = [
    ("⭐ Final score out of 10", "With a clear label (Excellent → Weak) and the AI's advice."),
    ("🎯 Requirements checklist", "Every must-have skill: ✅ found · 🟡 partial · ❌ missing, with proof."),
    ("📊 7 section scores", "Experience, skills, projects… each with quotes from the resume."),
    ("💬 Interview questions", "Made from the weakest or least clear parts of the resume."),
    ("📈 Analytics", "Career timeline, gaps, proven vs listed skills, impact numbers."),
    ("📥 Report to share", "Download a clean report (.md) or the raw data (.json)."),
]


def what_you_get(compact: bool = False) -> str:
    cards = "".join(f"<div class='rv-get-card'><b>{esc(t)}</b><span>{esc(d)}</span></div>" for t, d in WHAT_YOU_GET)
    return f"{heading('✨ What you get')}<div class='rv-get{' compact' if compact else ''}'>{cards}</div>"
