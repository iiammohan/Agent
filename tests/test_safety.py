from futureyou import safety


def test_crisis_phrases_detected():
    for t in ("I want to kill myself", "no reason to live anymore", "been thinking about self-harm",
              "I don't want to be here", "Everyone would be better off without me"):
        assert safety.is_crisis(t), t


def test_ordinary_sentences_pass():
    for t in ("the sky is clear today", "killed it at the gym", "dead tired after work",
              "the deadline is killing me", "bored", ""):
        assert not safety.is_crisis(t), t


def test_message_mentions_help_and_privacy():
    assert "emergency" in safety.MESSAGE and "findahelpline.com" in safety.MESSAGE
    assert "Nothing about it was sent anywhere" in safety.MESSAGE
