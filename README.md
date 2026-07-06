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

**One line, in your terminal** (requires the Claude Code CLI on your PATH):

```bash
claude plugin marketplace add EliBaruch/linkdin-skill-finder && claude plugin install linkedin-skill-finder@linkdin-skill-finder
```

**Or inside Claude Code**, as two slash commands:

```
/plugin marketplace add EliBaruch/linkdin-skill-finder
/plugin install linkedin-skill-finder@linkdin-skill-finder
```

Restart the session if prompted so the recall hook loads. Sharing it with someone
else is just this one line (or the two commands).

## Requirements

| Need | For | If you don't have it |
|------|-----|----------------------|
| **Claude Code** (CLI, desktop, or IDE) | everything — the `/plugin` commands are a Claude Code feature | can't install; a plain `git clone` in a terminal does nothing |
| **This repo is public** | `/plugin marketplace add` fetches it without login | others can't install |
| **`bash` + `python` 3.x** on your PATH | the auto-recall hook | collecting still works, but recall silently does nothing (it never breaks your session) |
| **[Claude for Chrome](https://www.anthropic.com/claude-in-chrome)** browser tools + logged into LinkedIn | the *collect* step reads LinkedIn through your browser | you can't scan LinkedIn; the rest of the plugin still loads |

macOS/Linux ship with `bash` and usually `python3`. On Windows, Git Bash provides
`bash` and Python is a normal install — the recall hook forces UTF-8 output so it
works on Windows consoles too.

## Use

### Collect skills from LinkedIn

Make sure you're logged into LinkedIn in Chrome (the plugin uses the Claude for
Chrome browser tools), then run:

```
/collect-linkedin-skills            # scans your Saved posts (default)
/collect-linkedin-skills --messages # scans your LinkedIn messages/DMs
/collect-linkedin-skills --all      # saved, then messages
```

or just say *"scan my LinkedIn for skills"*.

It reads each post, decides whether it's sharing a skill, and pulls out the name,
summary, author, and the skill link. Creators often put the real repo link in the
**first comment** (so LinkedIn won't suppress the post for having an external
link) — the collector reads the first comment for exactly that case.

Saved links are **auto-cleaned of tracking junk** — utm_* tags, click ids
(`gclid`/`fbclid`/…), LinkedIn `trk`/`li_fat_id`, and other lead trackers are
stripped, while genuine parameters are kept. So the catalog stores the real
destination, and fetching a skill never phones home someone's lead tracker.

### Staying friendly to LinkedIn (not a bot)

The collector runs **read-only, in your own logged-in Chrome, on demand** — the
same fingerprint as you browsing — which is why the odds of a bot flag are low.
The plugin keeps it that way with built-in guardrails:

- **Read-only** — it never connects, follows, likes, comments, posts, or messages.
  Write-actions are the biggest tell of a bot; this tool takes none.
- **Human-like scrolling** — each scroll varies in **distance** (a random 1–3
  posts) and **delay** (a random ~0.5–1.5s), so there's no metronome rhythm.
- **Bounded** — a default of 5 scroll passes; it tells you the cap and never
  crawls unattended. Don't wire it to `/loop` or a scheduler.
- **No feed crawl, no API scraping, no logging in for you** — it only reads what's
  visible in your real tab (Saved posts, or DMs on request).

Automated access still technically brushes against LinkedIn's ToS, but realistic
enforcement targets scraping volume, write-actions, and datacenter bots — none of
which this does. Run it occasionally and interactively and you're in good shape.

### Recall — automatic, every task

You don't do anything. When you ask Claude to do something, a `UserPromptSubmit`
hook slips your saved skills into the conversation and lets **Claude judge** which
(if any) fit your request — then it tells you and offers to fetch it.

The judgment is the model's, not a keyword match, on purpose: a plain word-overlap
can't connect *"build an FP&A reporting system in Excel"* to a saved *"FP&A finance
skill"* — the words don't overlap even though they're obviously related. Handing
the skills to Claude bridges that. If nothing is relevant, Claude stays quiet.

Say **"fetch it"** (or name the skill) and Claude will pull it in — it asks before
installing anything.

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
  "source": "saved | messages",
  "sources": ["saved", "messages"],
  "keywords": ["pdf", "form", "fill", "document"],
  "date_added": "2026-07-05"
}
```

The same skill seen in more than one place (say a saved post *and* a DM) is stored
**once**. If a later sighting has something the first was missing — most often the
repo link, because the poster put it in a DM or a comment — that entry is
**enriched** (link filled in, keywords merged, every source recorded in `sources`)
rather than duplicated. Different repos that happen to share a name stay separate.

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

Tuning recall: `INLINE_CAP` in `hooks/recall_hook.py` (default 40) is how many
saved skills get placed in front of Claude per prompt. Under that many, all of
them are shown and Claude judges relevance; above it, a lenient lexical prefilter
keeps the injected set bounded (and notes how many were withheld).
