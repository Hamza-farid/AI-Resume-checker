"""
📈 ANALYTICS TAB

SHOWS
  KPI tiles   💼 roles · ⏳ avg time per role · ⏸️ gaps · 📈 bullets with numbers · 🛠️ skills proven
  Charts      📅 career timeline (blue = relevant, orange = other)
              🛠️ skills per category (blue = proven, orange = only listed)
  Lists       🎓 education · 🏅 certifications · 🌐 languages · ⏸️ gaps (info only, never lowers a score)

DATA
  • AI extracts the facts → Python counts, averages, and draws

USED BY
  • frontend/results.py
"""

import streamlit as st

from frontend import components as ui
from frontend.charts import skills_chart, timeline_chart, timeline_rows


def render_analytics(data: dict) -> None:
    a = data["analytics"]
    jobs = timeline_rows(a["career_timeline"])
    inventory = a["skills_inventory"]

    avg_months = sum(j["Months"] for j in jobs) / len(jobs) if jobs else 0
    gap_months = sum(g["months"] for g in a["employment_gaps"])
    impact = 100 * a["bullets_with_numbers"] / a["bullets_total"] if a["bullets_total"] else None
    proven = sum(1 for s in inventory if s["proven"])
    proven_pct = 100 * proven / len(inventory) if inventory else None
    relevant = sum(1 for j in a["career_timeline"] if j["relevant_to_role"])

    st.html(ui.kpis([
        ("💼 Roles", str(len(a["career_timeline"])), f"{relevant} relevant to this job"),
        ("⏳ Avg time per role", f"{avg_months / 12:.1f} yrs" if jobs else "—", "from known dates"),
        ("⏸️ Gaps over 3 months", str(len(a["employment_gaps"])), f"{gap_months} months total" if gap_months else "none"),
        ("📈 Bullets with numbers", f"{impact:.0f}%" if impact is not None else "—",
         f"{a['bullets_with_numbers']} of {a['bullets_total']}"),
        ("🛠️ Skills proven", f"{proven_pct:.0f}%" if proven_pct is not None else "—", f"{proven} of {len(inventory)}"),
    ]))

    left, right = st.columns(2, gap="large")
    with left:
        st.html(ui.heading("📅 Career timeline"))
        if jobs:
            st.altair_chart(timeline_chart(jobs), width="stretch")
        else:
            st.caption("No roles with clear dates found.")
        skipped = len(a["career_timeline"]) - len(jobs)
        if skipped > 0:
            st.caption(f"ℹ️ {skipped} role(s) not shown: dates unclear.")
    with right:
        st.html(ui.heading("🛠️ Skills: proven vs only listed"))
        if inventory:
            st.altair_chart(skills_chart(inventory), width="stretch")
            st.caption("**Proven** = the resume shows the skill used in a job or project.")
        else:
            st.caption("No skills found.")

    edu = [(f"{e['degree']}{' · ' + e['field'] if e['field'] else ''}", f"{e['institution']} {e['end_year']}".strip())
           for e in a["education_list"]]
    certs = [(c["name"], c["year"]) for c in a["certifications_list"]]
    langs = [(f"{l['language']}", l["level"]) for l in a["languages_spoken"]]
    c1, c2, c3 = st.columns(3, gap="medium")
    c1.html(ui.heading("🎓 Education") + (ui.items(edu) if edu else "<span class='rv-na'>None listed</span>"))
    c2.html(ui.heading("🏅 Certifications") + (ui.items(certs) if certs else "<span class='rv-na'>None listed</span>"))
    c3.html(ui.heading("🌐 Languages") + (ui.items(langs) if langs else "<span class='rv-na'>None listed</span>"))

    if a["employment_gaps"]:
        st.html(ui.heading("⏸️ Employment gaps · info only, never lowers a score") + ui.items(
            [(f"{g['from']} → {g['to']}", f"about {g['months']} months") for g in a["employment_gaps"]], "warn"))
