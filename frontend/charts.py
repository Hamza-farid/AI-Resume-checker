"""
📊 CHARTS (Altair - comes with Streamlit, nothing extra to install)

WHAT
  • timeline_chart()       → career timeline, relevant vs other roles
  • skills_chart()         → skills per category, proven vs just listed
  • section_scores_chart() → 7 bars (spare; the Scores tab now uses HTML meters)

RULES
  • Thin bars, rounded ends, light grid, hover tooltip on every bar
  • 2 groups → blue + orange, with a legend
  • Light + dark theme colors from frontend/theme.py

USED BY
  • frontend/analytics.py
"""

import altair as alt
import pandas as pd

from core.scoring import ScoreResult
from frontend.theme import FONT
from frontend.theme import tokens as _tokens


def palette() -> dict:
    t = _tokens()
    return {"series_1": t["accent"], "series_2": t["series_2"], "ink": t["ink"], "ink_2": t["ink2"],
            "muted": t["muted"], "grid": t["grid"], "axis": t["axis"]}


def _style(chart: alt.Chart) -> alt.Chart:
    c = palette()
    return (
        chart.configure(background="transparent", font=FONT)
        .configure_view(strokeWidth=0)
        .configure_axis(
            labelColor=c["ink_2"], titleColor=c["muted"], gridColor=c["grid"], domainColor=c["axis"],
            tickColor=c["axis"], labelFontSize=12, titleFontSize=12, titleFontWeight="normal",
        )
        .configure_legend(labelColor=c["ink_2"], titleColor=c["muted"], orient="top", labelFontSize=12)
    )


def section_scores_chart(score: ScoreResult) -> alt.Chart:
    c = palette()
    df = pd.DataFrame(
        [
            {
                "Section": r.label,
                "Score": r.ai_score if r.applicable else 0,
                "Text": f"{r.ai_score}/10" if r.applicable else "N/A (not counted)",
                "Priority": r.priority.title(),
                "Marks": f"{r.marks_got:.1f} of {r.share_of_70:.1f}" if r.applicable else "not counted",
            }
            for r in score.rows
        ]
    )
    order = [r.label for r in score.rows]
    base = alt.Chart(df).encode(
        y=alt.Y("Section:N", sort=order, title=None, axis=alt.Axis(labelLimit=240)),
        tooltip=["Section", "Priority", alt.Tooltip("Text", title="AI score"), alt.Tooltip("Marks", title="Marks (of 70 scale)")],
    )
    bars = base.mark_bar(color=c["series_1"], cornerRadiusEnd=4).encode(
        x=alt.X("Score:Q", scale=alt.Scale(domain=[0, 10]), title="AI score out of 10", axis=alt.Axis(tickCount=5))
    )
    labels = base.mark_text(align="left", dx=6, color=c["ink"], fontSize=12).encode(x="Score:Q", text="Text:N")
    return _style((bars + labels).properties(height=ROW_STEP))


def _to_date(value: str, today: pd.Timestamp) -> pd.Timestamp | None:
    v = (value or "").strip().lower()
    if v in {"present", "current", "now", "ongoing"}:
        return today
    for fmt in ("%Y-%m", "%Y"):
        try:
            return pd.to_datetime(v, format=fmt)
        except (ValueError, TypeError):
            continue
    return None


def timeline_rows(timeline: list[dict]) -> list[dict]:
    """Jobs with readable dates → start, end, months. Unknown dates are skipped."""
    today = pd.Timestamp.today().normalize()
    rows = []
    for job in timeline:
        start, end = _to_date(job.get("start"), today), _to_date(job.get("end"), today)
        if start is None or end is None or end < start:
            continue
        months = max(1, (end.year - start.year) * 12 + (end.month - start.month))
        rows.append({
            "Role": f"{job['title']} · {job['company']}",
            "Start": start, "End": end, "Months": months,
            "Group": "Relevant to this job" if job.get("relevant_to_role") else "Other experience",
        })
    return rows


# Streamlit ignores a fixed pixel height for bar charts → rows collapse on top of each other.
# alt.Step = a fixed height PER ROW, which renders correctly.
ROW_STEP = alt.Step(38)
BAND = alt.Scale(paddingInner=0.38)  # thin bars with space between rows


def timeline_chart(rows: list[dict]) -> alt.Chart:
    c = palette()
    df = pd.DataFrame(rows)
    order = [r["Role"] for r in sorted(rows, key=lambda r: r["Start"], reverse=True)]
    return _style(
        alt.Chart(df)
        .mark_bar(cornerRadius=4)
        .encode(
            x=alt.X("Start:T", title=None, axis=alt.Axis(format="%Y", tickCount="year", labelOverlap="greedy")),
            x2="End:T",
            y=alt.Y("Role:N", sort=order, title=None, scale=BAND, axis=alt.Axis(labelLimit=260)),
            color=alt.Color(
                "Group:N",
                scale=alt.Scale(domain=["Relevant to this job", "Other experience"], range=[c["series_1"], c["series_2"]]),
                title=None,
            ),
            tooltip=["Role", alt.Tooltip("Start:T", format="%b %Y"), alt.Tooltip("End:T", format="%b %Y"), "Months", "Group"],
        )
        .properties(height=ROW_STEP)
    )


def skills_chart(inventory: list[dict]) -> alt.Chart:
    c = palette()
    df = pd.DataFrame(
        [{"Category": s["category"].title(), "Status": "Proven (used in work)" if s["proven"] else "Only listed",
          "Skill": s["skill"]} for s in inventory]
    )
    counts = df.groupby(["Category", "Status"], as_index=False).agg(Count=("Skill", "count"),
                                                                     Skills=("Skill", lambda x: ", ".join(x)))
    totals = counts.groupby("Category")["Count"].sum().sort_values(ascending=False)
    return _style(
        alt.Chart(counts)
        .mark_bar(cornerRadiusEnd=4, stroke=_tokens()["card"], strokeWidth=2)  # 2px gap between stacked parts
        .encode(
            y=alt.Y("Category:N", title=None, sort=list(totals.index), scale=BAND),
            x=alt.X("Count:Q", title="Number of skills", axis=alt.Axis(tickMinStep=1)),
            color=alt.Color(
                "Status:N",
                scale=alt.Scale(domain=["Proven (used in work)", "Only listed"], range=[c["series_1"], c["series_2"]]),
                title=None,
            ),
            order=alt.Order("Status:N", sort="descending"),
            tooltip=["Category", "Status", "Count", "Skills"],
        )
        .properties(height=ROW_STEP)
    )
