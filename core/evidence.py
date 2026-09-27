"""
📌 EVIDENCE CHECK (is every AI quote really in the resume?)

WHAT
  • check_quote()    → "verified" / "close" / "not_found" for one quote
  • check_evidence() → checks every section's quotes, adds the result to the AI answer

WHY
  • Evidence is our proof. If the AI rewords a quote or invents one, HR must SEE that.
  • 100% free: plain Python text matching, no AI

HOW
  both texts → lowercase, no markdown (** # |), no punctuation, single spaces
  quote found as one piece in the resume     → ✅ verified
  ≥ 85% of the quote's words in the resume   → 🟡 close   (small rewording, joined lines)
  less                                       → ⚠️ not_found

ADDS TO THE AI ANSWER
  sections[key]["evidence_check"] = [{"quote": ..., "status": "verified" | "close" | "not_found"}, ...]

USED BY
  • core/evaluator.py → frontend/results.py (✅/🟡/⚠️ next to each quote)
"""

import re

from prompts.sections_registry import SECTIONS

CLOSE_MATCH = 0.85
_WORD = re.compile(r"\w+", re.UNICODE)


def _norm(text: str) -> str:
    return " ".join(w.lower() for w in _WORD.findall(text or ""))


def check_quote(quote: str, resume_norm: str, resume_words: set[str]) -> str:
    q = _norm(quote)
    if not q:
        return "not_found"
    if q in resume_norm:
        return "verified"
    words = q.split()
    found = sum(1 for w in words if w in resume_words)
    return "close" if found / len(words) >= CLOSE_MATCH else "not_found"


def check_evidence(data: dict, resume_text: str) -> dict[str, int]:
    """Adds evidence_check to every section. Returns counts, e.g. {"verified": 12, "close": 1, "not_found": 0}."""
    resume_norm = _norm(resume_text)
    resume_words = set(resume_norm.split())
    counts = {"verified": 0, "close": 0, "not_found": 0}
    for s in SECTIONS:
        sec = data["sections"][s.key]
        checks = []
        for quote in sec.get("evidence", []):
            status = check_quote(quote, resume_norm, resume_words)
            counts[status] += 1
            checks.append({"quote": quote, "status": status})
        sec["evidence_check"] = checks
    return counts
