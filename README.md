# 면접관 AI (2nd-admission-service)

과학고 2차 전형(면접) 대비 서비스. 생활기록부·자기소개서 PDF를 업로드하면
Google Gemini가 예상 질문을 추출하고, 실시간 압박 면접 시뮬레이션을 제공합니다.

## 기능

| 기능 | 사용 모델 | 설명 |
|---|---|---|
| 초기 분석 + 대표 질문 5개 | Pro | 업로드 직후 자동 생성 |
| 추가 질문 추출 (20개) | Pro | 서류의 문장 단위 정밀 타격 질문 |
| 종합 전략 보고서 | Pro | 합격 시나리오 + 4D 전략 분석 |
| 전략적 모범 답안 | Pro | 생성된 전체 질문에 대한 방어 논리 (추가 질문 생성 후 활성화) |
| 실시간 압박 면접 시뮬레이션 | Flash | 난이도/피드백 설정, 스트리밍 채팅, 회차별 최종 리포트 누적 |

## 실행 방법

```bash
pip install -r requirements.txt   # Python 3.10+
streamlit run app.py
```

## secrets 설정 (`.streamlit/secrets.toml`)

```toml
GOOGLE_API_KEY = "..."          # Google AI Studio에서 발급
PREMIUM_ACCESS_CODE = "..."     # (현재 미사용 — 결제 게이트 재도입 시 사용 예정)
PROMPT_SECRET = """
(시스템 프롬프트 전문)
"""

# 선택: 모델 교체 (미지정 시 아래 기본값)
# PRO_MODEL = "gemini-3.1-pro"
# FLASH_MODEL = "gemini-3.6-flash"
```

참고:
- `PROMPT_SECRET` 안의 `{life_record}` / `{cover_letter}` 플레이스홀더는 더 이상
  필요 없습니다(서류 원문은 프롬프트 치환이 아니라 별도 콘텐츠로 전달됨). 남아
  있어도 자동으로 안내 문구로 치환되므로 그대로 둬도 됩니다.
- 모범 답안 생성의 질문 파싱 정확도를 높이려면 프롬프트에서 초기 분석 보고서의
  대표 질문 섹션 앞에 `---[대표_예상_질문_시작_마커]---` 를 출력하도록 지시하세요.
  (마커가 없으면 "대표 예상 질문" / "대표 질문" 제목으로 폴백)

## 모델 교체

모델명은 코드 수정 없이 secrets의 `PRO_MODEL` / `FLASH_MODEL` 키로 바꿀 수 있습니다.

기본값(2026-07 기준 안정 버전):
- `gemini-3.1-pro` — 2026-02-19 GA
- `gemini-3.6-flash` — 2026-07-21 GA (`gemini-3.5-flash`보다 출력 단가가 낮고 토큰 효율이 높음)

> 새 모델 출시/은퇴 일정은
> [모델 문서](https://ai.google.dev/gemini-api/docs/models)에서 확인하세요.

## 예상 API 비용

가격(2026-07 기준): `gemini-3.1-pro` 입력 $2.00 / 출력 $12.00 per 1M tokens
(200K 토큰 초과 시 $4/$18 — 앱의 서류 길이 제한이 이 구간 진입을 막아줌),
`gemini-3.6-flash` 입력 $1.50 / 출력 $7.50 per 1M tokens.

서류(생기부 15p + 자소서) + 시스템 프롬프트 ≈ 입력 25K 토큰 가정 시 1인 기준:

| 기능 | 모델 | 토큰 (입력/출력) | 예상 비용 |
|---|---|---|---|
| 초기 분석 + 대표 질문 | Pro | 25K / 4K | ~$0.10 |
| 추가 질문 추출 (20개) | Pro | 25K / 4K | ~$0.10 |
| 종합 전략 보고서 | Pro | 25K / 6K | ~$0.12 |
| 전략적 모범 답안 | Pro | 33K / 10K | ~$0.19 |
| 면접 시뮬레이션 (10턴) | Flash | ~40K×10턴 / 0.5K×10턴 | ~$0.30–0.65* |
| 시뮬레이션 최종 리포트 | Pro | 33K / 5K | ~$0.13 |
| **풀코스 합계 (1인)** | | | **~$1.0–1.3 (약 1,400–1,900원)** |

\* 시뮬레이션은 턴마다 서류+분석 자료가 함께 전송되지만, 앞부분이 동일하게 고정되어
있어 implicit caching 할인(캐시된 입력은 대폭 할인)이 적용되면 하한에 가까워집니다.

실제 비용은 서류 분량·프롬프트 길이·시뮬레이션 턴 수에 비례해 달라집니다.
[Google AI Studio](https://aistudio.google.com)의 사용량 대시보드에서 실측을 확인하세요.

## 구조

```
app.py               # 진입점 (페이지 설정, 모드 라우팅)
core/config.py       # secrets 로드, 모델 상수
core/state.py        # session_state 초기화/리셋
core/gemini.py       # google-genai 호출 래퍼 (보고서 생성, 면접 채팅)
core/pdf.py          # pypdf 텍스트 추출
core/parsing.py      # 보고서에서 질문 목록 파싱
ui/common.py         # 헤더, 에러 표시, 다운로드 버튼
ui/analysis.py       # 업로드/분석/심층 기능/시뮬레이션 시작
ui/simulation.py     # 면접 채팅 + 최종 리포트
tests/               # pytest 단위 테스트
```

설계 메모:
- **explicit context caching(CachedContent)을 쓰지 않습니다.** 이 워크로드(세션당
  Pro 수 회 + Flash 채팅)에서는 캐시 저장료가 절감액보다 커서 순손실이었고, 1시간
  TTL 만료가 복구 불가 오류의 원인이었습니다. 대신 시스템 프롬프트 + 서류 원문을
  모든 호출의 앞부분에 동일하게 고정 배치해 implicit caching(2.5+ 기본 활성,
  저장료 없음) 할인을 유도합니다.
- 면접 채팅 세션이 유실되어도 화면의 대화 기록으로 자동 재구성되므로 진행 중인
  면접이 끊기지 않습니다.

## 결제 게이트 (추후 재도입 예정)

이전 버전의 계좌이체 + 공용 액세스 코드 방식은 제거했습니다. 재도입 시
`ui/analysis.py`의 `_render_deep_features` / `_render_simulation_launcher` 호출부를
잠금 조건으로 감싸고, secrets의 `PREMIUM_ACCESS_CODE`를 활용하면 됩니다.
(권장: 사용자별 일회용 코드 또는 PG 연동 — 공용 코드는 공유 한 번에 무력화됩니다.)

## 테스트

```bash
pip install pytest
python -m pytest tests/ -v
```
