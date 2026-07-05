"""UserPromptSubmit hook: put the user's saved LinkedIn skills in front of Claude
so IT can judge relevance to the current request.

Why not match here? A literal keyword/token overlap in Python can't connect
"build an FP&A reporting system in Excel" to a saved "FP&A finance skill" — the
words don't overlap, even though they're obviously related. So this hook doesn't
decide relevance; it RETRIEVES candidate skills and hands them to the model with
an instruction to surface any that genuinely fit. The model does the semantic
matching.

Behaviour:
  - Small catalog (<= INLINE_CAP): inject all saved skills, compactly. The model
    stays silent unless one is relevant.
  - Large catalog (> INLINE_CAP): lexically prefilter to the top INLINE_CAP so the
    injected context stays bounded, and note how many were withheld (no silent
    truncation). If nothing even loosely matches, stay silent.
  - Empty catalog or empty prompt: silent.

Always exits 0, never blocks the session, pure stdlib.
"""
import sys
import os
import json

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Emit non-ASCII safely (Windows consoles default to cp1252).
try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

# Max skills to inline into a single prompt's context.
INLINE_CAP = 40
# Truncate each summary so the digest stays compact.
SUMMARY_CHARS = 160

HEADER = (
    "[linkedin-skill-finder] The user has saved these skills from LinkedIn. "
    "If one is genuinely relevant to the user's current request, briefly tell them "
    'it exists and offer to fetch it (they can say "fetch it"); ask before '
    "installing anything. If none is relevant, do not mention this note at all."
)


def _read_prompt():
    try:
        raw = sys.stdin.read()
    except Exception:
        return ""
    if not raw:
        return ""
    try:
        data = json.loads(raw)
    except ValueError:
        return raw
    return data.get("prompt") or data.get("user_prompt") or ""


def _digest(i, entry):
    name = entry.get("name") or "Untitled skill"
    summary = (entry.get("summary") or "").strip().replace("\n", " ")
    if len(summary) > SUMMARY_CHARS:
        summary = summary[: SUMMARY_CHARS - 1].rstrip() + "…"
    tags = ", ".join((entry.get("keywords") or [])[:8])
    url = entry.get("url") or ""
    line = f"{i}. {name}"
    if summary:
        line += f" — {summary}"
    if tags:
        line += f" [tags: {tags}]"
    line += f" (link: {url})" if url else " (no link saved yet)"
    return line


def main():
    prompt = _read_prompt()
    if not prompt.strip():
        return

    try:
        import catalog_lib
    except Exception:
        return

    catalog = catalog_lib.load_catalog()
    if not catalog:
        return

    entries = catalog
    omitted = 0

    if len(catalog) > INLINE_CAP:
        ptoks = catalog_lib.tokenize(prompt)
        pnorm = catalog_lib.normalize(prompt)
        scored = [
            (catalog_lib.lexical_score(ptoks, pnorm, e), idx, e)
            for idx, e in enumerate(catalog)
        ]
        scored = [t for t in scored if t[0] > 0]
        if not scored:
            return  # big catalog, nothing even loosely matches -> stay quiet
        scored.sort(key=lambda t: (-t[0], t[1]))
        entries = [e for _, _, e in scored[:INLINE_CAP]]
        omitted = max(0, len(scored) - INLINE_CAP)

    lines = [HEADER]
    for i, entry in enumerate(entries, 1):
        lines.append(_digest(i, entry))
    if omitted:
        lines.append(
            f"(+{omitted} more saved skills also loosely matched but aren't shown; "
            "ask to search the full catalog if needed.)"
        )
    print("\n".join(lines))


if __name__ == "__main__":
    try:
        main()
    except Exception:
        pass
    sys.exit(0)
