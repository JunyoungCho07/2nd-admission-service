"""설정 로드: secrets, 모델 이름, 공통 상수."""
from dataclasses import dataclass

import streamlit as st

# 기본 모델 (secrets의 PRO_MODEL / FLASH_MODEL 키로 코드 수정 없이 교체 가능)
DEFAULT_PRO_MODEL = "gemini-3.1-pro"
DEFAULT_FLASH_MODEL = "gemini-3.6-flash"

APP_TITLE = "면접관 AI"
LOGO_PATH = "JYC_clear.png"

# 서류 1건당 허용하는 최대 추출 텍스트 길이.
# 정상 생기부/자소서는 수만 자 수준 — 이 한도는 잘못된 파일(전집 스캔 등)로 인한
# 과금 폭탄과 gemini-3.1-pro의 200K 토큰 초과 시 2배 요금 구간 진입을 막는다.
MAX_DOC_CHARS = 150_000

# PROMPT_SECRET 안의 레거시 플레이스홀더 — 서류 원문은 프롬프트 치환이 아니라
# 별도의 사용자 콘텐츠로 전달되므로, 모델이 중괄호 문자열을 그대로 보지 않도록 안내문으로 바꾼다.
_PLACEHOLDER_NOTES = {
    "{life_record}": "(아래 [사용자 제출 자료]의 생활기록부 내용을 참조)",
    "{cover_letter}": "(아래 [사용자 제출 자료]의 자기소개서 내용을 참조)",
}


def normalize_prompt(raw_prompt: str) -> str:
    for placeholder, note in _PLACEHOLDER_NOTES.items():
        raw_prompt = raw_prompt.replace(placeholder, note)
    return raw_prompt


@dataclass(frozen=True)
class Settings:
    api_key: str
    system_prompt: str
    pro_model: str
    flash_model: str


def load_settings() -> Settings:
    """secrets를 검증해서 로드. 누락 시 사용자에게 안내하고 실행을 멈춘다."""
    try:
        api_key = st.secrets["GOOGLE_API_KEY"]
    except (FileNotFoundError, KeyError):
        st.error("API 키를 찾을 수 없습니다. .streamlit/secrets.toml의 GOOGLE_API_KEY를 확인해주세요.")
        st.stop()

    try:
        raw_prompt = st.secrets["PROMPT_SECRET"]
    except (FileNotFoundError, KeyError):
        st.error("프롬프트 내용을 찾을 수 없습니다. .streamlit/secrets.toml의 PROMPT_SECRET을 확인해주세요.")
        st.stop()

    return Settings(
        api_key=api_key,
        system_prompt=normalize_prompt(raw_prompt),
        pro_model=st.secrets.get("PRO_MODEL", DEFAULT_PRO_MODEL),
        flash_model=st.secrets.get("FLASH_MODEL", DEFAULT_FLASH_MODEL),
    )
