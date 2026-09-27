# How to score

Every score is a **whole number from 1 to 10**, judged against the job HR described. A great resume for a different job can still score low for this one.

| Score | Meaning |
|---|---|
| 9-10 | Exceptional for this role. Clear, specific, measurable proof. Rare, so give it only when it is earned. |
| 7-8 | Strong. Meets the requirements with good evidence. |
| 5-6 | Acceptable. Partly meets the requirements, or the evidence is thin. |
| 3-4 | Weak. Little relevance or little evidence. |
| 1-2 | Very weak, or almost no relevant content. |

## Rules
- **Evidence first, score last.** For each part, first collect 1-3 short quotes from the resume, then write the summary, and only then decide the score. If you cannot quote anything relevant, the score cannot be above 4.
- **Quotes are copied word for word.** Copy one continuous piece of text exactly as it appears in the resume. Do not add words (like "(skills list)"), do not join separate lines into one quote, do not describe the resume in your own words. The app checks every quote against the resume and marks the ones it cannot find.
- **Claims versus proof.** "Expert in Python" is a claim. "Built a Python pipeline processing 2M rows a day" is proof. Proof scores higher.
- **Numbers matter.** Measurable results (percentages, money, users, time saved) are strong evidence.
- **Not applicable.** If a section is missing from the resume and this job does not need it, set `applicable` to false and `score` to 0. The app then leaves it out. If the job does need it, set `applicable` to true and score it low.
- **Confidence.** Use `high` when the evidence is clear, `medium` when some things are unclear (vague dates, unclear role), and `low` when you had to interpret a lot.
- **Be specific.** Write "Add numbers to the 2023 sales role, such as revenue or team size", not "improve experience".

## Priorities (Low / Medium / High)
HR marks each section as Low, Medium, or High priority for this job. Priority tells you where HR wants **more detail**: give High-priority sections more careful evidence and more interview questions.

**Priority never changes a score.** A 7 means the same thing in a High section and a Low section. The app applies the priorities as weights when it calculates the final score.
