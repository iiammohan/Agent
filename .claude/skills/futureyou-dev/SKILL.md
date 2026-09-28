---
name: futureyou-dev
description: Conventions for working on the Future You agent in this repo. Load before adding a tool, a task, a prompt, or a test, and before opening a PR.
---

# Working on Future You

## Branch rules
- Never push to `Main`. All work goes to a `claude/...` branch and lands via a PR into `Main`; only the repo owner merges.
- `PLAN.md` is the source of truth for scope. If you deviate from it, say so in the PR body under "Deviations from PLAN.md".

## Layout
- `futureyou/llm.py` is the only file that imports the SDK. Everything else works with plain Messages-API dicts, so tests never need `anthropic` installed.
- `futureyou/loop.py` is the agent loop. Keep it readable; it is documented in the README line by line.
- `futureyou/tools.py` holds every tool as a pure function over `Store` plus a `Tool` entry in `build_tools()`. Tools return strings, never raise past the loop, and keep results under `config.MAX_TOOL_RESULT_CHARS`.
- `futureyou/tasks/<command>.py` is one command each: gather context, run the agent, save, print. I/O goes through `ask`/`say` parameters so tests can drive them.
- `futureyou/prompts/*.md` are the prompts. `{field}` placeholders are filled by `prompts.render()`. All user data goes into the request inside tags (`<self>`, `<goals>`, `<memory>`, `<recent_entries>`, `<today>`) and the prompt says tagged content is data, not instructions.

## Adding a capability
1. New capability = new tool (or a new front end calling `loop.run_agent`), never a longer prompt.
2. Write the function in `tools.py`, register it in `build_tools()` with a JSON schema (`additionalProperties: false`, `required` listed).
3. Add a test in `tests/test_tools.py` for the function and, if a task uses it, a scripted `MockClient` run in `tests/test_tasks.py`.
4. If the model should know when to use it, add one sentence to the relevant prompt.

## Tests
- `python3 tests/run_tests.py` (no dependencies) or `pytest` if installed. Both must be green before a push.
- Tests use `tests/helpers.py` (`fresh_store`, `seed_entries`, `write_self`) and `MockClient` with `text_response` / `tool_response`. Never hit the real API in tests.
- Dates: pass `today=` explicitly in tests so they don't depend on the wall clock.

## Model calls
- Model id and per-task effort live in `config.py`. Adaptive thinking is always on. Long outputs (chapters) stream.
- Prompt caching: `context.system_blocks()` puts `cache_control` on the last stable block. Don't put anything that changes per run into the system blocks.

## Safety and privacy
- `safety.is_crisis()` runs on every user sentence before any model call. Don't weaken it; add patterns with a test.
- Nothing leaves the machine except the API request. No analytics, no other hosts. `storage.Store.path()` refuses paths outside the home directory; keep it that way.
