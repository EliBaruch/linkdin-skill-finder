"""UserPromptSubmit hook: surface saved LinkedIn skills relevant to the prompt.

Reads the hook payload from stdin, keyword-matches the user's prompt against the
personal catalog (~/.claude/linkedin-skills-catalog.json), and prints a short
note about the top matches. Whatever this prints on stdout is injected into the
model's context for that turn.

Design rules:
  - Never block or slow the session: pure stdlib, no network, always exit 0.
  - Stay quiet unless there is a genuine match (empty catalog / no match => no output).
"""
import sys
import os
import json

# Make catalog_lib importable regardless of the working directory.
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Ensure we can emit non-ASCII (e.g. the 💡 marker) on any platform,
# including Windows consoles that default to cp1252.
try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

# Minimum shared-token count for an entry to be considered relevant.
SCORE_THRESHOLD = 2
MAX_RESULTS = 3


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
        return raw  # not JSON — treat the whole payload as the prompt
    return data.get("prompt") or data.get("user_prompt") or ""


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

    ptoks = catalog_lib.tokenize(prompt)
    if not ptoks:
        return

    scored = []
    for entry in catalog:
        s = catalog_lib.score_entry(ptoks, entry)
        if s >= SCORE_THRESHOLD:
            scored.append((s, entry))
    if not scored:
        return

    scored.sort(key=lambda x: x[0], reverse=True)

    lines = ["💡 Saved LinkedIn skills that may fit this task:"]
    for i, (_, entry) in enumerate(scored[:MAX_RESULTS], 1):
        name = entry.get("name", "Untitled skill")
        summary = entry.get("summary", "")
        url = entry.get("url") or entry.get("post_url") or ""
        piece = f"{i}. {name}"
        if summary:
            piece += f" — {summary}"
        if url:
            piece += f" ({url})"
        lines.append(piece)
    lines.append(
        'If one fits, say "fetch it" (or name it) and pull it in — '
        "ask the user before installing anything."
    )
    print("\n".join(lines))


if __name__ == "__main__":
    try:
        main()
    except Exception:
        # Never let a hook error surface to the user.
        pass
    sys.exit(0)
