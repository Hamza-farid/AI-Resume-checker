"""
🎨 THEME (light / dark + all the CSS)

WHAT
  • current()            → "light" or "dark" (what the browser shows right now)
  • tokens()             → colors for the current theme (used by CSS + charts)
  • inject_css()         → the whole app's custom CSS, built from the tokens
  • render_theme_switch() → ☀️ / 🌙 switch in the top-right

HOW THE SWITCH WORKS
  • The switch is a plain browser button (NOT a Streamlit widget)
      → clicking it does NOT re-run the Python script
      → no half-drawn page while the reload starts (that made card ③ appear late)
  1. HR clicks 🌙
  2. The session is already saved at the end of every run   (frontend/session.py)
  3. A tiny script stores "Dark" in the browser + reloads the page
  4. Streamlit starts in dark mode, the session is restored → nothing is lost

COLORS
  • Palettes live in .streamlit/config.toml ([theme.light] / [theme.dark])
  • Scores = one blue · 2 groups = blue + orange · status = green / yellow / red + icon + word

USED BY
  • app.py, frontend/charts.py, frontend/components.py
"""

import streamlit as st

_TOKENS = {
    "light": {
        "bg": "#f6f6f3", "card": "#ffffff", "card2": "#fbfbf9", "ink": "#0b0b0b", "ink2": "#52514e",
        "muted": "#898781", "line": "rgba(11,11,11,.10)", "grid": "#e1e0d9", "axis": "#c3c2b7",
        "accent": "#2a78d6", "accent_soft": "rgba(42,120,214,.10)", "series_2": "#eb6834",
        "good": "#0ca30c", "good_text": "#006300", "good_soft": "rgba(12,163,12,.10)",
        "warn": "#fab219", "warn_text": "#7a5200", "warn_soft": "rgba(250,178,25,.16)",
        "crit": "#d03b3b", "crit_text": "#a32020", "crit_soft": "rgba(208,59,59,.10)",
        "track": "#ecebe6", "shadow": "0 1px 2px rgba(0,0,0,.04), 0 4px 16px rgba(0,0,0,.04)",
    },
    "dark": {
        "bg": "#101010", "card": "#1a1a19", "card2": "#151514", "ink": "#ffffff", "ink2": "#c3c2b7",
        "muted": "#898781", "line": "rgba(255,255,255,.10)", "grid": "#2c2c2a", "axis": "#383835",
        "accent": "#3987e5", "accent_soft": "rgba(57,135,229,.16)", "series_2": "#d95926",
        "good": "#0ca30c", "good_text": "#3fd13f", "good_soft": "rgba(12,163,12,.16)",
        "warn": "#fab219", "warn_text": "#fab219", "warn_soft": "rgba(250,178,25,.14)",
        "crit": "#d03b3b", "crit_text": "#f07070", "crit_soft": "rgba(208,59,59,.16)",
        "track": "#2a2a28", "shadow": "0 1px 2px rgba(0,0,0,.3), 0 4px 16px rgba(0,0,0,.25)",
    },
}

FONT = 'system-ui, -apple-system, "Segoe UI", Roboto, sans-serif'


def current() -> str:
    try:
        return "dark" if st.context.theme.type == "dark" else "light"
    except Exception:
        return "light"


def tokens() -> dict:
    return _TOKENS[current()]


