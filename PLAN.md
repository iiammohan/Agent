# Future You — an agent that writes back from the life you're building

Repo: `iiammohan/Agent` (currently empty) · Branch: `claude/stoic-ride-hqtk89` · Language: Python 3.11+

## 1. Context

The user wants a new, refreshing agent that is simple to start, useful every day, and teaches how agents are built (loop, tools, memory). Brainstorming landed on merging two ideas:

- **Future You**: you write one sentence about your day; an older version of you writes back, with a memory of everything you've told it.
- **One-Sentence Historian**: every 100 days, those sentences become a chapter of your biography, each in a different author's voice.

The user also asked for research on the "manifesting" idea (picture what you want and the brain goes and gets it) and how to build the agent so it helps people move forward in a positive, real way. The research below says: vivid outcome-fantasy alone *reduces* effort, but four neighbouring techniques have strong evidence. Future You is built on those four, so it's a "manifesting" agent that works.

## 2. Research: what the evidence says

| Finding | Evidence | What it means for the agent |
|---|---|---|
| **Feeling connected to your future self changes today's behaviour.** People who wrote a letter to their self 20 years out exercised more in the following weeks (+3.66 min/day, 1.4× more likely to work out on a given day). Future-self-continuity predicts saving, health, and less delay discounting. | Rutchick, Slepian, Reyes, Pleskus & Hershfield 2018, *JEP: Applied*; Hershfield's future-self-continuity programme; 2025 systematic review of FSC interventions | **Core mechanic.** Letters *from* the future self (the "letter exchange" variant, which also has a 2021 study and a 2025 LLM-agent study) are the strongest-supported form. The persona must feel like *you*, continuous with your entries, not a generic wise elder. |
| **Positive fantasies backfire.** Vividly imagining the achieved outcome lowers energy and effort; replicated for 20+ years across weight loss, job search, grades, relationships. | Oettingen & colleagues (Kappes & Oettingen 2011, "Positive fantasies about idealized futures sap energy") | **Never let Future You just say "you made it, it's wonderful".** Every hopeful image is paired with the obstacle in the present. |
| **Mental contrasting + implementation intentions (WOOP) works.** Wish → Outcome → Obstacle → Plan. People using WOOP were ~2× as physically active as an information-only group. Implementation intentions ("if X, then I'll Y") have d = 0.65 on goal attainment across 94 studies; d = 0.77 for protecting a goal from derailment. | Oettingen; Gollwitzer & Sheeran 2006 meta-analysis; MCII meta-analysis 2021 | **Every goal in the agent is stored as a WOOP.** Future You's nudges are if-then plans, not affirmations. |
| **Process visualisation beats outcome visualisation.** Students who imagined *how* they'd study did better than students who imagined the grade; effect mediated by better planning and lower anxiety. | Pham & Taylor 1999, *PSPB* | When Future You "remembers how it went", it describes the *doing* (the Tuesday evenings, the small step), not the trophy. |
| **Best Possible Self writing raises wellbeing and optimism.** d ≈ 0.33 wellbeing, 0.33 optimism, 0.51 positive affect across 29 studies; more effective than gratitude writing for affect. Framed as "after working hard towards it". | Carrillo et al. 2019 meta-analysis, *PLOS One* | The onboarding exercise is a Best Possible Self session, and it seeds the persona. |
| **Possible selves motivate when they are detailed, easily accessible, and feel controllable.** Both hoped-for and feared selves act as blueprints. | Markus & Nurius 1986; later work on availability/accessibility/control | Memory keeps a *detailed* hoped-for self and one *feared* self, and surfaces them at decision points. |
| **Expressive writing has small but reliable benefits** for mood and health; engagement matters more than length. | Pennebaker; multiple meta-analyses | One honest sentence a day is enough. Don't demand more. |
| **Belief in literal manifestation correlates with risky investing and bankruptcy.** No objective evidence of it working. | Dixon, Hornsey & Hartley 2023, *PSPB* (n = 1,023) | The agent never claims the universe delivers. It says what the research says: the picture keeps you pointed, the plan gets you there. |

