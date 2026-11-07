"""
task_extractor.py
-----------------
Turns analysed sentences into structured task dictionaries.

Each task contains:
    - description
    - deadline (original expression; NOT invented)
    - priority (High / Medium / Low)
    - action_keyword
    - original_sentence
"""

import re
from datetime import datetime, timedelta
from nlp_processor import (
    analyze_text,
    tokenize_words,
    pos_tag_tokens,
    ACTION_VERBS,
    TASK_CUES,
)

# ----------------------------------------------------------------------
# Date / time patterns
# ----------------------------------------------------------------------
WEEKDAYS = r"(monday|tuesday|wednesday|thursday|friday|saturday|sunday)"
MONTHS = (r"(january|february|march|april|may|june|july|august|"
          r"september|october|november|december|jan|feb|mar|apr|jun|jul|"
          r"aug|sep|sept|oct|nov|dec)")

DATE_PATTERNS = [
    # by / before / on + weekday
    re.compile(rf"\b(?:by|before|on|until|till|due)\s+{WEEKDAYS}\b", re.I),
    # tomorrow / today / tonight (+ morning/afternoon/evening)
    re.compile(r"\b(tomorrow(?:\s+(?:morning|afternoon|evening|night))?|"
               r"tonight|today(?:\s+(?:morning|afternoon|evening))?)\b", re.I),
    # next week / next month / this week / end of day etc.
    re.compile(r"\b(next\s+(?:week|month|year)|this\s+(?:week|month|weekend)|"
               r"end\s+of\s+(?:day|week|month)|eod|eow|eom)\b", re.I),
    # "as soon as possible" / "ASAP"
    re.compile(r"\b(as\s+soon\s+as\s+possible|asap)\b", re.I),
    # "in 2 days" / "in a week"
    re.compile(r"\bin\s+\d+\s+(?:day|days|hour|hours|week|weeks)\b", re.I),
    # "before Monday morning" / "Friday evening"
    re.compile(rf"\b{WEEKDAYS}\s+(?:morning|afternoon|evening|night)\b", re.I),
    # explicit date: 12 June, 12th June, June 12, 12/06/2025, 2025-06-12
    re.compile(rf"\b\d{{1,2}}(?:st|nd|rd|th)?\s+{MONTHS}(?:\s+\d{{2,4}})?\b", re.I),
    re.compile(rf"\b{MONTHS}\s+\d{{1,2}}(?:st|nd|rd|th)?(?:\s*,?\s*\d{{2,4}})?\b", re.I),
    re.compile(r"\b\d{1,2}[/-]\d{1,2}[/-]\d{2,4}\b"),
    re.compile(r"\b\d{4}-\d{2}-\d{2}\b"),
    # bare time expressions: 5 pm, 17:30
    re.compile(r"\b\d{1,2}(?::\d{2})?\s*(?:am|pm)\b", re.I),
    re.compile(r"\b\d{1,2}:\d{2}\b"),
]

# ----------------------------------------------------------------------
# Priority keyword rules
# ----------------------------------------------------------------------
HIGH_WORDS = {
    "urgent", "urgently", "immediately", "asap", "today", "critical",
    "important", "priority", "right away", "right now", "as soon as possible",
    "high priority", "top priority", "must", "essential", "emergency",
    "deadline", "overdue",
}
MEDIUM_WORDS = {
    "soon", "this week", "upcoming", "moderate", "medium", "normal",
    "next week", "planned", "scheduled", "before",
}
LOW_WORDS = {
    "whenever", "optional", "no rush", "low priority", "someday",
    "eventually", "if possible", "nice to have", "later",
}


def detect_priority(sentence: str) -> str:
    """Keyword-based priority detection."""
    low = sentence.lower()
    if any(w in low for w in HIGH_WORDS):
        return "High"
    if any(w in low for w in MEDIUM_WORDS):
        return "Medium"
    if any(w in low for w in LOW_WORDS):
        return "Low"
    # Default for a clearly action-oriented sentence
    return "Medium"


# ----------------------------------------------------------------------
# Deadline extraction
# ----------------------------------------------------------------------
def extract_deadline(sentence: str):
    """Return the first matching date/time expression, or None."""
    matches = []
    for pattern in DATE_PATTERNS:
        for m in pattern.finditer(sentence):
            matches.append((m.start(), m.group(0).strip()))
    if not matches:
        return None
    # Earliest match in the sentence wins
    matches.sort(key=lambda x: x[0])
    return matches[0][1]


