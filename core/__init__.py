"""The app's logic, kept separate from Flask so it can be tested and reused on its own.

Vendored (copied) from the author's JobDesk project (core/ package, November 2026) and trimmed to what
this app needs:
    text.py      word helpers (tokens, Finnish-friendly word matching)          unchanged
    rank.py      ranked shortlist against a student's skills                     unchanged
    llm.py       small Claude API client using only the standard library         settings simplified
    finnish.py   Finnish-requirement classifier + baseline_v1 + quote check      mock answer changed
    batch.py     ads from pasted text or CSV                                     URL fetching removed
    evaluate.py  accuracy, confusion matrix, precision/recall, Markdown report   now runnable with -m
Nothing else from JobDesk is included: no user data, CVs, database or scraper code.
"""