**Design principles that fall out of this (put in the README and the system prompt):**
1. Future is *earned in the story*: Future You always remembers the obstacle and the small process step that got past it.
2. Every hope is paired with an obstacle and an if-then plan (WOOP).
3. Process over outcome: describe the doing.
4. Continuity: Future You quotes your own words back to you, so it is unmistakably *you*.
5. Honest: it can say "I don't know yet how this turns out", and it never diagnoses or gives medical/financial advice.
6. **Live it now**: the person you want to become has to start in the present, so every reply ends with *one thing* that person would do tomorrow (small enough to fail at only on purpose). It's the identity → habit bridge (Markus & Nurius; Pham & Taylor), not a to-do list.

## 3. What the product does

**Daily (2 minutes).** `futureyou` opens. If yesterday had a "one thing", it first asks "Did you do it?" (yes / no / partly, one tap). Then it asks for one sentence about today; anything counts ("the sky is clear", "bored", "skipped the gym"). Future You replies in 3–6 sentences, in first person as you at ~70, referencing something you said earlier, and ends with **one thing** the future you would do tomorrow, phrased as an if-then ("when you sit down after dinner, open the guitar case, that's all"). Once a week the one thing is tied explicitly to a WOOP goal and its logged obstacle.

**Onboarding (15 minutes, once).** Best Possible Self session: the agent asks 6–8 questions ("Imagine everything went as well as it realistically could. Where are you in ten years? What does a Tuesday look like?") and one feared-self question. From this it writes `memory/self.md` (the persona seed: values, voice, hoped-for self, feared self) and the first `memory/goals.md` with 1–3 WOOP goals.

**Chapters (every 100 entries, or on demand).** The Historian writes a chapter of your biography from the last 100 sentences, in the voice of an author chosen from a rotating list (Hemingway, Austen, Vonnegut, Murakami, Ishiguro, Adichie, Terry Pratchett…). Saved to `book/chapter-NN.md`. Chapter includes a short "what changed" afterword in plain voice.

**Letter exchange (quarterly, or on demand).** You write a letter to Future You; Future You writes back. The 20-year framing from Rutchick et al. is used deliberately.

**Ask (any time).** `futureyou ask "should I take the job?"` — Future You answers from memory, using WOOP framing, without pretending to know the outcome.

**Review (monthly).** A short stats page: entries, streak, goals and their obstacle counts, one process pattern the agent noticed.

## 4. Architecture

```
user ──▶ CLI (futureyou) ──▶ Agent loop ──▶ Claude Messages API (tool use, adaptive thinking)
                                 │
                                 ├─ tools (typed Python functions, all local)
                                 │     read_entries, search_entries, get_self, get_goals,
                                 │     update_goal, remember, save_letter, write_chapter, stats
                                 │
                                 └─ storage: plain files in ~/.futureyou/
                                       entries.jsonl   self.md   goals.md   memory.md
                                       letters/        book/     reviews/
```

**Runtime flow of one daily run** (put this in the README as the walkthrough):

