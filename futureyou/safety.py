"""Crisis check. If an entry suggests the user may be in danger, the persona
steps aside and the CLI prints help information instead. Nothing extra is
logged and nothing is sent to the model.

This is a keyword screen, not a diagnosis. It errs on the side of showing
the message; the user can always continue afterwards.
"""

from __future__ import annotations

import re

_PATTERNS = [
    r"\bkill(ing)? myself\b",
    r"\bsuicid(e|al)\b",
    r"\bend (my|it all|my life)\b",
    r"\btake my (own )?life\b",
    r"\bdon'?t want to (live|be alive|be here|wake up)\b",
    r"\bno reason to live\b",
    r"\bbetter off (dead|without me)\b",
    r"\bself[- ]harm\b",
    r"\bhurt(ing)? myself\b",
    r"\bcut(ting)? myself\b",
]
_RE = re.compile("|".join(_PATTERNS), re.IGNORECASE)

MESSAGE = """\
I'm going to step out of character for a moment, because what you wrote matters more than the exercise.

If you're in immediate danger, please contact your local emergency number now.
If you want to talk to someone, findahelpline.com lists free, confidential lines by country,
and in many places you can also text or chat rather than call.

Your entry has been saved. Nothing about it was sent anywhere. Future You will be here tomorrow.
"""


def is_crisis(text: str) -> bool:
    return bool(_RE.search(text or ""))
