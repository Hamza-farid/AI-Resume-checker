"""
💾 STORAGE

WHAT
  • save_processed() → resume Markdown  → processed/<date>_<name>.md   (Milestone 2)
  • save_result()    → AI's JSON answer → results/result_<name>.json   (Milestone 4)

WHY
  • So you can open the files and check our work with your own eyes
  • Saving never crashes the app: on error → log it + return None

NOTE
  • Both folders hold REAL candidate data → they are in .gitignore
  • On Streamlit Cloud these files vanish on restart (fine for testing)

USED BY
  • app.py, tests/test_milestone2.py, core/evaluator.py
"""

import json
import re
from datetime import datetime
from pathlib import Path

import config
from core.parser import ParsedResume
from logger import get_logger

log = get_logger(__name__)


def _safe_stem(filename: str) -> str:
    stem = Path(filename).stem
    stem = re.sub(r"[^A-Za-z0-9_-]+", "_", stem).strip("_")
    return stem[:60] or "resume"


def _stamp() -> str:
    return datetime.now().strftime("%Y-%m-%d_%H%M%S")


def save_processed(parsed: ParsedResume) -> Path | None:
    """Returns the saved path, or None if saving failed (the app keeps working either way)."""
    try:
        config.PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
        path = config.PROCESSED_DIR / f"{_stamp()}_{_safe_stem(parsed.original_name)}.md"
        path.write_text(parsed.markdown, encoding="utf-8")
        log.info(f"💾 Saved '{parsed.original_name}' → {path.relative_to(config.BASE_DIR)}")
        return path
    except OSError as e:
        log.error(f"💾 Could not save '{parsed.original_name}': {e}")
        return None


def save_result(resume_name: str, payload: dict) -> Path | None:
    """Saves the full evaluation (meta + job + AI answer) as pretty JSON."""
    try:
        config.RESULTS_DIR.mkdir(parents=True, exist_ok=True)
        path = config.RESULTS_DIR / f"result_{_safe_stem(resume_name)}.json"  # same resume again → overwritten
        path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
        log.info(f"💾 Saved result for '{resume_name}' → {path.relative_to(config.BASE_DIR)}")
        return path
    except (OSError, TypeError, ValueError) as e:
        log.error(f"💾 Could not save result for '{resume_name}': {e}")
        return None
