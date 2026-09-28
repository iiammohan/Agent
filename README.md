# Future You

One sentence a day. Answered by you at 70.

You write one honest line about today ("the sky is clear", "skipped the gym again", "bored"). Future You writes back in a few sentences, in first person, quoting something you wrote before, and ends with **one small thing** the person you're becoming would do tomorrow. Every hundred sentences become a chapter of your biography, each in a different author's voice. Every few months you exchange letters.

It is small on purpose: a command line, one dependency, plain files you own. It is also a worked example of how an agent is built: a loop, a handful of tools, and a memory you can read.

## Why it's built this way

The idea most people call "manifesting" (picture it and it comes) does not hold up. Vividly imagining the outcome *lowers* effort, in twenty years of studies (Oettingen). Belief in literal manifestation correlates with risky investing and bankruptcy (Dixon, Hornsey & Hartley 2023). But four neighbouring techniques have strong evidence, and Future You is built on them:

| Evidence | What the app does with it |
|---|---|
| Feeling connected to your future self changes today's behaviour. People who wrote to their self twenty years out exercised more in the following weeks (Rutchick, Slepian, Reyes, Pleskus & Hershfield 2018). | The replies come *from* your future self, in your own words, so the connection is concrete. |
| Mental contrasting with if-then plans (WOOP) roughly doubles follow-through; implementation intentions have a medium-to-large effect on goal attainment across 94 studies (Oettingen; Gollwitzer & Sheeran 2006). | Goals are stored as Wish / Outcome / Obstacle / Plan. Nudges are if-then sentences, never affirmations. |
| Imagining the *process* beats imagining the *outcome*; the effect works through better planning and lower anxiety (Pham & Taylor 1999). | When Future You "remembers how it went", it describes the doing: the Tuesday evenings, the ten minutes. |
| Best Possible Self writing raises optimism and wellbeing, framed as a future reached after real effort (Carrillo et al. 2019, 29 studies). | Onboarding is a Best Possible Self conversation; it seeds the persona. |
| Possible selves motivate when they are detailed and feel reachable; feared selves count too (Markus & Nurius 1986). | `self.md` keeps a detailed hoped-for self and one feared self. |

Six rules follow, and they are in the system prompt: the future is earned in the story; every hope comes with its obstacle and a plan; process over outcome; quote the user's own words; be honest about not knowing; and **live it now**, so every reply ends with one thing for tomorrow. Full research notes and sources are in [PLAN.md](PLAN.md).

## Install

```bash
git clone https://github.com/iiammohan/Agent.git && cd Agent
python3 -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
export ANTHROPIC_API_KEY=...        # or `ant auth login`
futureyou onboard                   # about fifteen minutes, once
futureyou                           # then one sentence a day
```

No key yet? `futureyou --mock --trace today "the sky is clear today"` runs a scripted model so you can see the shape.

## Commands

| Command | What happens |
|---|---|
| `futureyou` / `futureyou today "..."` | Asks about yesterday's one thing (yes / no / partly), takes one sentence, replies. `--mood 1-5` is optional. |
| `futureyou onboard` | The Best Possible Self conversation. Writes `self.md`, `profile.json`, first goals. |
| `futureyou ask "should I take the job?"` | Future You answers from memory, WOOP-style, without pretending to know the outcome. |
| `futureyou letter` | You write a letter (blank line to finish), Future You writes back. Both saved. |
| `futureyou chapter` | Writes the next biography chapter once 100 entries exist (`--force` to write early). |
| `futureyou review` | Monthly review: numbers from code, one paragraph from Future You. |
| `futureyou stats` | Numbers only, no model call. |
| `futureyou export` / `delete-all` | Zip everything, or remove everything. |

`--trace` on any command prints each tool call the agent makes.

## How the agent works

```
you ──▶ futureyou (CLI) ──▶ loop.run_agent ──▶ Claude Messages API
                                 │
                                 ├─ tools (plain Python functions, all local)
                                 │    read_entries · search_entries · get_self · get_goals · update_goal
                                 │    remember · set_one_thing · get_one_thing_history · stats
                                 │
                                 └─ ~/.futureyou/  (mode 700, plain files)
                                      entries.jsonl  actions.jsonl  self.md  goals.md  memory.md
                                      letters/  book/  reviews/
```

