# LinkedIn Skill Finder

A Claude Code plugin that solves a specific problem: you keep seeing people share
Claude **skills** on LinkedIn, you save the posts, and then you forget they exist
and never use them.

This plugin:

1. **Collects** the skills people share on LinkedIn — name, summary, and link —
   into a personal catalog.
2. **Recalls** them for you automatically: whenever you start *any* task, it
   checks the catalog and surfaces the relevant saved skill, then offers to fetch
   and install it.

## Install

```
/plugin marketplace add EliBaruch/linkdin-skill-finder
/plugin install linkedin-skill-finder@linkdin-skill-finder
```

Restart the session if prompted so the recall hook loads. Sharing it with someone
else is just those two commands.

Requirements: `bash` and `python` (3.x) on your PATH — the recall hook uses them
(the same assumption as Anthropic's official `security-guidance` plugin). If
Python is missing the hook simply stays silent; it never breaks your session.

## Use

### Collect skills from LinkedIn

Make sure you're logged into LinkedIn in Chrome (the plugin uses the Claude for
Chrome browser tools), then run:

```
/collect-linkedin-skills            # scans your Saved posts (default)
/collect-linkedin-skills --messages # scans your LinkedIn messages/DMs
/collect-linkedin-skills --feed     # scans your home feed
/collect-linkedin-skills --all      # all three
```

or just say *"scan my LinkedIn for skills"*.

It reads each post, decides whether it's sharing a skill, and pulls out the name,
summary, author, and the skill link. Creators often put the real repo link in the
**first comment** (so LinkedIn won't suppress the post for having an external
link) — the collector reads the first comment for exactly that case.

### Recall — automatic, every task

You don't do anything. When you ask Claude to do something, a `UserPromptSubmit`
hook quietly checks your catalog and, if a saved skill looks relevant, notes it:

```
💡 Saved LinkedIn skills that may fit this task:
1. PDF Form Filler — Fills PDF form fields from a data file. (https://github.com/...)
If one fits, say "fetch it" ...
```

Say **"fetch it"** (or name the skill) and Claude will pull the skill in — it asks
before installing anything.

## Where your data lives

- The **plugin** (this repo) is shareable code with no personal data.
- Your **catalog** is personal and lives at `~/.claude/linkedin-skills-catalog.json`.
  It is created on first collect and never committed to this repo.

Catalog entry shape:

```json
{
  "id": "<auto: hash of post_url>",
  "name": "PDF Form Filler",
  "summary": "Fills PDF form fields from a data file.",
  "url": "https://github.com/user/pdf-form-filler",
  "link_source": "body | first_comment",
  "post_url": "https://linkedin.com/posts/...",
  "author": "Jane Doe",
  "source": "saved | messages | feed",
  "keywords": ["pdf", "form", "fill", "document"],
  "date_added": "2026-07-05"
}
```

Why a dedicated JSON file instead of Claude's built-in memory? Recall has to work
across *all* your projects, and the hook needs machine-readable `keywords` to
match against — a single shared catalog file does both.

## How it's built

```
.claude-plugin/
  plugin.json          # the plugin
  marketplace.json     # this repo lists itself as a marketplace
skills/linkedin-skill-finder/
  SKILL.md             # collect + fetch behavior
  references/collection-guide.md
hooks/
  hooks.json           # registers the UserPromptSubmit recall hook
  recall_hook.py       # prompt -> catalog match -> surface top skills
  catalog_lib.py       # load/append/dedupe/keyword helpers
  collect_add.py       # append collected entries (used by the collector)
  lsf-python.sh        # finds a python interpreter for the hook
commands/
  collect-linkedin-skills.md
```

Tuning recall precision: `SCORE_THRESHOLD` in `hooks/recall_hook.py` (default 2 —
the number of shared keywords required before a skill is surfaced).
