"""
📋 WORKSPACE (the 3 cards at the top of the page - no scrolling needed)

LAYOUT
  ┌─ ① Job details ─────┐ ┌─ ② What matters? ──────┐ ┌─ ③ Resume ─────────┐
  │ 🎯 role              │ │ 💼 Experience [L|M|H] 17│ │ 📤 drop PDF / DOCX  │
  │ 📅 level  🌐 language │ │ 🛠️ Skills     [L|M|H] 17│ │ 📄 file chip        │
  │ ✅ must-have (chips)  │ │ ... 7 rows, live marks  │ │ 🔍 EVALUATE         │
  │ ➕ nice-to-have       │ │                         │ │ 🗑️ clear results    │
  │ 📋 JD & notes (pop)   │ │ Role Match always 30    │ │                     │
  └──────────────────────┘ └─────────────────────────┘ └─────────────────────┘

WHY
  • Everything above the fold: HR sees the upload box right away
  • Skills are chips: type + Enter (or pick a suggestion)
  • Priorities are one-click Low / Medium / High with live "marks out of 70"
  • Values live in session_state (frontend/session.py) → survive the theme switch

USED BY
  • app.py
"""

import streamlit as st

import config
from frontend.components import step
from frontend.session import apply_form_defaults
from prompts.prompt_builder import EXPERIENCE_LEVELS, JobContext
from prompts.sections_registry import SECTIONS

PRIORITY_OPTIONS = ["low", "medium", "high"]

# Short names so each priority row stays on ONE line
SHORT_LABEL = {
    "experience": "Experience", "skills": "Skills", "projects": "Projects", "education": "Education",
    "formatting": "ATS format", "summary": "Summary", "certifications": "Certificates",
}

SKILL_SUGGESTIONS = [
    "SQL", "Excel", "Python", "Power BI", "Tableau", "Statistics", "Machine Learning", "Data Visualization",
    "JavaScript", "TypeScript", "React", "Next.js", "Node.js", "HTML", "CSS", "Java", "C#", ".NET", "Go",
    "AWS", "Azure", "GCP", "Docker", "Kubernetes", "Terraform", "CI/CD", "Linux", "Git",
    "Figma", "User Research", "Prototyping", "Design Systems", "Product Roadmapping", "A/B Testing",
    "Agile / Scrum", "Project Management", "Stakeholder Management", "Communication", "Leadership",
    "Sales", "Marketing", "SEO", "Accounting", "Financial Analysis", "Recruiting",
]


def _keep_priority(key: str) -> None:
    """Clicking the selected button again would clear it → put the last value back."""
    if st.session_state.get(key) is None:
        st.session_state[key] = st.session_state.get(f"{key}_last", "medium")
    st.session_state[f"{key}_last"] = st.session_state[key]


def current_priorities() -> dict[str, str]:
    return {s.key: (st.session_state.get(f"prio_{s.key}") or s.default_priority) for s in SECTIONS}


def _job_card(locked: bool) -> None:
    """locked = an evaluation is running → inputs are read-only (a click would restart the AI call)."""
    with st.container(border=True):
        st.html(step(1, "Job details", "🎯 Role Match · 30 pts"))
        st.text_input("🎯 Job role *", key="f_role", placeholder="e.g. Data Analyst", max_chars=100, disabled=locked)
        st.selectbox("📅 Experience level", EXPERIENCE_LEVELS, key="f_experience", disabled=locked)
        languages = list(dict.fromkeys([*config.REPORT_LANGUAGES, st.session_state.get("f_language") or "English"]))
        st.selectbox(
            "🌐 Report language", languages, key="f_language", accept_new_options=True, disabled=locked,
            help=f"Pick one or type your own (letters only, max {config.MAX_CUSTOM_LANGUAGE_CHARS}).",
        )
        chosen = [*st.session_state.get("f_must", []), *st.session_state.get("f_nice", [])]
        options = list(dict.fromkeys([*SKILL_SUGGESTIONS, *chosen]))
        st.multiselect("✅ Must-have skills", options, key="f_must", accept_new_options=True,
                       placeholder="Type a skill + Enter", disabled=locked)
        st.multiselect("➕ Nice-to-have skills", options, key="f_nice", accept_new_options=True,
                       placeholder="Optional", disabled=locked)
        filled = sum(bool(st.session_state.get(k)) for k in ("f_jd", "f_notes"))
        with st.popover(f"📋 Job description & notes{f'  ·  {filled} added' if filled else ''}",
                        width="stretch", disabled=locked):
            st.text_area("Job description (optional)", key="f_jd", height=200,
                         max_chars=config.MAX_JOB_DESCRIPTION_CHARS, placeholder="Paste the job post here...")
            st.text_area("📝 Extra notes for the evaluator (optional)", key="f_notes", height=90,
                         max_chars=config.MAX_NOTES_CHARS, placeholder="e.g. Finance team, remote, client-facing")


