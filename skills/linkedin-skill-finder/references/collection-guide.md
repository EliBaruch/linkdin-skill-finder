# Collection guide — reading LinkedIn with the browser tools

This is the detailed playbook the `linkedin-skill-finder` skill follows when
collecting. It uses the `mcp__claude-in-chrome__*` tools. Load them via
ToolSearch first if they're deferred (batch them in one call):

```
select:mcp__claude-in-chrome__tabs_context_mcp,mcp__claude-in-chrome__navigate,mcp__claude-in-chrome__get_page_text,mcp__claude-in-chrome__read_page,mcp__claude-in-chrome__computer,mcp__claude-in-chrome__find,mcp__claude-in-chrome__tabs_create_mcp
```

## 0. Session setup

1. Call `tabs_context_mcp` **first**. If the user already has a LinkedIn tab
   open and logged in, reuse it. Otherwise `tabs_create_mcp` a new tab.
2. If LinkedIn shows a login wall, stop and tell the user to log in (suggest they
   run the login themselves), then resume. Do not try to authenticate for them.

## 1. Navigate to the chosen source

| Toggle       | URL                                        |
|--------------|--------------------------------------------|
| `--saved`    | `https://www.linkedin.com/my-items/saved-posts/` |
| `--messages` | `https://www.linkedin.com/messaging/`      |

`--all` runs saved → messages in sequence. (There is no feed scan — reading your
own saved list and DMs is enough, and crawling the home feed is both noisy and the
most crawler-like surface. See the safety guardrails at the bottom.)

## 2. Load content (bounded, human-like scroll)

- `get_page_text` (fast) or `read_page` to capture what's visible.
- Scroll to load more: default **5 scroll passes**, capturing text after each.
  LinkedIn uses infinite scroll — you only ever see what's loaded, so **state the
  cap to the user** ("scanned the first ~N posts"). Never imply full coverage.
- If the user asks for more, raise the pass count; otherwise keep it bounded so
  the run stays quick.

### Randomize every scroll — never scroll on a fixed rhythm or fixed distance

A metronome (same pause, same distance every pass) is the single most bot-like
thing a reader can do. So make each pass different:

- **Vary the distance.** Scroll a random **1–3 posts' worth** each pass — three
  posts one time, one the next, two after that. No set stride.
- **Vary the delay** between passes — a random pause each time, e.g. roughly
  **0.5s / 1.0s / 1.5s** (or any value in that range), never the same twice.
- Do both **inside one `javascript_tool` call**, where `Math.random()` is
  available, so the randomness is real rather than you eyeballing it. Randomize
  the scroll amount and an in-page `setTimeout` pause together:

```js
// one randomized, human-like scroll pass
const posts = 1 + Math.floor(Math.random() * 3);            // 1–3 posts
const px    = posts * (600 + Math.floor(Math.random() * 300)); // vary length
window.scrollBy(0, px);
await new Promise(r => setTimeout(r, 500 + Math.random() * 1000)); // ~0.5–1.5s
```

Then capture the newly loaded text and repeat for the next pass with fresh random
values. Applies to **both** saved posts and DMs.

## 3. Identify skill posts

For each post, judge with normal reading comprehension: *is this sharing a Claude
or AI "skill" (a SKILL.md / plugin / agent skill / prompt pack) that a person
could install or reuse?* Signals: the words "skill", "SKILL.md", "Claude Code
plugin", "agent skill", "/plugin install", a GitHub/gist link to a skill repo.

Skip generic thought-leadership posts with no reusable artifact.

## 4. Extract the link — body first, then the FIRST COMMENT

This is the important bit. Many creators **do not** put the repo link in the post
body, because LinkedIn's algorithm suppresses posts with external links. Instead
they write "link in the comments" and drop the real link in the **first comment**
(usually their own).

For each skill post:

1. Look for the skill link in the **post body**. If found → `link_source: "body"`.
2. If the body has no link (or says "link in comments / below / 👇"):
   - Open the comments. Use `computer` to click the post's comment icon or the
     "most relevant comment" preview, or `find` the comments region, then
     `read_page` / `get_page_text`.
   - Take the skill link from the **top / first comment** (prefer a comment by the
     post's author). Set `link_source: "first_comment"`.
3. If still no link anywhere, keep the entry but leave `url` empty and set
   `link_source: "body"` — record the `post_url` so the user can revisit it.

## 5. Build entries

For each captured skill, build an object:

```json
{
  "name": "<short skill name>",
  "summary": "<one line: what it does>",
  "url": "<skill repo/gist/page link, or empty>",
  "link_source": "body | first_comment",
  "post_url": "<the LinkedIn post permalink>",
  "author": "<poster name>",
  "source": "saved | messages",
  "keywords": ["4-8", "lowercase", "topic", "words"],
  "date_added": "<today's date, YYYY-MM-DD>"
}
```

Keyword tips: include the domain/nouns someone would type when they need this
skill (e.g. a PDF form-filler → `pdf`, `form`, `fill`, `document`, `acroform`).
Good keywords are what make recall fire later.

## 6. Save + report

- Write the array to a temp file and run:
  `python "${CLAUDE_PLUGIN_ROOT}/hooks/collect_add.py" < entries.json`
- It dedupes by the skill's `url` (falling back to `post_url`, then name+author),
  so the same skill seen in a saved post and a DM becomes one entry, and
  re-running collection is safe. When a later sighting has details the first
  lacked — most importantly a repo link that was missing — it **enriches** the
  existing entry instead of adding a duplicate (`collect_add.py` reports both the
  added and enriched counts).
- Report: posts scanned, new skills added, and the list of new names. Mention the
  scroll cap. If nothing new, say so plainly.

## Notes / failure modes

- LinkedIn's DOM changes often — rely on reading the page text and clicking by
  what you see, not on fixed selectors.
- If comment expansion fails after 2–3 tries, record the entry with the body link
  (or empty url) and move on; don't loop.
- Messages/DMs: skill links usually sit inside a conversation thread — open the
  relevant thread, read it, and extract shared links the same way.

## Safety guardrails — stay a reader, never a bot

This collector runs inside the user's own logged-in Chrome via the browser
extension, read-only and on demand. That is exactly why it's low-risk to LinkedIn.
Keep it that way — these are hard rules, not suggestions:

- **Read only. Never take write-actions.** No connecting, following, liking,
  commenting, posting, or sending messages — ever. Clicking a post's comment icon
  purely to *read* the first comment is fine; anything that changes state on
  LinkedIn is off-limits. Write-actions are the single biggest line between a
  reader and a bot in LinkedIn's eyes.
- **Never run this unattended.** Do not drive this skill from `/loop`, a cron
  job, `schedule`, or any background/recurring trigger. It runs when the user asks
  for it, interactively. A steady automated cadence is what builds a machine-like
  signature.
- **Keep the scroll bounded and human-like.** Default 5 passes; only raise it when
  the user explicitly asks. Always randomize distance and delay (section 2). Never
  crank passes into the dozens as a default.
- **Don't loop on failures.** If comment expansion (or any interaction) fails
  after 2–3 tries, record what you have and move on. A rapid retry storm of clicks
  is exactly what automation heuristics flag.
- **Prefer `--saved`.** Reading your own static saved list is the least suspicious
  surface. `--messages` is fine on demand; don't deep-crawl every DM thread.
- **Never scrape via LinkedIn's private/voyager API or a headless browser, and
  never log in on the user's behalf.** Only read what's visible in the user's real,
  already-authenticated tab.
