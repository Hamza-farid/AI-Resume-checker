"""
🧳 SESSION (keeps the form + results alive across a page reload)

WHAT
  • init_session()  → gives this browser tab an ID (?sid=... in the URL) and restores saved values
  • save_session()  → saves form values + the last evaluation + the login token on the server
  • clear_session() → logout: forgets everything this tab saved (form, results, token)

WHY
  • Switching ☀️/🌙 reloads the page, and a reload normally wipes everything
  • With this, HR switches the theme and the results are still there

FLOW
  first visit     → new sid in URL → defaults
  theme switch    → save_session() → reload → init_session() finds sid → values restored ✅

NOTE
  • Stored in server memory only (last 200 tabs). Never on disk, never in the URL
  • The uploaded file itself is not kept (browsers don't allow that); the results are
  • The login token is kept too, so a theme switch doesn't log you out. It still expires
    after SESSION_MINUTES. The ?sid= link works like a session key: don't share it while logged in

USED BY
  • app.py, frontend/theme.py, frontend/form.py
"""

import uuid

import streamlit as st

from prompts.sections_registry import SECTIONS

MAX_SAVED_TABS = 200

# Form widget keys and their defaults (widgets read their value from here, never pass a value)
FORM_DEFAULTS: dict = {
    "f_role": "",
    "f_experience": "Junior (1-3 yrs)",
    "f_language": "English",
    "f_must": [],
    "f_nice": [],
    "f_jd": "",
    "f_notes": "",
    **{f"prio_{s.key}": s.default_priority for s in SECTIONS},
}
PERSIST_KEYS = [*FORM_DEFAULTS.keys(), "evaluation", "auth_token"]


@st.cache_resource
def _vault() -> dict:
    return {}  # sid -> {key: value}, shared by the server process


def init_session() -> None:
    sid = st.query_params.get("sid")
    if not sid:
        sid = uuid.uuid4().hex[:16]
        st.query_params["sid"] = sid
    st.session_state["sid"] = sid

    if not st.session_state.get("_restored"):
        saved = _vault().get(sid)
        if saved:
            for key, value in saved.items():
                st.session_state[key] = value
        st.session_state["_restored"] = True


def apply_form_defaults() -> None:
    """Call in the SAME run that draws the form widgets (form.render_workspace).
    Streamlit bug: a widget value set in an earlier run where the widget was NOT drawn (e.g. on the
    login page) is kept on the server but NOT shown in the browser → screen and AI would disagree."""
    for key, value in FORM_DEFAULTS.items():
        st.session_state.setdefault(key, value)


def save_session() -> None:
    sid = st.session_state.get("sid")
    if not sid:
        return
    vault = _vault()
    vault[sid] = {k: st.session_state[k] for k in PERSIST_KEYS if k in st.session_state}
    while len(vault) > MAX_SAVED_TABS:  # forget the oldest tabs
        vault.pop(next(iter(vault)))


def clear_session() -> None:
    """Logout: remove this tab's form values, results and token (here AND in the server vault)."""
    for key in PERSIST_KEYS:
        st.session_state.pop(key, None)
    for key in ("eval_running", "eval_error", "eval_notice"):
        st.session_state.pop(key, None)
    sid = st.session_state.get("sid")
    if sid:
        _vault().pop(sid, None)
