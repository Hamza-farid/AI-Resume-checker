"""
📋 RESULTS PAGE

LAYOUT
  HERO   ⭕ score ring 8.5/10 · label + AI advice pills · headline · 2-line summary + max 4 tiny points
         · 🎯 30 / 📊 70 bars
  TABS   📊 Scores       → 7 section meters + formula + evidence only (✅ / 🟡 / ⚠️ quote check)
         🎯 Role Match   → ✅🟡❌ skill pills + proof table + experience fit
         💪 Pros & Cons  → green / yellow cards
         💬 Interview    → numbered question cards with the reason
         📈 Analytics    → frontend/analytics.py
         🚩 Flags        → cheating, date problems, biased HR notes not applied
         🔎 Audit        → model, prompt version, tokens, cost, what the AI read
  FOOTER 📥 report .md · 🧩 raw .json

LIVE SCORE
  • Re-calculated from the CURRENT priorities → change them above, no new AI call

USED BY
  • app.py
"""

import json

import streamlit as st

from core.report import build_markdown, section_quotes
from core.scoring import ScoreResult, calculate
from frontend import components as ui
from frontend.analytics import render_analytics
from frontend.theme import tokens

CONFIDENCE = {"high": "🟢 high confidence", "medium": "🟡 medium confidence", "low": "🔴 low confidence"}
FIT = {"below": ("🔴 Below the required level", "crit"), "meets": ("✅ Meets the required level", "good"),
       "exceeds": ("🌟 Exceeds the required level", "good"), "unclear": ("🟡 Unclear", "warn")}


def _scores_tab(data: dict, score: ScoreResult) -> None:
    left, right = st.columns([1.7, 1], gap="large")
    with left:
        st.html(ui.heading("📊 Section scores") + ui.meters(score))
    with right:
        st.html(ui.heading("🧮 How the final score is made") + ui.formula(score))
        st.caption("Low = 5 · Medium = 8 · High = 10 points. Each section's AI score (out of 10) fills its points.")

    st.html(ui.heading("📌 Evidence for each score · click to open"))
    for r in score.rows:
        sec = data["sections"][r.key]
        head = f"{r.ai_score}/10" if r.applicable else "N/A"
        with st.expander(f"{r.emoji} **{r.label}** · {head} · {CONFIDENCE.get(sec['confidence'], '')}"):
            checked = section_quotes(sec)
            if checked:
                st.html(ui.quotes(checked))
            else:
                st.caption("No quotes: this section is not in the resume.")
    st.caption("✅ found word for word in the resume · 🟡 close match · ⚠️ not found, check it")


def _role_tab(data: dict, score: ScoreResult) -> None:
    rm = data["role_match"]
    fit_text, fit_kind = FIT.get(rm["experience_level_fit"], ("🟡 Unclear", "warn"))
    must = f"{score.must_have_coverage:.0f}%" if score.must_have_coverage is not None else "—"
    nice = f"{score.nice_to_have_coverage:.0f}%" if score.nice_to_have_coverage is not None else "—"
    st.html(ui.kpis([
        ("🎯 Role Match", f"{score.role_score}/10", f"{score.role_marks} of 30 points"),
        ("✅ Must-have covered", must, "found = 1 · partial = ½"),
        ("➕ Nice-to-have covered", nice, "found = 1 · partial = ½"),
    ]) + ui.pill(fit_text, fit_kind))
    st.write(rm["summary"])
    if rm["other_requirements"]:
        st.caption(f"📋 Other requirements: {rm['other_requirements']}")

    for title, key in [("✅ Must-have skills", "must_have"), ("➕ Nice-to-have skills", "nice_to_have")]:
        if not rm[key]:
            continue
        st.html(ui.heading(title) + ui.skill_pills(rm[key]))
        st.dataframe(
            [{"Status": f"{ui.STATUS_ICON.get(i['status'], '•')} {i['status'].title()}", "Skill": i["skill"],
              "Proof from the resume": i["evidence"]} for i in rm[key]],
            hide_index=True, width="stretch",
        )
    st.caption("✅ found (used in work) · 🟡 partial (only listed, or a close skill) · ❌ missing")


def _pros_cons_tab(data: dict) -> None:
    st.html(
        "<div class='rv-grid2'>"
        f"<div>{ui.heading('💪 Strengths')}{ui.items([(x, '') for x in data['pros']], 'good')}</div>"
        f"<div>{ui.heading('🔧 Weak spots')}{ui.items([(x, '') for x in data['cons']], 'warn')}</div>"
        "</div>"
    )


def _questions_tab(data: dict) -> None:
    qs = data["interview_questions"]
    if not qs:
        st.caption("No questions suggested.")
        return
    st.html(ui.items(
        [(f"{n}. {q['question']}", f"💡 Why ask: {q['reason']} · tests {q['section'].replace('_', ' ')}")
         for n, q in enumerate(qs, 1)]
    ))


