"""분석 모드 UI: 업로드 → 초기 분석 → 심층 기능 → 시뮬레이션 시작 → 결과 열람."""
import streamlit as st

from core.config import MAX_DOC_CHARS, Settings
from core.gemini import create_interview_chat, generate_report, get_client
from core.parsing import parse_questions_from_report
from core.pdf import extract_text
from core.state import reset_analysis_state
from ui.common import download_report_button, error_box, render_header

# PROMPT_SECRET에 정의된 명령어 체계 — 프롬프트와의 호환을 위해 원문 유지
CMD_INITIAL = "이제 초기 분석을 시작하고 [초기 분석 보고서 및 대표 질문 5개]를 생성해주세요."
CMD_ADDITIONAL = "On command: '추가질문추출'"
CMD_STRATEGY = "On command: '생기부분석'"
CMD_MODEL_ANSWERS = (
    "On command: '모범답안생성'\n"
    "이제 위 질문 전체에 대한 [전략적 모범 답안 패키지]를 생성해주세요."
)

CONSENT_TEXT = (
    "업로드한 생활기록부·자기소개서는 면접 예상 질문 생성을 위해 Google Gemini API로 "
    "전송되어 처리되며, 이 앱의 서버에 별도로 저장되지 않습니다. 브라우저 탭을 닫으면 "
    "분석 결과와 서류 내용은 모두 사라집니다. 미성년자는 보호자의 동의 하에 이용해주세요."
)


def render_analysis(settings: Settings) -> None:
    render_header()
    if not st.session_state.analysis_complete:
        _render_upload(settings)
    else:
        _render_workspace(settings)


# --- 1단계: 업로드 & 초기 분석 ---

def _render_upload(settings: Settings) -> None:
    st.markdown(
        "<p style='text-align: center; font-size: 1.1em;'>당신의 서류를 기반으로 가장 날카로운 "
        "예상 질문을 추출하고, 완벽한 방어 논리를 설계합니다.</p>",
        unsafe_allow_html=True,
    )
    st.divider()
    st.subheader("1. 분석 자료 업로드")
    st.write("생기부와 자소서 PDF 파일을 각각 업로드해주세요.")

    col1, col2 = st.columns(2)
    with col1:
        life_record_file = st.file_uploader("📄 생활기록부 PDF 업로드", type=["pdf"])
    with col2:
        cover_letter_file = st.file_uploader("✍️ 자기소개서 PDF 업로드", type=["pdf"])

    st.info(CONSENT_TEXT, icon="🔒")
    consent = st.checkbox("위 내용을 확인했으며 개인정보 제공에 동의합니다.")

    start = st.button(
        "초기 분석 및 대표 질문 추출",
        use_container_width=True,
        type="primary",
        disabled=not consent,
    )
    if not consent:
        st.caption("ℹ️ 분석을 시작하려면 개인정보 제공 동의가 필요합니다.")
    if not start:
        return

    if not (life_record_file and cover_letter_file):
        st.warning("두 개의 PDF 파일을 모두 업로드해주세요.")
        return

    with st.spinner("PDF에서 텍스트를 추출하는 중..."):
        life_record_text = extract_text(life_record_file)
        cover_letter_text = extract_text(cover_letter_file)

    failed = []
    if not life_record_text:
        failed.append("생활기록부")
    if not cover_letter_text:
        failed.append("자기소개서")
    if failed:
        st.error(
            f"{' / '.join(failed)} PDF에서 텍스트를 추출하지 못했습니다. "
            "스캔(이미지)형이거나 암호화된 PDF는 지원되지 않습니다 — "
            "나이스(NEIS) 등에서 텍스트형 PDF로 다시 발급해 업로드해주세요."
        )
        return

    too_long = []
    if len(life_record_text) > MAX_DOC_CHARS:
        too_long.append(f"생활기록부({len(life_record_text):,}자)")
    if len(cover_letter_text) > MAX_DOC_CHARS:
        too_long.append(f"자기소개서({len(cover_letter_text):,}자)")
    if too_long:
        st.error(
            f"{' / '.join(too_long)}이(가) 허용 한도({MAX_DOC_CHARS:,}자)를 초과했습니다. "
            "올바른 서류 PDF인지 확인해주세요. 일반적인 생기부/자소서는 이 한도를 넘지 않습니다."
        )
        return

    try:
        with st.spinner("AI가 서류를 분석하고 있습니다... (1~2분 정도 걸릴 수 있어요)"):
            client = get_client(settings.api_key)
            initial_result = generate_report(
                client=client,
                model=settings.pro_model,
                system_prompt=settings.system_prompt,
                life_record=life_record_text,
                cover_letter=cover_letter_text,
                command=CMD_INITIAL,
            )
    except Exception as exc:
        error_box("AI 분석 중 오류가 발생했습니다. 잠시 후 다시 시도해주세요.", exc)
        return

    st.session_state.life_record = life_record_text
    st.session_state.cover_letter = cover_letter_text
    st.session_state.initial_result = initial_result
    st.session_state.analysis_complete = True
    st.rerun()


