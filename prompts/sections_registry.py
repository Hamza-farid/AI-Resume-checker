"""
📚 SECTIONS REGISTRY

WHAT
  • The ONE list of the 7 resume sections we score
  • Each has: key · label · emoji · default priority (low / medium / high)

WHY
  • One place to add / remove / rename a section
  • Everything else reads from here → nothing to update by hand

WHO READS THIS LIST
  prompt_builder.py → which rubric .md files go in the prompt
  schema.py         → which sections the JSON must have
  HR form           → which Low / Medium / High dropdowns to show (Milestone 5)
  charts            → which bars to draw (Milestone 6)

ADD A NEW SECTION (2 steps)
  1. Create prompts/sections/<key>.md with its rubric
  2. Add one line to SECTIONS below
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class Section:
    key: str               # used in JSON and file names
    label: str             # shown to HR
    emoji: str
    default_priority: str  # "low" | "medium" | "high"


SECTIONS: list[Section] = [
    Section("experience", "Work Experience", "💼", "high"),
    Section("skills", "Skills Depth", "🛠️", "high"),
    Section("projects", "Projects & Portfolio", "🚀", "medium"),
    Section("education", "Education", "🎓", "low"),
    Section("formatting", "Clarity & ATS Readability", "📄", "medium"),
    Section("summary", "Profile / Summary", "🧾", "low"),
    Section("certifications", "Certifications & Achievements", "🏅", "low"),
]

SECTION_KEYS = [s.key for s in SECTIONS]
SECTION_BY_KEY = {s.key: s for s in SECTIONS}
