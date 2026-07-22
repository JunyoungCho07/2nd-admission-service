"""AI 생성 보고서 파싱."""

# 초기 분석 보고서에서 '대표 질문' 섹션을 찾는 마커 후보 (앞에서부터 우선 적용).
# 첫 번째 마커는 PROMPT_SECRET에 동일 문자열을 넣어두면 가장 정확하게 동작한다.
QUESTION_MARKERS = (
    "---[대표_예상_질문_시작_마커]---",
    "대표 예상 질문",
    "대표 질문",
)


def parse_questions_from_report(text_block: str, markers: tuple[str, ...] = QUESTION_MARKERS) -> str:
    """마커 이후의 텍스트(질문 목록)를 추출한다. 마커가 없으면 원문 전체를 반환한다."""
    if not text_block:
        return ""
    for marker in markers:
        _, found, tail = text_block.partition(marker)
        if found:
            return tail.strip()
    return text_block
