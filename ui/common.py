"""공통 UI 요소: 헤더, 에러 표시, 다운로드 버튼."""
import base64
from pathlib import Path

import streamlit as st

from core.config import APP_TITLE, LOGO_PATH


def _image_base64(path: str) -> str | None:
    try:
        return base64.b64encode(Path(path).read_bytes()).decode("utf-8")
    except FileNotFoundError:
        return None


def render_header(target_exam: str | None = None) -> None:
    logo = _image_base64(LOGO_PATH)
    if logo:
        st.markdown(
            f'<div style="text-align: center;">'
            f'<img src="data:image/png;base64,{logo}" alt="로고" '
            f'style="width:180px; margin-bottom: 20px;"></div>',
            unsafe_allow_html=True,
        )
    st.markdown(f"<h1 style='text-align: center;'>{APP_TITLE}</h1>", unsafe_allow_html=True)
    if target_exam:
        st.markdown(
            f"<p style='text-align: center; font-weight: 600;'>🎯 {target_exam} 대비</p>",
            unsafe_allow_html=True,
        )
    st.markdown("<p style='text-align: center;'>Developed by JunyoungCho</p>", unsafe_allow_html=True)


def error_box(message: str, exc: Exception | None = None) -> None:
    """사용자 친화적 에러 + 접힌 상세 정보 (원시 예외를 본문에 그대로 노출하지 않는다)."""
    st.error(message)
    if exc is not None:
        with st.expander("자세한 오류 정보"):
            st.code(f"{type(exc).__name__}: {exc}")


def download_report_button(label: str, text: str, file_name: str, key: str) -> None:
    st.download_button(
        label=f"⬇️ {label} 다운로드",
        data=text,
        file_name=file_name,
        mime="text/markdown",
        key=key,
    )
