"""
🧪 MILESTONE 4 TEST: the first REAL AI call

WHAT
  • ONE resume → parse → Claude → scores → saved JSON

COST
  • ⚠️ Uses real tokens: roughly $0.05 - $0.07 per run (Sonnet 5, effort medium)

RUN (from the project folder)
  python tests/test_milestone4.py

CHECK
  • Scores printed in the terminal
  • Full answer in results/<date>_<name>.json
"""

import sys
from pathlib import Path

PROJECT_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_DIR))

from core.evaluator import EvaluationError, evaluate_resume  # noqa: E402
from core.parser import ResumeParseError, parse_resume  # noqa: E402
from prompts.prompt_builder import JobContext, describe_file  # noqa: E402
from prompts.sections_registry import SECTIONS  # noqa: E402

# 📁 Folder with the test resumes
RESUME_DIR = Path(__file__).resolve().parent / "milestone 2 resume pdfs"

# ✏️ Change this name to test another resume
RESUME_NAME = "test_simple.pdf"

# ✏️ Sample HR form - change anything you like
JOB = JobContext(
    role="Frontend Developer",
    experience_level="Mid-level (3-5 yrs)",
    must_have_skills=["React", "TypeScript", "CSS"],
    nice_to_have_skills=["Next.js", "Testing (Jest)"],
    report_language="English",
    job_description="",
    extra_notes="Remote role. Team builds dashboards for finance clients.",
    priorities={
        "experience": "high",
        "skills": "high",
        "projects": "medium",
        "education": "low",
        "formatting": "medium",
        "summary": "low",
        "certifications": "low",
    },
)

STATUS_ICON = {"found": "✅", "partial": "🟡", "missing": "❌"}


def main() -> None:
    print(f"\n🤖 Evaluating: {RESUME_NAME}  (real AI call, uses tokens)\n")

    path = RESUME_DIR / RESUME_NAME
    if not path.exists():
        print(f"❌ File not found: {path}")
        return

    try:
        parsed = parse_resume(RESUME_NAME, path.read_bytes())
        file_info = describe_file(parsed.file_type, parsed.method, parsed.pages)
        result = evaluate_resume(JOB, parsed.markdown, RESUME_NAME, file_info)
    except (ResumeParseError, EvaluationError) as e:
        print(f"\n❌ FAILED: {e}")
        return

    d = result.data
    rm = d["role_match"]

    print(f"\n{'═' * 60}\n📋 RESULT\n{'═' * 60}")
    print(f"🧑‍💼 {d['candidate_snapshot']['headline']}")
    print(f"\n🎯 Role Match: {rm['score']}/10  ({rm['experience_level_fit']} experience level)")
    for s in rm["must_have"]:
        print(f"   {STATUS_ICON[s['status']]} {s['skill']}")

    print("\n📊 Sections")
    for s in SECTIONS:
        sec = d["sections"][s.key]
        score = f"{sec['score']}/10" if sec["applicable"] else "N/A"
        print(f"   {s.emoji} {s.label:<32} {score:<6} ({sec['confidence']} confidence) [{JOB.priorities[s.key]}]")

    print("\n💪 Pros")
    for x in d["pros"]:
        print(f"   + {x}")
    print("🔧 Cons")
    for x in d["cons"]:
        print(f"   - {x}")
    print(f"\n🚩 Red flags: {len(d['red_flags'])}   💬 Interview questions: {len(d['interview_questions'])}")
    print(f"🧭 Recommendation: {d['recommendation']}")
    print(f"\n📝 {d['overall_summary']}")

    llm = result.llm
    print(f"\n{'─' * 60}")
    print(f"⏱️ {llm.latency_s:.0f}s · 🔢 in {llm.input_tokens:,} / out {llm.output_tokens:,} · "
          f"♻️ cache read {llm.cache_read_tokens:,} · 💰 ${llm.cost_usd:.4f}")
    if result.fixes:
        print(f"🔧 Score fixes: {result.fixes}")
    saved = result.saved_path.name if result.saved_path else "(not saved)"
    print(f"💾 Saved: results/{saved}")
    print("\n👀 Open that JSON file to see the full answer (evidence, analytics, questions).")


if __name__ == "__main__":
    main()