def resolve_deadline(expression: str):
    """
    Optionally resolve simple relative dates to a concrete date string.
    If unreliable, return the original expression unchanged.
    """
    if not expression:
        return "No deadline detected"
    expr = expression.strip()
    low = expr.lower()
    today = datetime.today()

    try:
        if low == "today":
            return f"Today ({today.strftime('%d %b %Y')})"
        if low == "tomorrow":
            return f"Tomorrow ({(today + timedelta(days=1)).strftime('%d %b %Y')})"
        if low.startswith("tomorrow"):
            d = (today + timedelta(days=1)).strftime('%d %b %Y')
            return f"{expr} ({d})"
        if low == "tonight":
            return f"Tonight ({today.strftime('%d %b %Y')})"
        # Otherwise keep the original expression – do not invent dates
        return expr
    except Exception:
        return expr


# ----------------------------------------------------------------------
# Task description builder
# ----------------------------------------------------------------------
def build_description(sentence: str, action_verbs) -> str:
    """
    Build a concise task description from the sentence.
    - Prefer the clause containing the action verb.
    - Strip polite/filler phrases.
    """
    text = sentence.strip().rstrip(".!?")

    # Split into clauses on punctuation/commas/semicolons
    clauses = re.split(r"[,;]|(?:\s+and\s+(?=\w))", text)
    clauses = [c.strip() for c in clauses if c.strip()]

    chosen = text
    if action_verbs:
        verb_forms = {v[0].lower() for v in action_verbs}
        for clause in clauses:
            if any(vt in clause.lower() for vt in verb_forms):
                chosen = clause
                break

    # Remove leading polite cues
    for cue in sorted(TASK_CUES, key=len, reverse=True):
        chosen = re.sub(rf"^\s*{re.escape(cue)}\s+", "", chosen, flags=re.I)
        chosen = re.sub(rf"\b{re.escape(cue)}\b", "", chosen, flags=re.I)

    # Remove temporal tails that duplicate the deadline field
    for pattern in DATE_PATTERNS:
        chosen = pattern.sub("", chosen)

    chosen = re.sub(r"\b(by|before|on|until|till|due)\s*$", "", chosen, flags=re.I)
    chosen = re.sub(r"\s{2,}", " ", chosen).strip(" ,.-")

    # Capitalise first letter
    if chosen:
        chosen = chosen[0].upper() + chosen[1:]
    else:
        chosen = sentence.strip().rstrip(".!?")

    return chosen


def pick_action_keyword(action_verbs, sentence: str) -> str:
    """Choose the most representative action verb."""
    if action_verbs:
        return action_verbs[0][0].lower()
    # Fallback: first curated verb appearing in the sentence
    for w in tokenize_words(sentence):
        if w.lower() in ACTION_VERBS:
            return w.lower()
    # Final fallback: first tagged VB*
    for word, tag in pos_tag_tokens(tokenize_words(sentence)):
        if tag.startswith("VB"):
            return word.lower()
    return "action"


# ----------------------------------------------------------------------
# Public API
# ----------------------------------------------------------------------
def extract_tasks(text: str):
    """
    Main entry point.
    Returns (tasks, analysed_sentences).
    """
    if not text or not text.strip():
        return [], []

    analysed = analyze_text(text)
    tasks = []

    for item in analysed:
        if not item["is_task"]:
            continue

        sentence = item["sentence"]
        verbs = item["action_verbs"]

        description = build_description(sentence, verbs)
        if not description or len(description.split()) < 2:
            continue

        deadline_raw = extract_deadline(sentence)
        deadline = resolve_deadline(deadline_raw)
        priority = detect_priority(sentence)
        keyword = pick_action_keyword(verbs, sentence)

        tasks.append({
            "description": description,
            "deadline": deadline,
            "priority": priority,
            "action_keyword": keyword,
            "original_sentence": sentence,
            "completed": False,
        })

    # De-duplicate by description
    seen = set()
    unique = []
    for t in tasks:
        key = t["description"].lower()
        if key in seen:
            continue
        seen.add(key)
        unique.append(t)

    return unique, analysed