"""
🧪 Milestone 2 test: read ONE resume → Markdown → save to processed/

Run from the project folder:
    python tests/test_milestone2.py

Then open the processed/ folder and check the .md file.
"""

import sys
from pathlib import Path

# Let this script import config, logger, core/... from the project folder
PROJECT_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_DIR))

from core.parser import ResumeParseError, parse_resume  # noqa: E402
from core.storage import save_processed  # noqa: E402

# 📁 Folder with the test resumes
RESUME_DIR = Path(__file__).resolve().parent / "milestone 2 resume pdfs"

# ✏️ Change this name to test another resume
RESUME_NAME = "tricky_sidebar.docx"


def main() -> None:
    path = RESUME_DIR / RESUME_NAME
    print(f"\n📄 Testing: {RESUME_NAME}\n")

    if not path.exists():
        print(f"❌ File not found: {path}")
        return

    try:
        parsed = parse_resume(RESUME_NAME, path.read_bytes())
    except ResumeParseError as e:
        print(f"\n❌ FAILED: {e}")
        return

    saved = save_processed(parsed)

    print("\n✅ DONE")
    print(f"   🔑 Method: {parsed.method}")
    print(f"   🔍 Text kept: {parsed.text_coverage}%")
    print(f"   📄 Pages : {parsed.pages or '-'}")
    print(f"   🔤 Words : {parsed.words}")
    print(f"   📊 Tables: {parsed.tables}")
    print(f"   💾 Saved : processed/{saved.name if saved else '(not saved)'}")
    print("\n👀 Now open that .md file and check it.")


if __name__ == "__main__":
    main()
