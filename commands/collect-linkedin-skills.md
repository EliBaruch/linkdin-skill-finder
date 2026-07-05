---
description: Scan LinkedIn (Saved posts by default) for shared Claude/AI skills and add them to your catalog
argument-hint: "[--saved | --messages | --feed | --all]"
---

Use the **linkedin-skill-finder** skill to collect skills shared on LinkedIn and
add them to the personal catalog at `~/.claude/linkedin-skills-catalog.json`.

Source to scan (from arguments; default `--saved` if empty): `$ARGUMENTS`

Follow the skill's `references/collection-guide.md`:
1. Check current browser tabs; reuse a logged-in LinkedIn tab or open one.
2. Navigate to the chosen source and read it with a bounded scroll.
3. For each skill post, extract name / summary / author / post URL and the skill
   link — **checking the first comment when the body has no link**.
4. Dedupe + append via `hooks/collect_add.py`.
5. Report posts scanned, new skills added, and their names.