One daily run, step by step:

1. `cli.py` opens the store. If yesterday had a one thing without an answer, it asks "Did you do it?" and records the result in `actions.jsonl`. No model call yet.
2. It takes your sentence, runs the crisis check in `safety.py` (if it trips, help information is shown instead of a reply), and appends the sentence to `entries.jsonl`.
3. `context.py` builds the request: the persona prompt plus `self.md` and `goals.md` as the **system** blocks (stable, so they're cached with `cache_control`), and the last 30 entries, `memory.md`, the check-in and today's sentence as the **user** turn, each wrapped in a tag so the model treats it as data.
4. `loop.py` runs the loop, which is the whole idea of an agent in about forty lines:

   ```python
   for _ in range(max_steps):
       response = client.create(system=system, messages=messages, tools=specs, ...)
       messages.append({"role": "assistant", "content": response["content"]})
       if response["stop_reason"] == "tool_use":
           results = [run(tool_use) for tool_use in response["content"] if it's a tool_use]
           messages.append({"role": "user", "content": results})   # all results, one turn
           continue
       return text_of(response["content"]), messages
   ```

   The model decides; your code acts; the result goes back; repeat. Tool failures become `is_error` results rather than exceptions, results are capped in size, and there's a step limit.
5. In a typical run the model calls `search_entries` to find your own words about today's topic, `get_one_thing_history` to size tomorrow's action (smaller after a miss, bigger after a streak), sometimes `remember` to keep a pattern, and `set_one_thing` to log tomorrow's action. Then it answers.
6. The reply is printed. If a chapter, letter or review is due, the CLI says so.

Files:

| File | Role |
|---|---|
| `futureyou/llm.py` | The only file that imports the SDK. Adaptive thinking, per-task effort, streaming for long output, a `MockClient` for tests. |
| `futureyou/loop.py` | The agent loop above. |
| `futureyou/tools.py` | Every tool: a function over `Store` plus a JSON schema. |
| `futureyou/context.py` | What the model sees, and where the cache boundary is. |
| `futureyou/prompts/` | The prompts, as markdown. |
| `futureyou/tasks/` | One module per command. |
| `futureyou/storage.py` | Atomic writes, confined to the home directory. |
| `futureyou/safety.py` | The crisis check. |

The rule for growing it: a new capability is a new tool, or a new front end calling the same `run_agent`, never a longer prompt. The expansion roadmap (photo and voice entries, a Telegram bot, a Dayweave adapter, semantic search, multiple future selves) is in PLAN.md §13.

## Memory

| File | Written by | Purpose |
|---|---|---|
| `entries.jsonl` | you | one line a day: `{date, text, mood}` |
| `actions.jsonl` | the agent + your check-in | the one-thing record: `{for_date, action, goal, result}` |
| `self.md` | onboarding | hoped-for self, feared self, values, voice |
| `goals.md` | the agent (`update_goal`) | WOOP goals with an obstacle log |
| `memory.md` | the agent (`remember`) | dated facts it chose to keep, capped at 300 lines |
| `letters/`, `book/`, `reviews/` | tasks | what it wrote |

## Privacy

- Everything lives in `~/.futureyou` (override with `FUTUREYOU_HOME`), created with mode 700.
- The only network call is to the Anthropic API, and only with what the current task needs: `self.md`, `goals.md`, `memory.md`, the last 30 entries and today's line. The full history is sent only when a chapter is written, and only that chapter's 100 entries.
- Your API key is read from the environment and never written by the app.
- `futureyou export` gives you a zip; `futureyou delete-all` removes everything.
- If a sentence suggests you may be in danger, the persona steps aside and the app prints help information instead. Nothing extra is logged and nothing is sent to the model.

Future You is not a therapist and doesn't give medical, financial or legal advice; the prompt says so and it will tell you when a question is outside what it should answer.

## Development

```bash
python3 tests/run_tests.py     # no dependencies needed
pytest                         # if installed
```

Tests never call the API; they drive the loop with `MockClient` and scripted responses. Conventions for adding tools and tasks are in `.claude/skills/futureyou-dev/SKILL.md`. Work happens on `claude/...` branches and lands in `Main` through a pull request.
