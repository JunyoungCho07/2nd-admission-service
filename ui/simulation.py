"""면접 시뮬레이션 모드 UI (실시간 채팅)."""
import streamlit as st

from core.config import Settings
from core.gemini import create_interview_chat, generate_report, get_client, stream_chat_reply
from ui.common import error_box

CMD_FINAL_REPORT = "'종료' 명령입니다. 위 대화 내용을 바탕으로 [면접 시뮬레이션 최종 리포트]를 생성해주세요."


def render_simulation(settings: Settings) -> None:
    st.title("🤖 실시간 압박 면접 시뮬레이션")

    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])

    if user_input := st.chat_input("답변을 입력하세요..."):
        _handle_turn(settings, user_input)

    col1, col2 = st.columns(2)
    with col1:
        if st.button("시뮬레이션 종료 및 최종 리포트 생성", use_container_width=True, type="primary"):
            _finish_with_report(settings)
    with col2:
        if st.button("리포트 없이 종료하기", use_container_width=True):
            _finish_without_report()


def _ensure_chat(settings: Settings):
    """채팅 세션을 반환. 유실됐으면(서버 재시작 등) 대화 기록으로 재구성한다."""
    if st.session_state.chat is None:
        client = get_client(settings.api_key)
        st.session_state.chat = create_interview_chat(
            client=client,
            model=settings.flash_model,
            system_prompt=settings.system_prompt,
            life_record=st.session_state.life_record,
            cover_letter=st.session_state.cover_letter,
            context_reports=st.session_state.sim_context or None,
            prior_messages=st.session_state.messages,
            start_prompt=st.session_state.sim_start_prompt,
        )
    return st.session_state.chat


def _handle_turn(settings: Settings, user_input: str) -> None:
    with st.chat_message("user"):
        st.markdown(user_input)

    with st.chat_message("assistant"):
        try:
            chat = _ensure_chat(settings)
            reply = st.write_stream(stream_chat_reply(chat, user_input))
        except Exception as exc:
            # 실패한 턴은 기록하지 않고, 다음 턴에서 messages 기준으로 세션을 재구성한다.
            st.session_state.chat = None
            error_box("면접관 응답 생성에 실패했습니다. 같은 답변을 다시 보내주세요.", exc)
            return

    st.session_state.messages.append({"role": "user", "content": user_input})
    st.session_state.messages.append({"role": "assistant", "content": str(reply)})


def _transcript_text() -> str:
    lines = []
    for message in st.session_state.messages:
        speaker = "면접관" if message["role"] == "assistant" else "지원자"
        lines.append(f"{speaker}: {message['content']}")
    return "\n\n".join(lines)


def _finish_with_report(settings: Settings) -> None:
    if not any(m["role"] == "user" for m in st.session_state.messages):
        st.warning("아직 답변한 내용이 없습니다. 최소 한 번은 답변한 뒤 리포트를 생성해주세요.")
        return

    try:
        with st.spinner("면접 전체 내용을 바탕으로 최종 리포트를 생성하고 있습니다..."):
            client = get_client(settings.api_key)
            report = generate_report(
                client=client,
                model=settings.pro_model,
                system_prompt=settings.system_prompt,
                life_record=st.session_state.life_record,
                cover_letter=st.session_state.cover_letter,
                command=CMD_FINAL_REPORT,
                extra_context=f"[면접 전체 대화 기록]\n{_transcript_text()}",
            )
    except Exception as exc:
        # 대화 기록은 그대로 유지되므로 버튼을 다시 눌러 재시도할 수 있다.
        error_box("리포트 생성 중 오류가 발생했습니다. 대화 기록은 보존되어 있으니 다시 시도해주세요.", exc)
        return

    _archive_and_exit(report)


def _finish_without_report() -> None:
    """리포트 없이도 언제든 나갈 수 있는 탈출구 — 대화 기록은 보존된다."""
    if any(m["role"] == "user" for m in st.session_state.messages):
        _archive_and_exit(report=None)
        return
    st.session_state.messages = []
    st.session_state.chat = None
    st.session_state.simulation_mode = False
    st.rerun()


def _archive_and_exit(report: str | None) -> None:
    st.session_state.simulation_history.append(
        {"transcript": st.session_state.messages.copy(), "report": report}
    )
    st.session_state.messages = []
    st.session_state.chat = None
    st.session_state.simulation_mode = False
    st.rerun()