# --- 2단계: 분석 완료 후 워크스페이스 ---

def _render_workspace(settings: Settings) -> None:
    client = get_client(settings.api_key)

    st.subheader("📊 초기 분석 보고서 및 대표 질문")
    st.markdown(st.session_state.initial_result)
    download_report_button("초기 분석 보고서", st.session_state.initial_result, "초기분석보고서.md", "dl_initial")

    if st.button("새로운 분석 시작하기", type="secondary"):
        reset_analysis_state()
        st.rerun()

    st.divider()
    _render_deep_features(client, settings)
    st.divider()
    _render_simulation_launcher(client, settings)
    _render_results_archive()


def _run_report(client, settings: Settings, state_key: str, command: str, spinner: str, extra_context: str | None = None) -> None:
    try:
        with st.spinner(spinner):
            st.session_state[state_key] = generate_report(
                client=client,
                model=settings.pro_model,
                system_prompt=settings.system_prompt,
                life_record=st.session_state.life_record,
                cover_letter=st.session_state.cover_letter,
                command=command,
                extra_context=extra_context,
            )
    except Exception as exc:
        error_box("보고서 생성 중 오류가 발생했습니다. 잠시 후 다시 시도해주세요.", exc)
        return
    st.rerun()


def _render_deep_features(client, settings: Settings) -> None:
    st.subheader("⚙️ 심층 분석 기능")
    st.write("서류의 모든 잠재적 약점을 파고드는 심층 분석으로 면접을 완벽하게 대비하세요.")

    col1, col2, col3 = st.columns(3)

    with col1:
        questions_done = bool(st.session_state.additional_questions)
        if st.button("추가 질문 추출 (20개)", use_container_width=True, disabled=questions_done):
            _run_report(
                client, settings, "additional_questions", CMD_ADDITIONAL,
                "서류의 특정 문장과 단어까지 파고드는 20개의 정밀 타격 질문을 생성 중입니다...",
            )
        if questions_done:
            st.caption("ℹ️ 추가 질문이 생성되었습니다.")

    with col2:
        report_done = bool(st.session_state.premium_report)
        if st.button("종합 전략 보고서", use_container_width=True, disabled=report_done):
            _run_report(
                client, settings, "premium_report", CMD_STRATEGY,
                "합격 시나리오와 4D 전략 분석을 포함한 최종 보고서를 생성 중입니다...",
            )
        if report_done:
            st.caption("ℹ️ 보고서가 생성되었습니다.")

    with col3:
        questions_ready = bool(st.session_state.additional_questions)
        if st.button("전략적 모범 답안 생성", use_container_width=True, disabled=not questions_ready):
            initial_questions = parse_questions_from_report(st.session_state.initial_result)
            questions_context = "\n\n---\n\n".join(
                [initial_questions, st.session_state.additional_questions]
            )
            _run_report(
                client, settings, "model_answers", CMD_MODEL_ANSWERS,
                "모든 질문에 대한 모범 답안을 생성 중입니다...",
                extra_context=f"[답변해야 할 질문 목록]\n{questions_context}",
            )
        if not questions_ready:
            st.caption("ℹ️ '추가 질문 추출'을 먼저 실행해야 모범 답안을 생성할 수 있습니다.")


