"""Prompt loading. Prompts are markdown files next to this module so they can
be read and edited without touching code. Curly braces in them are template
fields filled by `render`.
"""

from __future__ import annotations

from importlib import resources

# Rotating voices for the Historian. Chapter N uses AUTHORS[(N-1) % len].
AUTHORS: list[tuple[str, str]] = [
    ("Ernest Hemingway", "Short declarative sentences. Concrete nouns. Emotion shown through action and omission, never named."),
    ("Jane Austen", "Wry, precise, socially observant. Long balanced sentences with a gentle irony toward the protagonist's self-deceptions."),
    ("Kurt Vonnegut", "Plain words, short paragraphs, dark humour, sudden tenderness. Occasional aside to the reader. 'So it goes' is off limits; find your own refrain."),
    ("Haruki Murakami", "Calm first-person-adjacent detachment, everyday details (coffee, records, weather) given quiet weight, a hint of the uncanny."),
    ("Kazuo Ishiguro", "Restrained, formal, memory-haunted narration that circles what it cannot say directly."),
    ("Chimamanda Ngozi Adichie", "Warm, clear, specific; attentive to family, food, and small social frictions; unafraid of directness."),
    ("Terry Pratchett", "Affectionate satire, footnote-style asides, absurdity that lands on something true."),
    ("Toni Morrison", "Lyrical, rhythmic, weighted sentences; the past pressing on the present; dignity in ordinary lives."),
]


def load(template: str) -> str:
    return resources.files("futureyou.prompts").joinpath(template).read_text(encoding="utf-8")


def render(template: str, **fields: str) -> str:
    text = load(template)
    for key, value in fields.items():
        text = text.replace("{" + key + "}", str(value))
    return text
