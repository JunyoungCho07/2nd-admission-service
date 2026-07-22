from core.parsing import parse_questions_from_report


def test_extracts_after_primary_marker():
    text = "서론...\n---[대표_예상_질문_시작_마커]---\n1. 질문 하나\n2. 질문 둘"
    assert parse_questions_from_report(text) == "1. 질문 하나\n2. 질문 둘"


def test_falls_back_to_korean_markers():
    text = "분석 내용\n## 대표 예상 질문\n1. 질문"
    assert parse_questions_from_report(text) == "1. 질문"

    text2 = "분석 내용\n### 대표 질문 5개\n1. 질문"
    assert parse_questions_from_report(text2) == "5개\n1. 질문"


def test_returns_original_when_no_marker():
    text = "마커가 전혀 없는 텍스트"
    assert parse_questions_from_report(text) == text


def test_empty_input():
    assert parse_questions_from_report("") == ""


def test_marker_priority_order():
    text = "대표 질문\n낮은 우선순위\n---[대표_예상_질문_시작_마커]---\n높은 우선순위"
    assert parse_questions_from_report(text) == "높은 우선순위"
