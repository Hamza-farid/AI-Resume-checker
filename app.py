"""
🎯 FAIR RESUME EVALUATOR - the Streamlit app

RUN
  streamlit run app.py

PAGE
  ┌──────────┬ 🎯 Fair Resume Evaluator [AI AGENT] ─────────── [☀️ | 🌙] ┐
  │ 📖 GUIDE  │ ① Job (🎯 30 pts) │ ② What matters? (📊 70) │ ③ Resume + 🔍 │
  │ steps    ├──────────────────────────────────────────────────────┤
  │ score    │ ⭕ score hero + 7 tabs (scores, role, pros/cons, questions, │
  │ fairness │   analytics, flags, audit)                              │
  │ [«]      │                                                          │
  └──────────┴──────────────────────────────────────────────────────┘
  📖 sidebar = frontend/guide.py (« closes it)

FLOW
  form + resume → parse (core/parser) → AI (core/evaluator → llm/) → score (core/scoring, live) → results

NOTES
  • One resume at a time
  • Session (form + results) is saved → survives the ☀️/🌙 switch (frontend/session.py)
"""

import streamlit as st

import config
from core.evaluator import EvaluationError, evaluate_resume
from core.parser import ResumeParseError, parse_resume
from core.storage import save_processed
from frontend import components as ui
from frontend.auth import logout, render_session_timer, require_login
from frontend.form import current_priorities, render_workspace
from frontend.guide import render_guide_sidebar
from frontend.results import render_results
from frontend.session import init_session, save_session
from frontend.theme import inject_css, render_theme_switch
from logger import get_logger
from prompts.prompt_builder import describe_file

log = get_logger("app")

st.set_page_config(page_title=config.APP_NAME, page_icon="🎯", layout="wide", initial_sidebar_state="expanded")
init_session()
inject_css()

# ─────────────── 🔐 login gate: nothing below runs without a valid 10-minute token ───────────────
session = require_login()
busy = bool(st.session_state.get("eval_running"))

# ─────────────── 📖 guide in the left sidebar · one-line header ───────────────
render_guide_sidebar()
brand, timer_col, logout_col, switch = st.columns([4.4, 0.75, 0.85, 1.45], vertical_alignment="center")
brand.html(ui.brand(config.APP_NAME))
with timer_col:
    render_session_timer(session)
with logout_col:
    if st.button("↪ Log out", width="stretch", disabled=busy):
        logout()
        st.rerun()
with switch:
    render_theme_switch()

# ─────────────── workspace: ① job · ② priorities · ③ resume ───────────────
job, uploaded, progress_slot, running = render_workspace()


def run_evaluation() -> None:
    """Draws Step 1/4 … 4/4 inside card ③ (right under the button). Result or error goes to session_state."""
    if uploaded is None:
        st.session_state["eval_error"] = "The file is gone. Please upload the resume again."
        return
    log.info(f"🚀 New evaluation | user='{session['sub']}' | file='{uploaded.name}' | role='{job.role}'")
    with st.status("Evaluating the resume...", expanded=True) as status:
        try:
            st.write("📄 Step 1/4 · Reading the resume...")
            parsed = parse_resume(uploaded.name, uploaded.getvalue())
            save_processed(parsed)
            st.write(f"✅ Read {parsed.words:,} words · {parsed.text_coverage}% of the text kept")
            if parsed.text_coverage < 97:
                st.write("⚠️ Some text could not be read. Results may miss something.")

            st.write("🧠 Step 2/4 · The AI is checking every section against the rubric (about 1-3 minutes)...")
            file_info = describe_file(parsed.file_type, parsed.method, parsed.pages)
            result = evaluate_resume(job, parsed.markdown, uploaded.name, file_info)
            st.write("🧮 Step 3/4 · Calculating the score (30 + 70)...")
            st.write("📋 Step 4/4 · Building your report...")

            st.session_state["evaluation"] = {
                "data": result.data,
                "meta": result.meta,
                "job": result.job,
                "priorities_at_eval": dict(result.job.priorities),
                "resume_name": uploaded.name,
                "resume_markdown": parsed.markdown,
                "parsed": {"method": parsed.method, "text_coverage": parsed.text_coverage,
                           "pages": parsed.pages, "words": parsed.words},
            }
            st.session_state["_scroll_to_results"] = True
            status.update(label="✅ Evaluation complete", state="complete", expanded=False)
        except (ResumeParseError, EvaluationError) as e:
            log.error(f"💥 Evaluation failed for '{uploaded.name}': {e}")
            status.update(label="❌ Evaluation failed", state="error")
            st.session_state["eval_error"] = str(e)
        except Exception:
            log.exception(f"💥 Unexpected error for '{uploaded.name}'")
            status.update(label="❌ Something went wrong", state="error")
            st.session_state["eval_error"] = "Unexpected error. Check the terminal or the logs/ folder for details."


if running:
    with progress_slot:
        run_evaluation()
    st.session_state["eval_running"] = False
    st.rerun()  # redraw: button back to normal, results (or the error) shown

# ─────────────── results ───────────────
evaluation = st.session_state.get("evaluation")
if evaluation:
    try:
        render_results(evaluation, current_priorities())
    except Exception:
        log.exception("💥 Could not show the results")
        st.error("The results could not be displayed. Check the logs/ folder for details.")

    if st.session_state.pop("_scroll_to_results", False):
        st.html(
            "<script>setTimeout(() => document.getElementById('rv-results')"
            "?.scrollIntoView({behavior: 'smooth', block: 'start'}), 300);</script>",
            unsafe_allow_javascript=True,
        )

save_session()
