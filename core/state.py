"""st.session_state 초기화/리셋.

기본값은 호출 시마다 새로 만든다 — 모듈 전역의 가변 객체(list 등)를 setdefault로
넣으면 Streamlit 프로세스 안에서 세션 간에 같은 객체가 공유될 수 있다.
"""
import streamlit as st


def _defaults() -> dict:
    return {
        "analysis_complete": False,
        "simulation_mode": False,
        "life_record": "",
        "cover_letter": "",
        "initial_result": "",
        "additional_questions": "",
        "premium_report": "",
        "model_answers": "",
        "messages": [],            # 진행 중인 시뮬레이션의 대화 (role/content dict)
        "simulation_history": [],  # 완료된 시뮬레이션 [{transcript, report}]
        "chat": None,              # google-genai 채팅 세션 (유실 시 messages로 재구성)
        "sim_start_prompt": "",    # 채팅 세션 재구성에 필요한 시작 명령어
        "sim_context": "",         # 채팅 세션 재구성에 필요한 사전 분석 자료
    }


def init_session_state() -> None:
    for key, value in _defaults().items():
        if key not in st.session_state:
            st.session_state[key] = value


def reset_analysis_state() -> None:
    """'새로운 분석 시작하기' — 모든 분석/시뮬레이션 상태를 비운다."""
    for key in list(_defaults()):
        st.session_state.pop(key, None)
