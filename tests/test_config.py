from core.config import normalize_prompt


def test_replaces_legacy_placeholders():
    raw = "[생기부] = {life_record}\n[자기소개서] = {cover_letter}"
    result = normalize_prompt(raw)
    assert "{life_record}" not in result
    assert "{cover_letter}" not in result
    assert "생활기록부" in result
    assert "자기소개서" in result


def test_prompt_without_placeholders_unchanged():
    raw = "당신은 면접관입니다. {other_braces}는 건드리지 않는다."
    assert normalize_prompt(raw) == raw
