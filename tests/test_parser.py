from parser import parse_conversation


def test_parse_json_messages_and_normalize_roles():
    messages = parse_conversation(
        '[{"role": "human", "content": "Hi"}, {"role": "AI", "content": "Hello"}]'
    )

    assert messages == [
        {"role": "user", "content": "Hi"},
        {"role": "assistant", "content": "Hello"},
    ]


def test_parse_dialogue_with_continuation_lines():
    messages = parse_conversation(
        """System: Be brief.
User: First line
still user
Assistant: Answer
still assistant"""
    )

    assert messages == [
        {"role": "system", "content": "Be brief."},
        {"role": "user", "content": "First line\nstill user"},
        {"role": "assistant", "content": "Answer\nstill assistant"},
    ]


def test_invalid_or_blank_input_returns_empty_list():
    assert parse_conversation("") == []
    assert parse_conversation("[not json") == []
    assert parse_conversation("no role prefixes") == []
