"""google-genai SDK 래퍼.

설계 노트:
- 구 SDK(google-generativeai)의 explicit context caching(CachedContent)은 제거했다.
  1시간 TTL 저장료(특히 Pro 캐시 $4.50/1M tokens/hr) 때문에 이 워크로드에서는
  캐싱을 안 쓰는 것보다 오히려 비쌌고, 캐시 만료 시 복구 불가 데드엔드 버그의
  원인이었다. 대신 매 호출에서 시스템 프롬프트 + 서류 원문을 동일한 순서로
  앞부분에 고정 배치해 Gemini의 implicit caching(2.5+ 기본 활성, 저장료 없음)
  할인을 유도한다.
- 시뮬레이션 채팅은 SDK의 chats 세션을 사용한다. 대화 기록은 SDK가 관리하며,
  세션이 유실되면 st.session_state의 메시지 목록으로 언제든 재구성할 수 있다.
"""
import time

from google import genai
from google.genai import errors, types

import streamlit as st

# 시뮬레이션 시작 시 서류를 전달받았음을 확인하는 고정 응답 (history 재구성용)
_DOCS_ACK = "네, 제출된 생활기록부와 자기소개서를 모두 확인했습니다. 준비되었습니다."

# 일시적 오류(과부하/속도 제한)로 판단해 자동 재시도하는 HTTP 상태 코드
_RETRYABLE_CODES = {429, 500, 502, 503, 504}
_MAX_ATTEMPTS = 3
_BACKOFF_SECONDS = 2.0


class EmptyResponseError(RuntimeError):
    """모델이 빈 응답을 반환 (안전 필터 차단 또는 일시 장애)."""


def _is_retryable(exc: Exception) -> bool:
    return isinstance(exc, errors.APIError) and exc.code in _RETRYABLE_CODES


@st.cache_resource
def get_client(api_key: str) -> genai.Client:
    return genai.Client(api_key=api_key)


def build_docs_block(life_record: str, cover_letter: str) -> str:
    return (
        "--- [사용자 제출 자료] ---\n"
        f"[생활기록부 내용]:\n{life_record}\n\n"
        f"[자기소개서 내용]:\n{cover_letter}"
    )


def generate_report(
    client: genai.Client,
    model: str,
    system_prompt: str,
    life_record: str,
    cover_letter: str,
    command: str,
    extra_context: str | None = None,
) -> str:
    """서류 + (선택) 추가 컨텍스트 + 명령어로 단발 생성 호출을 수행한다.

    implicit caching 히트율을 위해 서류 블록을 항상 첫 파트에 고정한다.
    단발(멱등) 호출이므로 429/5xx 일시 오류와 빈 응답은 최대 3회까지 자동 재시도한다.
    """
    parts = [build_docs_block(life_record, cover_letter)]
    if extra_context:
        parts.append(extra_context)
    parts.append(command)

    last_exc: Exception | None = None
    for attempt in range(_MAX_ATTEMPTS):
        if attempt:
            time.sleep(_BACKOFF_SECONDS * (2 ** (attempt - 1)))
        try:
            response = client.models.generate_content(
                model=model,
                contents=parts,
                config=types.GenerateContentConfig(system_instruction=system_prompt),
            )
        except Exception as exc:
            if _is_retryable(exc):
                last_exc = exc
                continue
            raise
        text = (response.text or "").strip()
        if text:
            return text
        last_exc = EmptyResponseError("모델이 빈 응답을 반환했습니다.")
    raise last_exc


def _history_from_messages(messages: list[dict]) -> list[types.Content]:
    history = []
    for message in messages:
        role = "model" if message["role"] == "assistant" else "user"
        history.append(types.Content(role=role, parts=[types.Part(text=message["content"])]))
    return history


def create_interview_chat(
    client: genai.Client,
    model: str,
    system_prompt: str,
    life_record: str,
    cover_letter: str,
    context_reports: str | None = None,
    prior_messages: list[dict] | None = None,
    start_prompt: str | None = None,
):
    """면접 시뮬레이션용 채팅 세션을 만든다.

    서류(+기존 분석 결과)를 첫 user 턴으로 넣어 이후 모든 턴에서 참조되게 한다.
    세션 복구 시에는 prior_messages(화면에 표시된 대화)와 최초 start_prompt를
    그대로 재주입해 진행 중이던 면접을 이어간다.
    """
    docs = build_docs_block(life_record, cover_letter)
    if context_reports:
        docs += f"\n\n--- [사전 분석 자료] ---\n{context_reports}"

    history = [
        types.Content(role="user", parts=[types.Part(text=docs)]),
        types.Content(role="model", parts=[types.Part(text=_DOCS_ACK)]),
    ]
    if prior_messages:
        if start_prompt:
            history.append(types.Content(role="user", parts=[types.Part(text=start_prompt)]))
        history.extend(_history_from_messages(prior_messages))

    return client.chats.create(
        model=model,
        config=types.GenerateContentConfig(system_instruction=system_prompt),
        history=history,
    )


def stream_chat_reply(chat, message: str):
    """chat.send_message_stream 청크를 st.write_stream에 바로 넘길 수 있는 제너레이터."""
    for chunk in chat.send_message_stream(message):
        yield chunk.text or ""