def _priority_card(locked: bool) -> None:
    priorities = current_priorities()
    total = sum(config.PRIORITY_VALUES[p] for p in priorities.values())
    with st.container(border=True):
        st.html(step(2, "What matters for this job?", "📊 Sections · 70 pts"))
        for s in SECTIONS:
            key = f"prio_{s.key}"
            st.session_state.setdefault(f"{key}_last", st.session_state.get(key) or s.default_priority)
            name, ctrl, share = st.columns([1.0, 1.9, 0.3], vertical_alignment="center", gap="small")
            name.html(f"<div class='rv-prio-name' title='{s.label}'>{s.emoji} {SHORT_LABEL.get(s.key, s.label)}</div>")
            with ctrl:
                st.segmented_control(
                    s.label, PRIORITY_OPTIONS, key=key, format_func=str.title,
                    label_visibility="collapsed", on_change=_keep_priority, args=(key,), width="stretch",
                    disabled=locked,
                )
            marks = config.SECTIONS_MARKS * config.PRIORITY_VALUES[priorities[s.key]] / total
            share.html(f"<div class='rv-share' title='points out of 70'><b>{marks:.1f}</b></div>")


def _start_evaluation() -> None:
    """Button callback: runs BEFORE the page re-draws, so the button is already disabled on screen.
    (A role typed without Enter is sent along with the click, so checking it here works.)"""
    if not (st.session_state.get("f_role") or "").strip():
        st.session_state["eval_notice"] = "👈 Please enter the **job role** first."
        return
    st.session_state["eval_running"] = True
    st.session_state.pop("eval_error", None)


def _resume_card(running: bool):
    """Returns (uploaded file, progress slot). The progress steps are drawn INSIDE this card, right under the button."""
    with st.container(border=True):
        st.html(step(3, "Resume", "PDF · DOCX"))
        uploaded = st.file_uploader(
            "Upload resume", type=config.ALLOWED_EXTENSIONS, label_visibility="collapsed", disabled=running,
        )
        st.button(
            "⏳ Evaluating..." if running else "🔍 Evaluate resume",
            type="primary", width="stretch", disabled=running or not uploaded, on_click=_start_evaluation,
        )
        slot = st.container()  # app.py draws the Step 1/4 … 4/4 progress here
        notice = st.session_state.pop("eval_notice", None)
        if notice:
            slot.warning(notice)
        if st.session_state.get("eval_error") and not running:
            slot.error(f"❌ {st.session_state['eval_error']}")
        if not running:
            st.caption("👆 Drop a resume to start." if not uploaded else "⏱️ Takes about 1-3 minutes.")
        if st.session_state.get("evaluation"):
            if st.button("🗑️ Clear results", width="stretch", disabled=running):
                st.session_state.pop("evaluation", None)
                st.rerun()
    return uploaded, slot


def render_workspace() -> tuple[JobContext, object, object, bool]:
    """Returns (job, uploaded file, progress slot, running?)."""
    apply_form_defaults()  # same run as the widgets (see session.apply_form_defaults)
    running = bool(st.session_state.get("eval_running"))
    c1, c2, c3 = st.columns([1.0, 1.4, 0.85], gap="medium")
    with c1:
        _job_card(running)
    with c2:
        _priority_card(running)
    with c3:
        role = (st.session_state.get("f_role") or "").strip()
        uploaded, slot = _resume_card(running)

    job = JobContext(
        role=role,
        experience_level=st.session_state.get("f_experience") or EXPERIENCE_LEVELS[1],
        must_have_skills=list(st.session_state.get("f_must") or []),
        nice_to_have_skills=list(st.session_state.get("f_nice") or []),
        report_language=st.session_state.get("f_language") or "English",
        job_description=st.session_state.get("f_jd") or "",
        extra_notes=st.session_state.get("f_notes") or "",
        priorities=current_priorities(),
    )
    return job, uploaded, slot, running