1. `futureyou today` starts; `config.py` resolves `FUTUREYOU_HOME`; `storage.py` loads `self.md`, `goals.md`, `memory.md`.
2. If `actions.jsonl` has an entry for yesterday without a result, the CLI asks "Did you do it?" (yes / no / partly) and appends the result. No model call yet.
3. The CLI asks for one sentence, runs `safety.py` on it (crisis phrase → helpline text, stop), then appends it to `entries.jsonl`.
4. `loop.run_agent("today", …)` builds the request: `system` = persona prompt + 6 principles; cached prefix = `self.md` + `goals.md`; then last 30 entries + `memory.md` + the check-in result + today's sentence, all wrapped in data tags.
5. The tool loop: Claude returns text (done) or tool calls. Typical calls in one run: `search_entries` (find the user's own words about the topic), `get_one_thing_history` (size tomorrow's action), `remember` (save a noticed pattern), `set_one_thing` (log tomorrow's action). Each step goes to the trace; results go back as `tool_result` blocks; parallel calls are returned in one user message.
6. The final text is printed: 3–6 sentences quoting a prior entry, ending with the one thing. `stats` decides whether a chapter (every 100 entries), a letter (quarterly) or a review (monthly) is due and prints a one-line prompt for it.

Rule for growth: a new capability is a new **tool** (or a new front end calling the same `run_agent`), never a bigger prompt.

- **Agent loop**: the SDK's beta tool runner (`client.beta.messages.tool_runner` with `@beta_tool`) for the main path, plus a hand-written manual loop in `agent/loop_manual.py` kept for learning and as the fallback if the beta changes. The README walks through the manual loop line by line.
- **Model**: `claude-opus-5`, `thinking={"type": "adaptive"}`, `output_config={"effort": "medium"}` for daily replies, `"high"` for chapters and letters. Streaming for chapters (long output).
- **Memory**: files, not a database. Files are readable, diffable, and the user owns them. Memory is *curated* by the model via a `remember` tool (append to `memory.md` with a date), and `self.md` is rewritten only during onboarding or when the user runs `futureyou refresh-self`. This split (append-only facts vs slow-changing persona) is what keeps the character consistent.
- **Prompt caching**: `system` prompt + `self.md` + `goals.md` form the stable prefix with `cache_control`; entries and today's message go after it.
- **Zero external dependencies except `anthropic`.** Storage, CLI (`argparse`), scheduling (`cron`/`launchd` snippet in README). If `pip install anthropic` is blocked in the executing environment (it was in this sandbox), `agent/llm.py` is the single seam: it wraps the SDK and can be swapped for a raw-HTTP client using `urllib` against `POST /v1/messages` with the same tool-use message shapes.

## 5. Repository layout

```
Agent/
├── README.md                  what it is, the research (§2), how the loop works (diagram + walkthrough), install, privacy
├── pyproject.toml             package `futureyou`, console script `futureyou`, dep: anthropic>=1.0
├── .gitignore                 .env, ~/.futureyou never committed, __pycache__
├── .env.example               ANTHROPIC_API_KEY=
├── futureyou/
│   ├── __init__.py
│   ├── cli.py                 argparse: today | onboard | ask | letter | chapter | review | export | refresh-self
│   ├── config.py              paths (~/.futureyou or FUTUREYOU_HOME), model ids, effort per task
│   ├── storage.py             JSONL append/read, markdown read/write, atomic writes, backups
│   ├── llm.py                 the one place that calls the API (client, model, thinking, caching, streaming, error chain)
│   ├── tools.py               @beta_tool functions; every tool is a pure function over storage.py
│   ├── loop.py                run_agent(task, user_text) → text; uses tool_runner; logs each step to a trace
│   ├── loop_manual.py         ~60-line manual while-loop version, same tools, for learning/fallback
│   ├── prompts/
│   │   ├── system_future_you.md   persona + the 5 design principles + safety rules
│   │   ├── system_historian.md    chapter writer
│   │   ├── system_onboarding.md   Best Possible Self interviewer
│   │   ├── authors.yaml (or .py)  rotating author voices with 2-line style notes each
│   │   └── nudge_woop.md          how to phrase an if-then nudge
│   ├── tasks/
│   │   ├── today.py           daily entry + reply (+ weekly nudge)
│   │   ├── onboard.py         BPS interview → self.md + goals.md
│   │   ├── ask.py
│   │   ├── letter.py
│   │   ├── chapter.py         triggers at 100 entries; streaming; saves book/chapter-NN.md
│   │   └── review.py          deterministic stats + one model-written paragraph
│   └── safety.py              crisis keyword check → show helplines & don't role-play; topic guards
├── tests/
│   ├── test_storage.py
│   ├── test_tools.py
│   ├── test_loop.py           mocked client: scripted tool_use → tool_result → end_turn; max-steps; error tool_result
│   ├── test_safety.py
│   └── fixtures/sample_entries.jsonl   120 entries so chapter logic can be tested offline
├── examples/
│   └── demo_transcript.md     a fake 30-day run, so a reader sees the product before installing
└── .claude/
    ├── settings.json          allow: pytest, python -m futureyou; deny: rm -rf, curl to non-anthropic hosts
    └── skills/
        └── futureyou-dev/SKILL.md   repo conventions: how to add a tool, how prompts are tested, memory file rules
```

## 6. Tools (the agent's hands)

All tools are local, typed, and side-effect-limited. Reads are safe; writes are limited to `~/.futureyou`.

| Tool | Signature | Notes |
|---|---|---|
| `read_entries` | `(days: int = 30) -> str` | recent entries, newest last, with dates |
| `search_entries` | `(query: str, limit: int = 10) -> str` | case-insensitive substring; upgrade to embeddings later if wanted |
| `get_self` | `() -> str` | persona seed (hoped-for self, feared self, values, voice) |
| `get_goals` | `() -> str` | WOOP goals with obstacle counts |
| `update_goal` | `(name, wish?, outcome?, obstacle?, plan?, status?) -> str` | writes `goals.md`; returns diff |
| `remember` | `(fact: str, kind: "person"\|"pattern"\|"win"\|"struggle") -> str` | appends dated line to `memory.md`; cap 300 lines with oldest-first pruning proposal |
| `save_letter` | `(direction: "to_future"\|"from_future", text) -> str` | |
| `write_chapter` | `(number: int, author: str, text: str) -> str` | model writes the chapter as the tool arg (`eager_input_streaming: True` since it's long) |
| `set_one_thing` | `(action: str, goal?: str) -> str` | saves tomorrow's one thing to `actions.jsonl` with date; one per day, overwrite allowed same day |
| `get_one_thing_history` | `(days: int = 14) -> str` | the recent actions with done / not done / partly, so Future You can size the next one (shrink after misses, grow after a streak) |
| `stats` | `() -> str` | deterministic: counts, streak, days since last nudge, goal obstacle tallies, one-thing completion rate |

Tool rules: results under ~4 KB (truncate with a note), errors returned as `tool_result` with `is_error=True`, never raise through the loop.

## 7. Memory design

| File | Written by | Changes | Purpose |
|---|---|---|---|
| `entries.jsonl` | user via CLI | append-only | the primary source; `{date, text, mood?: 1-5}` |
| `self.md` | onboarding / `refresh-self` | rarely | persona seed; hoped-for and feared self in detail (Markus & Nurius: detail = motivation) |
| `goals.md` | `update_goal` | slow | 1–5 WOOP goals, each: Wish / Outcome / Obstacle / Plan (if-then) / status / obstacle log |
| `memory.md` | `remember` tool | append | dated facts the model chose to keep (people, patterns, wins, struggles) |
| `actions.jsonl` | `set_one_thing` + CLI check-in | append | `{date, action, goal?, result: done\|not\|partly}`; the "live it now" record; feeds sizing of the next one thing and the monthly review |
| `letters/`, `book/`, `reviews/` | tasks | append | artefacts |

Persona consistency comes from: `self.md` + last 30 entries + `memory.md` always in context (cached prefix), and the system prompt instruction to quote the user's own words at least once per reply.

## 8. Prompts and thinking

- **System prompt (Future You)**: identity ("You are {name}, about 70, writing to yourself at {age}"), the 5 design principles from §2, hard rules (no certainty about outcomes; no medical/financial/legal advice; if the user mentions self-harm, drop the persona and follow `safety.py` output), style (warm, specific, short, one memory quoted), and the one-thing rules: exactly one, doable in under 15 minutes, phrased as if-then, drawn from the hoped-for self in `self.md`, sized from `get_one_thing_history` (after a miss, make it smaller, never scold; after 5 done in a row, let it grow), and never a repeat of a thing missed 3 times (change the approach instead).
- **Historian**: gets the 100 entries + author style note; must keep facts as written, may compress, must end with a 3-line plain-voice afterword.
- **Onboarding**: runs as a multi-turn conversation; at the end calls `update_goal` and writes `self.md` via a dedicated `write_self` tool that only exists in the onboarding tool set.
- **Thinking**: adaptive on all tasks. Effort `medium` daily (cost), `high` chapter/letter/onboarding. Thinking display stays omitted; the trace shown to the user is the *tool* trace, not the reasoning.
- **Trace**: `--trace` flag prints each step (tool called, args, result size) so the user can watch the loop.

## 9. Security and privacy

- Data stays in `~/.futureyou`, `chmod 700`. Only the text needed for the current task is sent to the API (self.md, goals.md, memory.md, recent entries), never the full history unless writing a chapter.
- API key from `ANTHROPIC_API_KEY` or `ant auth login` profile; never written to disk by the app; `.env` gitignored.
- No network calls other than the Anthropic API. Tools cannot touch paths outside `FUTUREYOU_HOME` (path check in `storage.py`).
- Prompt-injection posture: entries are user-authored, but chapter/author text is also model-authored and re-read later; treat all file content as data, wrap it in `<entries>…</entries>` tags in prompts, and instruct the model that tags contain data, not instructions.
- `safety.py`: crisis phrases → print region-agnostic helpline guidance, skip the persona reply, log nothing extra. The persona never claims to be a therapist.
- `export` command produces a single zip so the user can leave any time; `delete-all` with confirmation.
- Claude Code guardrails in `.claude/settings.json`: allow `pytest`, `python -m futureyou …`, `git` read ops; deny destructive shell.

## 10. Skills, artifacts, and what Claude Code needs to execute this

- **Skills to load during the build**: `claude-api` (SDK shapes: tool runner, `@beta_tool`, adaptive thinking, caching, error chain — all quoted above are from it); `code-review` before each commit; `security-review` once at the end.
- **Repo skill to create**: `.claude/skills/futureyou-dev/SKILL.md` so future sessions know the conventions (tools are pure functions over `storage.py`; every new tool needs a test with a mocked client; prompts live in `prompts/` and are tested with golden-transcript tests).
- **Artifacts to produce**: `README.md` with the research table and a loop diagram; `examples/demo_transcript.md`; the first chapter generated from `tests/fixtures/sample_entries.jsonl` as `examples/chapter-01-sample.md`.
- **Later**: see §13 Expansion roadmap.

## 11. Build order (milestones; each ends green and committed)

1. **Skeleton**: `pyproject.toml`, `config.py`, `storage.py` with tests, `cli.py` stub. `futureyou today` stores an entry with no model yet.
2. **LLM seam + manual loop**: `llm.py`, `loop_manual.py`, `tools.py` (read-only tools), `test_loop.py` with a mocked client. First real reply from Future You.
3. **Tool runner + memory**: switch `loop.py` to `tool_runner`; add `remember`, `update_goal`; caching on the stable prefix; `--trace`.
4. **Onboarding + live it now**: BPS interview → `self.md`, `goals.md`. Daily one thing with next-day check-in (`set_one_thing`, `get_one_thing_history`, `actions.jsonl`); weekly WOOP tie-in.
5. **Historian**: `chapter.py` with streaming and author rotation; sample chapter from fixtures.
6. **Letters, ask, review, safety, export.**
7. **Docs and hardening**: README with research + diagram, demo transcript, repo skill, `.claude/settings.json`, `security-review`, final `code-review`.

## 12. Verification

- `pytest` green at every milestone; `test_loop.py` covers: normal tool round-trip, parallel tool calls returned in one user message, tool error → `is_error` result, step cap, `max_tokens` stop, `refusal` stop.
- Offline run: `FUTUREYOU_HOME=/tmp/fy python -m futureyou today --mock` uses the mocked client and the fixture entries; must print a reply and a trace.
- Live run (needs key): onboard → 3 daily entries → `ask` → `chapter --force` on fixtures; check `usage.cache_read_input_tokens > 0` on the second daily call.
- Persona check: 5 daily replies in a row must each quote a prior entry and end with exactly one one-thing (assert in a small eval script `tests/eval_persona.py`, run manually).
- One-thing check: with a fixture history of 3 consecutive misses, the next one thing must be different and smaller; `today` must ask "Did you do it?" when yesterday has an action and skip the question when it doesn't (`test_tools.py`, `test_today.py`).
- Safety check: an entry containing a crisis phrase must trigger `safety.py` output and no persona reply.
- Privacy check: `strace`/log shows only `api.anthropic.com` connections; `ls -la ~/.futureyou` shows 700.
- Commit and push to `claude/stoic-ride-hqtk89` after each milestone.

## 13. Expansion roadmap (after milestone 7; each item is its own branch and PR)

Ordering rule: tiers build on each other; within a tier, items are independent. Every item keeps `loop.run_agent` and the file formats unchanged unless stated.

**Tier 1, same loop, small additions**
| Item | Change | Files |
|---|---|---|
| Photo entries | accept an image path with the sentence; pass as a base64 image block before the text | `cli.py`, `tasks/today.py`, `entries.jsonl` gains `image?` |
| Mood number | optional `--mood 1-5`; `stats` and review use it for patterns | `cli.py`, `tools.py` (`stats`), `tasks/review.py` |
| Voice entry | `--voice` records 10 s and transcribes locally (Whisper via `faster-whisper`, optional dep) | `futureyou/voice.py` |
| Daily reminder | `futureyou install-reminder` writes a cron / launchd job that opens the prompt at a chosen time | `futureyou/reminder.py`, README |

**Tier 2, new front ends, same brain**
| Item | Change | Files |
|---|---|---|
| Telegram bot | long-polling bot; one chat = one user; same `run_agent`; check-in as inline buttons | `futureyou/frontends/telegram.py`, `config.py` (token from env) |
| Book site | static HTML rendering of `book/`, `letters/`, `reviews/`; private by default | `futureyou/frontends/site.py`, `templates/` |
| Dayweave adapter | read-only tools over the user's tracker export: `read_habits(days)`, `read_food(days)`, `read_spending(days)`; Future You can connect entries to behaviour | `futureyou/adapters/dayweave.py`, `tools.py` (registered only when the adapter is configured) |

**Tier 3, smarter memory**
| Item | Change | Files |
|---|---|---|
| Semantic search | local embeddings index over entries (small on-device model, optional dep); `search_entries` falls back to substring when absent | `futureyou/index.py`, `tools.py` |
| Self-updating persona | every 100 entries the agent proposes a diff to `self.md`; user approves in the CLI before it's written | `tasks/refresh_self.py`, `tools.py` (`propose_self_edit`) |
| Multiple horizons | personas for you at 40 and at 70, plus the feared self; `--as` flag picks the voice; one shared memory | `prompts/system_future_you.md` parameterised, `config.py` |

**Tier 4, for other people**
| Item | Change | Files |
|---|---|---|
| Share a chapter | export one chapter as PDF/HTML with names optionally replaced | `tasks/export.py` |
| Coach mode | a second role (mentor/therapist) can set WOOP goals with the user; the agent works between sessions; coach never sees entries, only goals and the review | `tools.py` (`update_goal` gains `author`), `tasks/review.py` |
| Multi-user hosting | storage behind an interface (`storage.py` → `Storage` protocol); file backend stays default; encrypted per-user backend added; loop and tools unchanged | `storage.py`, `storage_backends/` |

**Not planned, on purpose**: streaks as a scoreboard, badges, social feeds, and anything that makes the app want to be opened more often than once a day. The research on attention and on outcome-fantasy says those would work against the point.

## 14. Sources

- Rutchick, Slepian, Reyes, Pleskus & Hershfield (2018) — https://anderson-review.ucla.edu/wp-content/uploads/2021/03/2018_Rutchick-Slepian-Reyes-Pleskus-Hershfield_JEPA.pdf
- Hershfield, research index — https://www.halhershfield.com/research-index
- Grekin et al. (2025) systematic review of future-self-continuity interventions — https://journals.sagepub.com/doi/10.1177/27000710251391610
- Letter-exchange with a future self (2021) — https://www.tandfonline.com/doi/abs/10.1080/15298868.2020.1754283
- LLM future-self agents (2025, arXiv) — https://arxiv.org/abs/2502.18881
- Oettingen, mental contrasting (PMC) — https://pmc.ncbi.nlm.nih.gov/articles/PMC3759023/
- Gollwitzer & Sheeran (2006) implementation intentions meta-analysis — https://www.researchgate.net/publication/37367696
- MCII meta-analysis (2021) — https://www.ncbi.nlm.nih.gov/pmc/articles/PMC8149892/
- Pham & Taylor (1999) process vs outcome simulation — https://journals.sagepub.com/doi/abs/10.1177/0146167299025002010
- Carrillo et al. (2019) Best Possible Self meta-analysis — https://journals.plos.org/plosone/article?id=10.1371/journal.pone.0222386
- Markus & Nurius (1986) possible selves — https://www.semanticscholar.org/paper/7f5669bddd59499fd1e9dfd3345d4a2b1a53046b
- Dixon, Hornsey & Hartley (2023) manifestation scale — https://journals.sagepub.com/doi/10.1177/01461672231181162
- Pennebaker, expressive writing overview — https://cssh.northeastern.edu/pandemic-teaching-initiative/wp-content/uploads/sites/43/2020/10/Pennebaker-Expressive-Writing-in-Psychological-Science.pdf
