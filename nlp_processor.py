"""
nlp_processor.py
----------------
Handles all NLP preprocessing and linguistic analysis:
- Sentence tokenization
- Word tokenization
- Stop-word removal
- POS tagging
- Named Entity Recognition (via NLTK chunking)
- Action verb identification
"""

import re
import nltk
from nltk.tokenize import sent_tokenize, word_tokenize
from nltk.corpus import stopwords
from nltk import pos_tag, ne_chunk
import streamlit as st

@st.cache_resource
def download_nltk_data():
    nltk.download('punkt', quiet=True)
    nltk.download('punkt_tab', quiet=True)
    nltk.download('stopwords', quiet=True)
    nltk.download('averaged_perceptron_tagger', quiet=True)
    nltk.download('averaged_perceptron_tagger_eng', quiet=True)
    nltk.download('maxent_ne_chunker', quiet=True)
    nltk.download('maxent_ne_chunker_tab', quiet=True)
    nltk.download('words', quiet=True)

download_nltk_data()

# ----------------------------------------------------------------------
# One-time NLTK resource download (safe if already present)
# ----------------------------------------------------------------------
def ensure_nltk_resources():
    resources = [
        ("tokenizers/punkt", "punkt"),
        ("tokenizers/punkt_tab", "punkt_tab"),
        ("corpora/stopwords", "stopwords"),
        ("taggers/averaged_perceptron_tagger", "averaged_perceptron_tagger"),
        ("taggers/averaged_perceptron_tagger_eng", "averaged_perceptron_tagger_eng"),
        ("chunkers/maxent_ne_chunker", "maxent_ne_chunker"),
        ("chunkers/maxent_ne_chunker_tab", "maxent_ne_chunker_tab"),
        ("corpora/words", "words"),
    ]
    for path, name in resources:
        try:
            nltk.data.find(path)
        except LookupError:
            try:
                nltk.download(name, quiet=True)
            except Exception:
                pass


ensure_nltk_resources()

# ----------------------------------------------------------------------
# Static resources
# ----------------------------------------------------------------------
try:
    STOP_WORDS = set(stopwords.words("english"))
except Exception:
    STOP_WORDS = set()

# Action verbs commonly used for tasks (imperative base form)
ACTION_VERBS = {
    "complete", "finish", "submit", "send", "email", "call", "review",
    "prepare", "create", "update", "fix", "check", "verify", "schedule",
    "organize", "organise", "plan", "write", "read", "discuss", "attend",
    "book", "order", "buy", "pay", "confirm", "reply", "respond", "share",
    "upload", "download", "install", "test", "deploy", "design", "build",
    "contact", "message", "remind", "deliver", "collect", "arrange",
    "clean", "print", "draft", "approve", "ask", "tell", "inform", "notify",
    "follow", "meet", "start", "stop", "set", "assign", "track", "monitor",
    "manage", "process", "handle", "close", "open", "fill", "record",
    "note", "explain", "present", "analyze", "analyse", "research",
}

# Words that often introduce a task/instruction
TASK_CUES = {
    "please", "kindly", "need to", "needs to", "have to", "has to",
    "must", "should", "remember to", "don't forget", "do not forget",
    "make sure", "ensure", "let's", "lets", "we will", "i will",
    "you will", "we need", "i need", "you need", "also", "and then",
    "then", "after that", "next", "finally",
}


# ----------------------------------------------------------------------
# Core preprocessing functions
# ----------------------------------------------------------------------
def clean_text(text: str) -> str:
    """Normalise whitespace and remove stray characters."""
    if not text:
        return ""
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def split_sentences(text: str):
    """Sentence tokenization with a regex fallback."""
    text = clean_text(text)
    if not text:
        return []
    try:
        sents = sent_tokenize(text)
    except Exception:
        sents = re.split(r"(?<=[.!?])\s+|\n+", text)
    return [s.strip() for s in sents if s.strip()]


def tokenize_words(sentence: str):
    """Word tokenization with a regex fallback."""
    try:
        return word_tokenize(sentence)
    except Exception:
        return re.findall(r"\b\w+[\w'-]*\b", sentence)


def remove_stopwords(tokens):
    """Return tokens without stop-words (keeps punctuation)."""
    return [t for t in tokens if t.lower() not in STOP_WORDS]


def pos_tag_tokens(tokens):
    """POS tagging with a simple fallback."""
    try:
        return pos_tag(tokens)
    except Exception:
        return [(t, "NN") for t in tokens]


def extract_entities(sentence: str):
    """NER using NLTK's ne_chunk (works best on capitalised text)."""
    try:
        tokens = word_tokenize(sentence)
        tags = pos_tag(tokens)
        tree = ne_chunk(tags)
        entities = []
        for subtree in tree:
            if hasattr(subtree, "label"):
                entity = " ".join(c[0] for c in subtree)
                entities.append((entity, subtree.label()))
        return entities
    except Exception:
        return []


def find_action_verbs(sentence: str):
    """
    Return a list of (verb, tag) that are likely task verbs.
    Combines a curated vocabulary with POS VB* tags.
    """
    tokens = tokenize_words(sentence)
    tagged = pos_tag_tokens(tokens)
    verbs = []
    for word, tag in tagged:
        low = word.lower()
        if low in ACTION_VERBS or (tag.startswith("VB") and low in ACTION_VERBS):
            verbs.append((word, tag))
        elif tag in ("VB", "VBP", "VBZ") and low in ACTION_VERBS:
            verbs.append((word, tag))
    # Fallback: if nothing found, return first VB* token
    if not verbs:
        for word, tag in tagged:
            if tag.startswith("VB"):
                verbs.append((word, tag))
                break
    return verbs


# ----------------------------------------------------------------------
# Sentence classification
# ----------------------------------------------------------------------
def is_task_sentence(sentence: str) -> bool:
    """
    Decide whether a sentence contains an actionable task.
    Uses action verbs, modal cues, and imperative heuristics.
    """
    if not sentence or len(sentence.split()) < 2:
        return False

    low = sentence.lower()

    # Cue phrases such as "please", "make sure", "need to"
    if any(cue in low for cue in TASK_CUES):
        return True

    tokens = tokenize_words(sentence)
    tagged = pos_tag_tokens(tokens)

    # Any curated action verb present?
    has_action_verb = any(t[0].lower() in ACTION_VERBS for t in tagged)
    if has_action_verb:
        return True

    # Imperative start: first word is a base-form verb
    for word, tag in tagged:
        if word.isalpha():
            if tag in ("VB", "VBP") and word.lower() in ACTION_VERBS:
                return True
            break

    return False


# ----------------------------------------------------------------------
# Convenience bundle used by the extractor
# ----------------------------------------------------------------------
def analyze_text(text: str) -> list:
    """
    Returns a list of dicts, one per sentence, with all NLP artefacts.
    """
    results = []
    for sent in split_sentences(text):
        tokens = tokenize_words(sent)
        filtered = remove_stopwords(tokens)
        tagged = pos_tag_tokens(tokens)
        verbs = find_action_verbs(sent)
        entities = extract_entities(sent)
        results.append({
            "sentence": sent,
            "tokens": tokens,
            "filtered_tokens": filtered,
            "pos_tags": tagged,
            "action_verbs": verbs,
            "entities": entities,
            "is_task": is_task_sentence(sent),
        })
    return results
