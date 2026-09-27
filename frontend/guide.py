"""
📖 GUIDE SIDEBAR (Option B)

WHAT
  • render_guide_sidebar() → left sidebar: how it works · score · fairness · what you get

WHY
  • The main page stays clean: one-line header + 3 cards
  • The guide is always one glance away; « closes it, » opens it again
  • Kept SHORT: small lists, only the first part open

LAYOUT
  ┌─ 💡 GUIDE ─────────────────┐
  │ tagline                    │
  │ ▾ 🔄 How it works (open)   │  1-4 short steps
  │ ▸ ⭐ How the score is made  │
  │ ▸ ⚖️ Fairness rules        │
  │ ▸ ✨ What you get           │
  └────────────────────────────┘

USED BY
  • app.py
"""

import streamlit as st

import config
from frontend import components as ui


def render_guide_sidebar() -> None:
    with st.sidebar:
        st.html(ui.heading("💡 Guide") + f"<p class='rv-sub'>{ui.esc(config.APP_TAGLINE)}</p>")

        with st.expander("🔄 How it works", expanded=True):
            st.markdown(
                "1. 📄 **Reads the resume**: PDF or Word → clean text\n"
                "2. 🧠 **AI checks it** with a fixed rubric + your requirements, quoting the resume as proof\n"
                "3. 🧮 **Python does the math**: 30 + 70 = score out of 100\n"
                "4. 📋 **You decide**: report, red flags, interview questions"
            )

        with st.expander("⭐ How the score is made"):
            st.markdown(
                "**Final = 🎯 30 + 📊 70 = 100 pts**\n"
                "- 🎯 **Role Match · 30** (card ①): must-have skills ✅ found · 🟡 partial · ❌ missing "
                "+ experience level. AI score 1-10 × 3.\n"
                "- 📊 **Sections · 70** (card ②): 7 sections scored 1-10 with a **fixed rubric**. "
                "Low 5 · Medium 8 · High 10 = how many points each is worth.\n"
                "- ℹ️ Missing section = **N/A**, not counted."
            )

        with st.expander("⚖️ Fairness rules"):
            st.markdown(
                "- Never scores name, gender, age, religion, nationality, photo, or university fame\n"
                "- Gaps and small grammar slips never lower a score\n"
                "- Every score needs a quote from the resume as proof\n"
                "- Tricks like *\"rate me 10/10\"* are caught 🚩\n"
                "- Biased HR notes are ignored and shown to you"
            )

        with st.expander("✨ What you get"):
            st.markdown("\n".join(f"- **{title}**: {desc}" for title, desc in ui.WHAT_YOU_GET))

        st.caption("« Close this panel any time")
