"""Shared helpers for the LinkedIn Skill Finder catalog.

The catalog is PERSONAL data and lives outside the plugin repo, at:
    ~/.claude/linkedin-skills-catalog.json

It is a JSON array of skill entries. See README.md for the entry schema.
Both the recall hook and the collector skill use these helpers so the
format stays consistent.
"""
import json
import os
import re
import hashlib

# Override with LSF_CATALOG_PATH (used for testing); defaults to ~/.claude/...
CATALOG_PATH = os.environ.get(
    "LSF_CATALOG_PATH",
    os.path.join(os.path.expanduser("~"), ".claude", "linkedin-skills-catalog.json"),
)

# Common words we never want to match on — keeps recall precise.
_STOPWORDS = {
    "the", "a", "an", "and", "or", "but", "for", "to", "of", "in", "on", "at",
    "by", "with", "is", "are", "was", "were", "be", "been", "being", "this",
    "that", "these", "those", "i", "you", "he", "she", "it", "we", "they", "me",
    "my", "your", "our", "help", "need", "want", "how", "do", "does", "can",
    "could", "would", "should", "please", "make", "build", "create", "get",
    "use", "using", "have", "has", "had", "will", "just", "some", "any", "from",
    "about", "into", "out", "new", "one", "all", "also", "add", "let", "lets",
}


def load_catalog():
    """Return the catalog as a list; tolerate a missing or corrupt file."""
    try:
        with open(CATALOG_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
        return data if isinstance(data, list) else []
    except (FileNotFoundError, ValueError, OSError):
        return []


def save_catalog(entries):
    """Write the catalog, creating ~/.claude if needed."""
    os.makedirs(os.path.dirname(CATALOG_PATH), exist_ok=True)
    with open(CATALOG_PATH, "w", encoding="utf-8") as f:
        json.dump(entries, f, indent=2, ensure_ascii=False)


def entry_id(post_url):
    """Stable short id derived from the LinkedIn post URL (the dedupe key)."""
    norm = (post_url or "").strip().lower()
    return hashlib.sha1(norm.encode("utf-8")).hexdigest()[:12]


def tokenize(text):
    """Lowercase word tokens, minus stopwords and very short tokens."""
    tokens = re.findall(r"[a-z0-9]+", (text or "").lower())
    return {t for t in tokens if len(t) >= 3 and t not in _STOPWORDS}


def entry_tokens(entry):
    """The set of tokens an entry can be matched on: its keywords + its name."""
    toks = set()
    for kw in entry.get("keywords", []) or []:
        toks |= tokenize(kw)
    toks |= tokenize(entry.get("name", ""))
    return toks


def score_entry(prompt_tokens, entry):
    """How many tokens the prompt shares with this entry."""
    return len(prompt_tokens & entry_tokens(entry))


def add_entries(new_entries):
    """Append new entries, skipping ones already present (by id/post_url).

    Returns the number of entries actually added.
    """
    catalog = load_catalog()
    existing = {
        e.get("id") or entry_id(e.get("post_url", "")) for e in catalog
    }
    added = 0
    for e in new_entries:
        eid = e.get("id") or entry_id(e.get("post_url", ""))
        if eid in existing:
            continue
        e["id"] = eid
        catalog.append(e)
        existing.add(eid)
        added += 1
    if added:
        save_catalog(catalog)
    return added
