---
name: linkedin-skill-finder
description: Collect Claude/AI skills shared on LinkedIn (saved posts or messages) into a personal catalog, and fetch a saved skill on request. Use when the user wants to scan or collect LinkedIn for skills, save skills they've seen on LinkedIn, or pull in a previously-saved LinkedIn skill.
---

# LinkedIn Skill Finder

Two jobs: **collect** skills people share on LinkedIn into a personal catalog, and
**fetch** a saved skill when the user wants it. (Automatic *recall* — surfacing a
relevant saved skill at the start of a task — is handled separately by this
plugin's `UserPromptSubmit` hook, not by this skill.)

The catalog is personal data stored at `~/.claude/linkedin-skills-catalog.json`.
The helper module `hooks/catalog_lib.py` (in this plugin) reads/writes it and
does the deduping — use it rather than hand-editing the JSON.

## When to collect

Trigger phrases: "scan my LinkedIn for skills", "collect the skills I saved on
LinkedIn", "/collect-linkedin-skills", "add these LinkedIn skills to my catalog".

### Sources (toggle)

- `--saved` (**default**): the user's LinkedIn Saved list — `linkedin.com/my-items/saved-posts/`. Most reliable.
- `--messages`: LinkedIn messages/DMs — `linkedin.com/messaging/`.
- `--all`: run saved, then messages.

There is no feed scan — reading the saved list and DMs covers what people share,
and crawling the home feed is the noisiest, most crawler-like surface.

### How to collect

Follow **`references/collection-guide.md`** step by step. In short:

1. Call `mcp__claude-in-chrome__tabs_context_mcp` first. Reuse a logged-in
   LinkedIn tab if one exists; otherwise open a new tab to the source URL.
2. Read the page (`get_page_text` / `read_page`) and scroll a **bounded** number
   of times (default 5). Tell the user the scroll cap — never imply you saw more.
   **Randomize each scroll** — vary both the distance (a random 1–3 posts) and the
   pause between passes (a random ~0.5–1.5s), never a fixed rhythm. The guide has
   a `javascript_tool` snippet that does both with `Math.random()`.
3. For each post, judge: *is this sharing a Claude/AI skill?* If yes, extract
   `name`, `summary`, `author`, `post_url`, and the **skill link (`url`)**:
   - Check the post **body** first.
   - **If there's no link in the body, read the first comment** — people put the
     repo link there so LinkedIn won't suppress the post for an external link.
     Take the link from the top comment and set `link_source: "first_comment"`.
   - If a link is only ever in the body, set `link_source: "body"`.
4. Generate 4–8 lowercase `keywords` per skill (these drive recall matching).
5. Dedupe + append with `catalog_lib.add_entries(...)`. Identity is the skill's
   `url`, so the same skill seen in a saved post AND a DM becomes one entry. When
   two sightings match, the existing entry is **enriched** rather than duplicated:
   a missing `url` gets filled from the sighting that has it (e.g. the link was
   only in a DM), `summary`/`author` gaps are filled, keywords are merged, and
   every source it was seen in is recorded in `sources`. Different repos with the
   same name stay separate.
6. Report: how many posts scanned, how many new skills added, how many existing
   entries were enriched, and list the new names. If nothing new, say so.

To save, write the entries you built as a JSON array to a temp file and pipe it
through the plugin's helper (it handles ids + dedupe and reports the count):

```bash
python "${CLAUDE_PLUGIN_ROOT}/hooks/collect_add.py" < entries.json
```

Links are **auto-cleaned of lead/tracking parameters** on save (utm_*, click ids,
LinkedIn `trk`/`li_fat_id`, etc. — via `catalog_lib.clean_url`), so you don't need
to strip them yourself. It cleans query params only; it does not unwrap shortened
links like `lnkd.in` (the fetch step follows those redirects).

## Safety — stay a reader, never a bot

This runs read-only in the user's own logged-in Chrome, which is why it's low-risk
to LinkedIn. Keep it that way (full list in `references/collection-guide.md`):

- **Read only.** Never connect, follow, like, comment, post, or send messages.
  Clicking a comment icon to *read* the first comment is fine; changing any state
  on LinkedIn is not.
- **Never unattended.** Don't drive this from `/loop`, cron, `schedule`, or any
  recurring/background trigger — it runs interactively, on demand.
- **Bounded, randomized scroll** (default 5 passes; random distance and delay).
- **Don't loop on failures** — after 2–3 tries, record what you have and move on.
- **No headless/API scraping and never log in for the user** — only read what's
  visible in their real, already-authenticated tab.

## When to fetch

If the user says "fetch it" / names a saved skill (often right after the recall
hook surfaced one), or asks to install a catalogued skill:

1. Look it up in the catalog and take its `url`.
2. `WebFetch` the url.
   - If it resolves to a repo/gist/page containing a `SKILL.md` (or an installable
     plugin): summarize what it does and **ask before installing**. On approval,
     install into `~/.claude/skills/<name>/` (or add its marketplace/plugin).
   - If it's an article or a dead link: summarize / report, don't install.
3. Never run or install external content without explicit confirmation.

## Entry schema

```json
{
  "name": "PDF Form Filler",
  "summary": "Fills PDF form fields from a data file.",
  "url": "https://github.com/user/pdf-form-filler",
  "link_source": "body | first_comment",
  "post_url": "https://linkedin.com/posts/...",
  "author": "Jane Doe",
  "source": "saved | messages",
  "sources": ["saved", "messages"],
  "keywords": ["pdf", "form", "fill", "document"],
  "date_added": "YYYY-MM-DD"
}
```

`source` is where it was first seen; `sources` (added automatically on enrichment)
lists every place it's since turned up.

`id` is added automatically by `catalog_lib` (from the skill `url`, falling back
to `post_url`); don't set it yourself.