def _flags_tab(data: dict, parsed: dict) -> None:
    html = ""
    if data["red_flags"]:
        flags = sorted(data["red_flags"], key=lambda f: ui.SEVERITY_ORDER.get(f.get("severity", "medium"), 1))
        counts = {s: sum(1 for f in flags if f.get("severity", "medium") == s) for s in ("high", "medium", "verify")}
        html += ui.heading("🚩 Red flags") + ui.flag_summary(counts) + ui.flag_cards(flags)
        html += "<p class='rv-sub'>Flags point at things to ask about. They are not proof of lying, and they never change a score by themselves.</p>"
    if data["hr_instruction_flags"]:
        html += ui.heading("⚖️ HR notes NOT applied (fairness rules)") + ui.items(
            [(x, "") for x in data["hr_instruction_flags"]], "warn")
    if parsed.get("text_coverage", 100) < 97:
        html += ui.items([(f"📄 Only {parsed['text_coverage']}% of the file's text was read", "Check the processed .md file")], "warn")
    if not html:
        html = ui.items([("✅ No red flags. Nothing suspicious found.", "")], "good")
    st.html(html)


def _audit_tab(score: ScoreResult, ev: dict) -> None:
    meta, parsed = ev["meta"], ev["parsed"]
    st.html(ui.kpis([
        ("⏱️ Time", f"{meta.get('latency_s', 0):.0f}s", "AI answer time"),
        ("💰 Est. cost", f"${meta.get('cost_usd', 0):.3f}", str(meta.get("provider", ""))),
        ("🔢 Tokens in / out", f"{meta.get('input_tokens', 0) + meta.get('cache_read_tokens', 0):,} / {meta.get('output_tokens', 0):,}", "incl. cache"),
        ("📄 Text read", f"{parsed['text_coverage']}%", parsed["method"]),
    ]))
    st.markdown(
        f"- 🤖 Model `{meta.get('model')}` · effort `{meta.get('effort')}`\n"
        f"- 📝 Prompt `{meta.get('prompt_version')}` · fingerprint `{meta.get('prompt_fingerprint')}`\n"
        f"- 🧾 Request / session ID `{meta.get('request_id')}`"
    )
    if meta.get("score_fixes"):
        st.markdown("- 🔧 Score fixes: " + "; ".join(meta["score_fixes"]))
    if ev["priorities_at_eval"] != {r.key: r.priority for r in score.rows}:
        st.info("ℹ️ Priorities changed after the evaluation. The score is updated; the written feedback is from the original priorities.")
    with st.expander("👁️ Exact resume text the AI read"):
        st.text(ev["resume_markdown"])


def render_results(ev: dict, priorities: dict[str, str]) -> None:
    data, job = ev["data"], ev["job"]
    score = calculate(data, priorities)  # live: CURRENT priorities

    st.html("<div id='rv-results'></div>")
    st.html(ui.hero(score, data, job.role, ev["resume_name"], tokens()))
    if data["red_flags"]:
        high = sum(1 for f in data["red_flags"] if f.get("severity") == "high")
        extra = f" · **{high} high**" if high else ""
        st.warning(f"🚩 {len(data['red_flags'])} red flag(s) found{extra}. See the **Flags** tab.")

    tabs = st.tabs(["📊 Scores", "🎯 Role Match", "💪 Pros & Cons",
                    f"💬 Interview ({len(data['interview_questions'])})", "📈 Analytics",
                    f"🚩 Flags ({len(data['red_flags'])})", "🔎 Audit"])
    with tabs[0]:
        _scores_tab(data, score)
    with tabs[1]:
        _role_tab(data, score)
    with tabs[2]:
        _pros_cons_tab(data)
    with tabs[3]:
        _questions_tab(data)
    with tabs[4]:
        render_analytics(data)
    with tabs[5]:
        _flags_tab(data, ev["parsed"])
    with tabs[6]:
        _audit_tab(score, ev)

    report = build_markdown(data, score, job, ev["meta"], ev["resume_name"])
    stem = ev["resume_name"].rsplit(".", 1)[0]
    d1, d2 = st.columns(2)
    d1.download_button("📥 Download report (.md)", report, file_name=f"report_{stem}.md",
                       mime="text/markdown", width="stretch")
    d2.download_button(
        "🧩 Download raw data (.json)",
        json.dumps({"meta": ev["meta"], "final": score.__dict__ | {"rows": [r.__dict__ for r in score.rows]},
                    "evaluation": data}, indent=2, ensure_ascii=False, default=str),
        file_name=f"result_{stem}.json", mime="application/json", width="stretch",
    )
