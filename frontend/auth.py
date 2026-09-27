"""
🔐 AUTH (login page + 10-minute JWT session)

WHAT
  • require_login()        → shows the login page and STOPS the app until the user is logged in
  • render_session_timer() → 🔒 9:41 countdown in the header (runs in the browser, no Python re-runs)
  • logout()               → clears the token + this tab's saved data

LOGIN = 3 FIELDS (all must match .env / Streamlit secrets)
  👤 Username  → APP_USERNAME
  🔑 Password  → APP_PASSWORD
  🗝️ Access key → APP_ACCESS_KEY

FLOW
  login ok ─► JWT token {sub, iat, exp = now + 10 min}  (signed with JWT_SECRET, HS256)
            ─► stored in session_state["auth_token"]
  every run ─► token checked · expired / broken → back to the login page
  browser   ─► countdown hits 0 → page reloads → token expired → login page (auto-logout ✅)

SAFETY
  • compare_digest: comparison time doesn't leak which part was wrong
  • one message for any mistake: never says WHICH field was wrong
  • 5 wrong tries → locked for 60 seconds
  • login not set up in .env → the app refuses to open (fails closed)

USED BY
  • app.py
"""

import hmac
import secrets
import time

import jwt
import streamlit as st

import config
from frontend import components as ui
from frontend.session import clear_session
from logger import get_logger

log = get_logger(__name__)

_ALGO = "HS256"


@st.cache_resource
def _signing_key() -> str:
    """JWT_SECRET from .env, or a random key for this server run (tokens then die on restart)."""
    return config.JWT_SECRET or secrets.token_urlsafe(48)


def is_configured() -> bool:
    return all([config.APP_USERNAME, config.APP_PASSWORD, config.APP_ACCESS_KEY])


def _same(a: str, b: str | None) -> bool:
    return hmac.compare_digest((a or "").encode("utf-8"), (b or "").encode("utf-8"))


def _issue_token(username: str) -> str:
    now = int(time.time())
    payload = {"sub": username, "iat": now, "exp": now + config.SESSION_MINUTES * 60}
    return jwt.encode(payload, _signing_key(), algorithm=_ALGO)


def current_session() -> dict | None:
    """The valid token payload, or None (missing / expired / tampered)."""
    token = st.session_state.get("auth_token")
    if not token:
        return None
    try:
        return jwt.decode(token, _signing_key(), algorithms=[_ALGO])
    except jwt.ExpiredSignatureError:
        log.info("⌛ Session expired → logged out")
    except jwt.InvalidTokenError as e:
        log.warning(f"🚫 Invalid login token → logged out: {e}")
    logout(quiet=True)
    return None


def logout(quiet: bool = False) -> None:
    clear_session()
    if not quiet:
        log.info("👋 User logged out")


def _try_login(username: str, password: str, key: str) -> None:
    lock_until = st.session_state.get("_login_lock_until", 0)
    if time.time() < lock_until:
        st.session_state["_login_error"] = f"🔒 Too many tries. Wait {int(lock_until - time.time())} seconds."
        return

    ok = _same(username.strip(), config.APP_USERNAME) & _same(password, config.APP_PASSWORD) & _same(key, config.APP_ACCESS_KEY)
    if ok:
        st.session_state["auth_token"] = _issue_token(username.strip())
        st.session_state.pop("_login_fails", None)
        st.session_state.pop("_login_error", None)
        log.info(f"🔓 Login OK | user='{username.strip()}' | session={config.SESSION_MINUTES} min")
        return

    fails = st.session_state.get("_login_fails", 0) + 1
    st.session_state["_login_fails"] = fails
    log.warning(f"🚫 Failed login {fails}/{config.MAX_LOGIN_ATTEMPTS} | user='{username.strip()}'")
    if fails >= config.MAX_LOGIN_ATTEMPTS:
        st.session_state["_login_lock_until"] = time.time() + config.LOGIN_LOCK_SECONDS
        st.session_state["_login_fails"] = 0
        st.session_state["_login_error"] = f"🔒 Too many wrong tries. Locked for {config.LOGIN_LOCK_SECONDS} seconds."
    else:
        st.session_state["_login_error"] = "❌ Wrong username, password, or access key."


def _on_submit() -> None:
    _try_login(
        st.session_state.get("_login_user", ""),
        st.session_state.get("_login_pass", ""),
        st.session_state.get("_login_key", ""),
    )
    for k in ("_login_pass", "_login_key"):  # never keep secrets in session_state
        st.session_state.pop(k, None)


def _render_login_page() -> None:
    _, middle, _ = st.columns([1, 1.1, 1])
    with middle:
        st.html("<div style='height:6vh'></div>" + ui.brand(config.APP_NAME))
        with st.container(border=True):
            st.html(ui.heading("🔐 Sign in") + "<p class='rv-sub'>Enter your username, password, and access key.</p>")
            if not is_configured():
                st.error("Login is not set up. Add APP_USERNAME, APP_PASSWORD and APP_ACCESS_KEY to .env "
                         "(or Streamlit Cloud secrets), then restart the app.")
                return
            # on_click callback runs BEFORE the next script run → that run is already logged in.
            # (Calling st.rerun() inside the form instead made the form fields show wrong values.)
            with st.form("login", border=False):
                st.text_input("👤 Username", key="_login_user", autocomplete="username")
                st.text_input("🔑 Password", key="_login_pass", type="password", autocomplete="current-password")
                st.text_input("🗝️ Access key", key="_login_key", type="password", autocomplete="off")
                st.form_submit_button("Sign in", type="primary", width="stretch", on_click=_on_submit)
            if st.session_state.get("_login_error"):
                st.error(st.session_state["_login_error"])
            st.caption(f"🔒 You stay signed in for {config.SESSION_MINUTES} minutes.")


def require_login() -> dict:
    """Returns the session (token payload). If not logged in: shows the login page and stops the app."""
    session = current_session()
    if session:
        return session
    _render_login_page()
    st.stop()


def render_session_timer(session: dict) -> None:
    """Countdown in the browser. At 0 the page reloads → Python sees the expired token → login page."""
    exp_ms = int(session["exp"]) * 1000 + 1500  # +1.5s so the server surely sees it as expired
    st.html(
        f"""
<div class="rv-timer" title="Auto sign-out when this reaches 0"><span id="rv-timer">🔒 --:--</span></div>
<script>
(() => {{
  const exp = {exp_ms};
  if (window.__rvTimer) clearInterval(window.__rvTimer);
  const tick = () => {{
    const el = document.getElementById("rv-timer");
    const left = exp - Date.now();
    if (left <= 0) {{ clearInterval(window.__rvTimer); window.location.reload(); return; }}
    const m = Math.floor(left / 60000), s = Math.floor((left % 60000) / 1000);
    if (el) el.textContent = `🔒 ${{m}}:${{String(s).padStart(2, "0")}}`;
  }};
  tick();
  window.__rvTimer = setInterval(tick, 1000);
}})();
</script>""",
        unsafe_allow_javascript=True,
    )
