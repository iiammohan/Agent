"""Paths, model ids and per-task effort. Everything tunable lives here."""

from __future__ import annotations

import os
from pathlib import Path

# Provider is chosen at runtime (see llm.resolve_provider): anthropic or openrouter.
# FUTUREYOU_MODEL overrides the model id for whichever provider is active.
MODEL = os.environ.get("FUTUREYOU_MODEL", "claude-opus-5")                       # Anthropic direct
OPENROUTER_MODEL = os.environ.get("FUTUREYOU_MODEL", "anthropic/claude-opus-5")  # any id OpenRouter lists
OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1"

# Effort per task: cheap for the daily reply, higher when the output is long or rare.
EFFORT = {
    "today": "medium",
    "ask": "medium",
    "onboard": "high",
    "letter": "high",
    "chapter": "high",
    "review": "medium",
}

MAX_TOKENS = {
    "today": 4096,
    "ask": 4096,
    "onboard": 4096,
    "letter": 8000,
    "chapter": 16000,
    "review": 4096,
}

ENTRIES_PER_CHAPTER = 100
LETTER_EVERY_DAYS = 90
REVIEW_EVERY_DAYS = 30
RECENT_ENTRY_DAYS = 30
MAX_AGENT_STEPS = 8
MAX_TOOL_RESULT_CHARS = 4000
MEMORY_MAX_LINES = 300


def home() -> Path:
    """Where the user's data lives. FUTUREYOU_HOME overrides the default."""
    return Path(os.environ.get("FUTUREYOU_HOME", "~/.futureyou")).expanduser()