def inject_css() -> None:
    t = tokens()
    st.html(f"""
<style>
  :root {{
    --rv-card:{t['card']}; --rv-card2:{t['card2']}; --rv-ink:{t['ink']}; --rv-ink2:{t['ink2']};
    --rv-muted:{t['muted']}; --rv-line:{t['line']}; --rv-accent:{t['accent']}; --rv-accent-soft:{t['accent_soft']};
    --rv-good:{t['good']}; --rv-good-text:{t['good_text']}; --rv-good-soft:{t['good_soft']};
    --rv-warn:{t['warn']}; --rv-warn-text:{t['warn_text']}; --rv-warn-soft:{t['warn_soft']};
    --rv-crit:{t['crit']}; --rv-crit-text:{t['crit_text']}; --rv-crit-soft:{t['crit_soft']};
    --rv-track:{t['track']}; --rv-shadow:{t['shadow']};
  }}
  .block-container {{ padding-top: 1.2rem; padding-bottom: 3rem; max-width: 1400px; }}
  header[data-testid="stHeader"] {{ background: transparent; }}

  /* bordered Streamlit containers → cards */
  div[data-testid="stVerticalBlockBorderWrapper"] {{ box-shadow: var(--rv-shadow); }}

  /* brand bar */
  .rv-brand {{ display:flex; align-items:center; gap:.8rem; }}
  .rv-logo {{ width:44px; height:44px; border-radius:12px; display:grid; place-items:center; font-size:1.5rem;
             background: var(--rv-accent-soft); }}
  .rv-title {{ font-size:1.45rem; font-weight:700; color:var(--rv-ink); line-height:1.1; margin:0; }}
  .rv-sub {{ font-size:.86rem; color:var(--rv-muted); margin:0; }}

  /* step headers */
  .rv-step {{ display:flex; align-items:center; gap:.55rem; margin: 0 0 .4rem 0; }}
  .rv-step-num {{ width:26px; height:26px; border-radius:50%; display:grid; place-items:center; font-size:.8rem;
                 font-weight:700; background:var(--rv-accent); color:#fff; }}
  .rv-step-title {{ font-weight:650; font-size:1.02rem; color:var(--rv-ink); }}
  .rv-step-note {{ font-size:.8rem; color:var(--rv-muted); margin-left:auto; }}

  /* pills */
  .rv-pill {{ display:inline-flex; align-items:center; gap:.3rem; padding:.18rem .6rem; border-radius:999px;
             font-size:.8rem; font-weight:600; border:1px solid var(--rv-line); color:var(--rv-ink2);
             background:var(--rv-card2); margin:0 .3rem .3rem 0; white-space:nowrap; }}
  .rv-pill.accent {{ background:var(--rv-accent-soft); color:var(--rv-accent); border-color:transparent; }}
  .rv-pill.good {{ background:var(--rv-good-soft); color:var(--rv-good-text); border-color:transparent; }}
  .rv-pill.warn {{ background:var(--rv-warn-soft); color:var(--rv-warn-text); border-color:transparent; }}
  .rv-pill.crit {{ background:var(--rv-crit-soft); color:var(--rv-crit-text); border-color:transparent; }}

  /* hero */
  .rv-hero {{ display:grid; grid-template-columns: auto 1fr minmax(240px, 320px); gap:1.6rem; align-items:center;
             background:var(--rv-card); border:1px solid var(--rv-line); border-radius:18px; padding:1.4rem 1.6rem;
             box-shadow:var(--rv-shadow); }}
  .rv-ring {{ position:relative; width:150px; height:150px; border-radius:50%; }}
  .rv-ring-hole {{ position:absolute; inset:13px; border-radius:50%; background:var(--rv-card);
                  display:grid; place-items:center; text-align:center; }}
  .rv-ring-num {{ font-size:2.6rem; font-weight:750; color:var(--rv-ink); line-height:1; }}
  .rv-ring-of {{ font-size:.8rem; color:var(--rv-muted); }}
  .rv-hero h3 {{ margin:.15rem 0 .35rem 0; font-size:1.25rem; color:var(--rv-ink); }}
  .rv-hero p {{ margin:.2rem 0; color:var(--rv-ink2); font-size:.95rem; line-height:1.45; }}
  .rv-split {{ display:flex; flex-direction:column; gap:.9rem; }}
  .rv-split-row {{ font-size:.85rem; color:var(--rv-ink2); }}
  .rv-split-row b {{ color:var(--rv-ink); font-size:1.05rem; }}
  @media (max-width: 900px) {{ .rv-hero {{ grid-template-columns: 1fr; justify-items:start; }} }}

  /* meters */
  .rv-bar {{ height:8px; border-radius:999px; background:var(--rv-track); overflow:hidden; margin-top:.3rem; }}
  .rv-bar > span {{ display:block; height:100%; border-radius:999px; background:var(--rv-accent); }}
  .rv-meters {{ display:flex; flex-direction:column; gap:.2rem; }}
  .rv-meter {{ display:grid; grid-template-columns: minmax(300px, 1.5fr) 2fr 70px 100px; gap:1rem; align-items:center;
              padding:.55rem .2rem; border-bottom:1px solid var(--rv-line); }}
  .rv-meter:last-child {{ border-bottom:none; }}
  .rv-meter-name {{ font-weight:600; color:var(--rv-ink); font-size:.95rem; display:flex; align-items:center;
                   gap:.45rem; flex-wrap:wrap; }}
  .rv-meter-name .rv-pill {{ margin:0; font-size:.72rem; padding:.08rem .5rem; }}
  .rv-meter-score {{ font-weight:700; color:var(--rv-ink); text-align:right; font-size:1.05rem; }}
  .rv-meter-marks {{ color:var(--rv-muted); font-size:.82rem; text-align:right; }}
  .rv-na {{ color:var(--rv-muted); font-style:italic; font-size:.85rem; }}
  @media (max-width: 760px) {{ .rv-meter {{ grid-template-columns: 1fr 1fr; }} }}

  /* kpi tiles */
  .rv-kpis {{ display:grid; grid-template-columns: repeat(auto-fit, minmax(170px, 1fr)); gap:.8rem; margin:.3rem 0 1rem 0; }}
  .rv-kpi {{ background:var(--rv-card); border:1px solid var(--rv-line); border-radius:14px; padding:.9rem 1rem;
            box-shadow:var(--rv-shadow); }}
  .rv-kpi-label {{ font-size:.8rem; color:var(--rv-muted); }}
  .rv-kpi-value {{ font-size:1.6rem; font-weight:720; color:var(--rv-ink); line-height:1.25; }}
  .rv-kpi-note {{ font-size:.78rem; color:var(--rv-ink2); }}

  /* lists: pros / cons / questions / flags */
  .rv-grid2 {{ display:grid; grid-template-columns: 1fr 1fr; gap:1rem; }}
  @media (max-width: 760px) {{ .rv-grid2 {{ grid-template-columns: 1fr; }} }}
  .rv-item {{ background:var(--rv-card); border:1px solid var(--rv-line); border-left:4px solid var(--rv-accent);
             border-radius:12px; padding:.7rem .9rem; margin-bottom:.6rem; color:var(--rv-ink); font-size:.93rem; }}
  .rv-item.good {{ border-left-color: var(--rv-good); }}
  .rv-item.warn {{ border-left-color: var(--rv-warn); }}
  .rv-item.crit {{ border-left-color: var(--rv-crit); }}
  .rv-item small {{ display:block; color:var(--rv-muted); margin-top:.3rem; font-size:.8rem; }}
  .rv-h {{ font-weight:700; color:var(--rv-ink); margin:.4rem 0 .6rem 0; font-size:1rem; }}

  .rv-quote {{ border-left:3px solid var(--rv-accent); background:var(--rv-accent-soft); padding:.45rem .8rem;
              margin:.35rem 0; border-radius:0 8px 8px 0; font-style:italic; color:var(--rv-ink); font-size:.92rem; }}
  .rv-quote.warn {{ border-left-color: var(--rv-warn); background: var(--rv-warn-soft); }}
  .rv-quote-badge {{ font-style:normal; margin-right:.45rem; cursor:help; }}
  .rv-points {{ margin:.35rem 0 .3rem 0; padding-left:1.1rem; color:var(--rv-ink); font-size:.93rem; line-height:1.55; }}
  .rv-points li {{ margin:.1rem 0; }}
  .rv-formula {{ background:var(--rv-card2); border:1px dashed var(--rv-line); border-radius:12px; padding:.7rem 1rem;
                color:var(--rv-ink2); font-size:.9rem; line-height:1.7; }}
  .rv-formula b {{ color:var(--rv-ink); }}
  .rv-share {{ font-size:.8rem; color:var(--rv-muted); text-align:right; padding-top:.45rem; }}
  .rv-share b {{ color:var(--rv-ink); }}

  /* 🔒 session countdown */
  .rv-timer {{ text-align:center; font-size:.85rem; font-weight:650; color:var(--rv-ink2); font-variant-numeric: tabular-nums;
              border:1px solid var(--rv-line); border-radius:999px; padding:.35rem .6rem; background:var(--rv-card); }}

  /* theme switch (plain buttons, no Python re-run) */
  .rv-theme {{ display:inline-flex; float:right; border:1px solid var(--rv-line); border-radius:999px; padding:3px;
              background:var(--rv-card); box-shadow:var(--rv-shadow); }}
  .rv-theme button {{ border:none; background:transparent; color:var(--rv-ink2); font-size:.85rem; font-weight:600;
                     padding:.35rem .8rem; border-radius:999px; cursor:pointer; font-family:inherit; white-space:nowrap; }}
  .rv-theme button.on {{ background:var(--rv-accent); color:#fff; }}
  .rv-theme button:not(.on):hover {{ background:var(--rv-accent-soft); color:var(--rv-accent); }}

  /* brand */
  .rv-badge {{ font-size:.66rem; font-weight:800; letter-spacing:.08em; padding:.18rem .5rem; border-radius:6px;
              background:var(--rv-accent); color:#fff; vertical-align:middle; margin-left:.45rem; }}
  .rv-trust {{ display:flex; gap:.4rem; flex-wrap:wrap; margin-top:.35rem; }}

  /* how it works strip */
  .rv-how {{ display:grid; grid-template-columns: repeat(4, 1fr); gap:.7rem; margin:.3rem 0 .9rem 0; }}
  .rv-how.compact, .rv-get.compact {{ grid-template-columns: 1fr 1fr; }}
  .rv-how.side {{ grid-template-columns: 1fr; gap:.5rem; margin:0; }}
  /* slimmer sidebar ONLY while it is open (the « collapse keeps working) */
  section[data-testid="stSidebar"][aria-expanded="true"] {{ width: 270px !important; min-width: 270px !important; }}
  section[data-testid="stSidebar"] .block-container, section[data-testid="stSidebar"] [data-testid="stSidebarContent"] {{ padding-top: .4rem; }}
  .rv-prio-name {{ font-weight:650; color:var(--rv-ink); font-size:.9rem; white-space:nowrap; overflow:hidden;
                  text-overflow:ellipsis; padding-top:.35rem; }}
  .rv-how.side .rv-how-step {{ box-shadow:none; padding:.55rem .65rem; }}
  section[data-testid="stSidebar"] .rv-trust {{ margin-bottom:.4rem; }}
  .rv-brand .rv-title {{ font-size:1.3rem; }}
  @media (max-width: 900px) {{ .rv-how {{ grid-template-columns: 1fr 1fr; }} }}
  .rv-how-step {{ background:var(--rv-card); border:1px solid var(--rv-line); border-radius:14px; padding:.7rem .85rem;
                 display:flex; gap:.65rem; align-items:flex-start; box-shadow:var(--rv-shadow); }}
  .rv-how-icon {{ font-size:1.25rem; width:36px; height:36px; border-radius:10px; display:grid; place-items:center;
                 background:var(--rv-accent-soft); flex:0 0 36px; }}
  .rv-how-title {{ font-weight:700; color:var(--rv-ink); font-size:.9rem; }}
  .rv-how-text {{ color:var(--rv-ink2); font-size:.8rem; line-height:1.4; }}

  /* card explainers + "what you'll get" */
  .rv-explain {{ background:var(--rv-accent-soft); border-radius:10px; padding:.55rem .75rem; color:var(--rv-ink2);
                font-size:.82rem; line-height:1.5; margin:.2rem 0 .6rem 0; }}
  .rv-explain b {{ color:var(--rv-ink); }}
  .rv-get {{ display:grid; grid-template-columns: repeat(3, 1fr); gap:.8rem; }}
  @media (max-width: 900px) {{ .rv-get {{ grid-template-columns: 1fr; }} }}
  .rv-get-card {{ background:var(--rv-card); border:1px dashed var(--rv-line); border-radius:14px; padding:.9rem 1rem; }}
  .rv-get-card b {{ color:var(--rv-ink); display:block; margin-bottom:.2rem; }}
  .rv-get-card span {{ color:var(--rv-ink2); font-size:.84rem; }}
</style>
""")


def render_theme_switch() -> None:
    """☀️ / 🌙 buttons that switch the theme in the browser (no Python re-run)."""
    active = current()
    light_cls = "on" if active == "light" else ""
    dark_cls = "on" if active == "dark" else ""
    st.html(
        f"""
<div class="rv-theme">
  <button id="rv-theme-light" class="{light_cls}" title="Light mode">☀️ Light</button>
  <button id="rv-theme-dark" class="{dark_cls}" title="Dark mode">🌙 Dark</button>
</div>
<script>
(() => {{
  const key = `stActiveTheme-${{window.location.pathname}}-v2`;
  const go = (theme) => {{
    window.localStorage.setItem(key, JSON.stringify(theme));
    // short wait: lets a just-typed field reach the server before the reload
    setTimeout(() => window.location.reload(), 350);
  }};
  const light = document.getElementById("rv-theme-light");
  const dark = document.getElementById("rv-theme-dark");
  if (light && !light.dataset.ready) {{ light.dataset.ready = "1"; light.addEventListener("click", () => go("Light")); }}
  if (dark && !dark.dataset.ready) {{ dark.dataset.ready = "1"; dark.addEventListener("click", () => go("Dark")); }}
}})();
</script>""",
        unsafe_allow_javascript=True,
    )
