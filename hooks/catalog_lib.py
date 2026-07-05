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


def _hash(s):
    return hashlib.sha1((s or "").encode("utf-8")).hexdigest()[:12]


def _norm_url(u):
    return (u or "").strip().lower().rstrip("/")


def entry_key(entry):
    """Identity of a skill for dedupe.

    Prefer the actual skill link (`url`) so the SAME skill found in different
    places — a saved post, a DM, the feed — collapses into ONE entry instead of
    being stored again. Fall back to the post URL, then to name+author (so DM
    entries with no post URL don't all collide on an empty key).
    """
    url = _norm_url(entry.get("url"))
    if url:
        return "u:" + _hash(url)
    post = (entry.get("post_url") or "").strip().lower()
    if post:
        return "p:" + _hash(post)
    name_author = (entry.get("name", "") + "|" + entry.get("author", "")).strip().lower()
    return "n:" + _hash(name_author)


def entry_id(post_url):
    """Backward-compatible id derived from a post URL. Prefer entry_key()."""
    return "p:" + _hash((post_url or "").strip().lower())


def _name_author(entry):
    return (
        (entry.get("name", "") or "").strip().lower(),
        (entry.get("author", "") or "").strip().lower(),
    )


def same_skill(a, b):
    """Are these two entries the same skill?

    - Both have links -> same only if the links match (different repos stay
      distinct even when the name/author are identical).
    - Same post URL -> same sighting.
    - Otherwise (at least one has no link) -> match on name+author, so a
      linkless saved-post entry and a linked DM of the same skill are recognized
      as one (and the link can then be filled in — see _enrich).
    """
    ua, ub = _norm_url(a.get("url")), _norm_url(b.get("url"))
    if ua and ub:
        return ua == ub
    pa = (a.get("post_url") or "").strip().lower()
    pb = (b.get("post_url") or "").strip().lower()
    if pa and pb and pa == pb:
        return True
    na, nb = _name_author(a), _name_author(b)
    return bool(na[0]) and na == nb


def _merge_list(existing_list, new_list):
    out = list(existing_list or [])
    seen = {str(x).lower() for x in out}
    for x in new_list or []:
        if str(x).lower() not in seen:
            out.append(x)
            seen.add(str(x).lower())
    return out


def _enrich(existing, new):
    """Fill gaps in an existing entry from a new sighting of the same skill.

    Notably: if the existing entry has no link and the new one does (the
    'saw it in a saved post without the repo link, then got the link in a DM'
    case), the link is filled in. Returns True if anything changed.
    """
    changed = False
    if not _norm_url(existing.get("url")) and _norm_url(new.get("url")):
        existing["url"] = new["url"]
        if new.get("link_source"):
            existing["link_source"] = new["link_source"]
        changed = True
    for field in ("summary", "author", "post_url", "date_added"):
        if not existing.get(field) and new.get(field):
            existing[field] = new[field]
            changed = True
    merged = _merge_list(existing.get("keywords"), new.get("keywords"))
    if merged != (existing.get("keywords") or []):
        existing["keywords"] = merged
        changed = True
    new_source = new.get("source")
    if new_source:
        sources = existing.get("sources")
        if not sources:
            sources = [existing["source"]] if existing.get("source") else []
        if new_source not in sources:
            sources.append(new_source)
            changed = True
        existing["sources"] = sources
    return changed


def tokenize(text):
    """Lowercase word tokens, minus stopwords and 1-char tokens.

    Keeps 2-char tokens so domain shorthands survive (fp, ai, ml, hr, ui, db...).
    """
    tokens = re.findall(r"[a-z0-9]+", (text or "").lower())
    return {t for t in tokens if len(t) >= 2 and t not in _STOPWORDS}


def normalize(text):
    """Lowercase, alphanumeric-only — collapses 'FP&A' / 'FP and A' toward 'fpa'."""
    return re.sub(r"[^a-z0-9]+", "", (text or "").lower())


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


def lexical_score(prompt_tokens, prompt_norm, entry):
    """Lenient lexical relevance used only to PREFILTER very large catalogs.

    Token overlap, plus a bonus when a compact keyword (e.g. 'fpa') appears as a
    substring of the normalized prompt. This is a coarse net, not the final call
    on relevance — that judgment is the model's (see recall_hook.py).
    """
    score = len(prompt_tokens & entry_tokens(entry))
    for kw in entry.get("keywords", []) or []:
        k = normalize(kw)
        if len(k) >= 3 and k in prompt_norm:
            score += 1
    return score


def add_entries(new_entries):
    """Add sightings to the catalog, deduping and enriching by skill identity.

    For each new entry: if it matches an existing skill (see same_skill), the
    existing entry is enriched with any details the new sighting adds (e.g. a
    repo link that was missing); otherwise it's appended as a new skill.

    Returns a dict: {"added": int, "enriched": int, "total": int}.
    """
    catalog = load_catalog()
    added = 0
    enriched = 0
    for new in new_entries:
        match = next((ex for ex in catalog if same_skill(ex, new)), None)
        if match is not None:
            if _enrich(match, new):
                enriched += 1
            continue
        new.setdefault("id", entry_key(new))
        catalog.append(new)
        added += 1
    if added or enriched:
        save_catalog(catalog)
    return {"added": added, "enriched": enriched, "total": len(catalog)}