def _render_simulation_launcher(client, settings: Settings) -> None:
    st.subheader("🤖 실시간 압박 면접 시뮬레이션")
    st.write("AI 면접관과 함께 실제와 같은 압박 면접을 경험하고, 당신의 논리를 최종 점검하세요.")

    difficulty = st.slider("면접 난이도 설정 (1~10)", 1, 10, 5)
    feedback_mode = st.toggle("답변 후 실시간 피드백 ON/OFF", value=True)

    if not st.button("면접 시뮬레이션 시작하기", use_container_width=True, type="primary"):
        return

    feedback_status = "ON" if feedback_mode else "OFF"
    start_prompt = (
        "[사용자 명령어]\n"
        "On command: '면접시뮬레이션시작'\n"
        f"Parameters: difficulty: {difficulty}, feedback_mode: '{feedback_status}'\n"
        "이제 당신에게 제공된 서류 정보를 바탕으로 첫 번째 질문을 생성해주세요."
    )

    sim_context = _simulation_context()
    try:
        with st.spinner("AI 면접관을 준비 중입니다..."):
            chat = create_interview_chat(
                client=client,
                model=settings.flash_model,
                system_prompt=settings.system_prompt,
                life_record=st.session_state.life_record,
                cover_letter=st.session_state.cover_letter,
                context_reports=sim_context,
            )
            first_question = (chat.send_message(start_prompt).text or "").strip()
    except Exception as exc:
        error_box("시뮬레이션 준비 중 오류가 발생했습니다. 잠시 후 다시 시도해주세요.", exc)
        return

    st.session_state.chat = chat
    st.session_state.sim_start_prompt = start_prompt
    st.session_state.sim_context = sim_context or ""
    st.session_state.messages = [{"role": "assistant", "content": first_question}]
    st.session_state.simulation_mode = True
    st.rerun()


def _simulation_context() -> str | None:
    """면접관이 참고할 사전 분석 자료 (있는 것만)."""
    sections = []
    if st.session_state.initial_result:
        sections.append(f"[초기 분석 보고서 및 대표 질문]:\n{st.session_state.initial_result}")
    if st.session_state.additional_questions:
        sections.append(f"[심층 해부 질문 (20개)]:\n{st.session_state.additional_questions}")
    return "\n\n".join(sections) or None


# --- 결과 열람 ---

def _render_results_archive() -> None:
    has_results = (
        st.session_state.premium_report
        or st.session_state.additional_questions
        or st.session_state.model_answers
        or st.session_state.simulation_history
    )
    if not has_results:
        return

    st.markdown("---")
    st.subheader("📋 분석 결과 및 리포트")
    st.write("아래 섹션을 클릭하여 각 분석 내용을 확인하세요.")

    if st.session_state.premium_report:
        with st.expander("📑 종합 전략 보고서"):
            st.markdown(st.session_state.premium_report)
            download_report_button("종합 전략 보고서", st.session_state.premium_report, "종합전략보고서.md", "dl_strategy")

    if st.session_state.additional_questions:
        with st.expander("🔬 심층 해부 질문 (20개)"):
            st.markdown(st.session_state.additional_questions)
            download_report_button("심층 해부 질문", st.session_state.additional_questions, "심층해부질문.md", "dl_questions")

    if st.session_state.model_answers:
        with st.expander("💡 전략적 모범 답안 패키지"):
            st.markdown(st.session_state.model_answers)
            download_report_button("모범 답안 패키지", st.session_state.model_answers, "모범답안패키지.md", "dl_answers")

    for i, sim in enumerate(reversed(st.session_state.simulation_history)):
        entry_number = len(st.session_state.simulation_history) - i
        if sim["report"]:
            with st.expander(f"📋 면접 시뮬레이션 {entry_number} — 최종 리포트", expanded=(i == 0)):
                st.markdown(sim["report"])
                download_report_button(
                    f"시뮬레이션 {entry_number} 리포트", sim["report"],
                    f"면접시뮬레이션리포트_{entry_number}.md", f"dl_sim_report_{entry_number}",
                )
        with st.expander(f"💬 면접 시뮬레이션 {entry_number} — 전체 대화 다시보기"):
            for message in sim["transcript"]:
                with st.chat_message(message["role"]):
                    st.markdown(message["content"])
