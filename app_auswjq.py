import streamlit as st
import google.generativeai as genai
from pathlib import Path
import PyPDF2
import io

# --- 초기 설정 ---

# st.session_state 초기화
if 'analysis_complete' not in st.session_state:
    st.session_state.analysis_complete = False
if 'life_record' not in st.session_state:
    st.session_state.life_record = ""
if 'cover_letter' not in st.session_state:
    st.session_state.cover_letter = ""
if 'initial_result' not in st.session_state:
    st.session_state.initial_result = ""
if 'additional_questions' not in st.session_state:
    st.session_state.additional_questions = ""
if 'premium_report' not in st.session_state:
    st.session_state.premium_report = ""
if 'model_answers' not in st.session_state:
    st.session_state.model_answers = ""

# 프롬프트 로드
try:
    prompt_path = Path(__file__).parent / "prompt_main.txt"
    AI_PROMPT = prompt_path.read_text(encoding="utf-8")
except FileNotFoundError:
    st.error("핵심 프롬프트 파일('prompt_main.txt')을 찾을 수 없습니다.")
    st.stop()

# API 키 설정
try:
    api_key = st.secrets["GOOGLE_API_KEY"]
    genai.configure(api_key=api_key)
    model = genai.GenerativeModel('gemini-1.5-pro-latest')
except (FileNotFoundError, KeyError):
    st.error("API 키를 찾을 수 없습니다. .streamlit/secrets.toml 파일을 확인해주세요.")
    st.stop()

# PDF 텍스트 추출 함수
def extract_text_from_pdf(pdf_file):
    if pdf_file is not None:
        try:
            pdf_reader = PyPDF2.PdfReader(io.BytesIO(pdf_file.read()))
            text = ""
            for page in pdf_reader.pages:
                text += page.extract_text() or ""
            return text
        except Exception as e:
            st.error(f"PDF 파일을 읽는 중 오류가 발생했습니다: {e}")
            return None
    return None

# --- 사용자 인터페이스 (UI) ---

st.markdown("<h1 style='text-align: center;'>압박 면접 전략 분석가</h1>", unsafe_allow_html=True)

# 초기 분석이 완료되지 않았으면 파일 업로드 화면 표시
if not st.session_state.analysis_complete:
    st.markdown("<p style='text-align: center; font-size: 1.1em;'>당신의 서류를 기반으로 가장 날카로운 예상 질문을 추출하고, 완벽한 방어 논리를 설계합니다.</p>", unsafe_allow_html=True)
    st.divider()
    st.subheader("1. 분석 자료 업로드")
    st.write("생기부와 자소서 PDF 파일을 각각 업로드해주세요.")
    col1, col2 = st.columns(2)
    with col1:
        life_record_file = st.file_uploader("📄 생활기록부 PDF 업로드", type=['pdf'])
    with col2:
        cover_letter_file = st.file_uploader("✍️ 자기소개서 PDF 업로드", type=['pdf'])
    
    if st.button("초기 분석 및 대표 질문 추출", use_container_width=True, type="primary"):
        # ... (이전 코드와 동일) ...
        if life_record_file and cover_letter_file:
            # ... (텍스트 추출 로직) ...
            life_record_text = extract_text_from_pdf(life_record_file)
            cover_letter_text = extract_text_from_pdf(cover_letter_file)

            if life_record_text and cover_letter_text:
                final_prompt = f"{AI_PROMPT}\n\n---\n[사용자 제출 자료]\n\n[생기부 내용]:\n{life_record_text}\n\n[자소서 내용]:\n{cover_letter_text}"
                
                with st.spinner("AI가 서류를 정밀 분석 중입니다..."):
                    # ... (AI 호출 및 상태 저장 로직) ...
                    response = model.generate_content(final_prompt)
                    st.session_state.life_record = life_record_text
                    st.session_state.cover_letter = cover_letter_text
                    st.session_state.initial_result = response.text
                    st.session_state.analysis_complete = True
                    st.rerun()

# 초기 분석이 완료되면 결과 및 추가 기능 버튼 표시
else:
    st.subheader("📊 초기 분석 보고서 및 대표 질문")
    st.markdown(st.session_state.initial_result)
    st.divider()

    st.subheader("⚙️ 프리미엄 기능")
    st.write("서류의 모든 잠재적 약점을 파고드는 심층 분석을 통해 면접을 완벽하게 대비하세요.")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        if st.button("추가 질문 추출 (20개)", use_container_width=True):
            with st.spinner("서류의 특정 문장과 단어까지 파고드는 20개의 정밀 타격 질문을 생성중입니다..."):
                additional_prompt = f"{AI_PROMPT}\n\n---\n[사용자 제출 자료]\n\n[생기부 내용]:\n{st.session_state.life_record}\n\n[자소서 내용]:\n{st.session_state.cover_letter}\n\n---\n[사용자 명령어]\nOn command: '추가질문추출'"
                response = model.generate_content(additional_prompt)
                st.session_state.additional_questions = response.text

    with col2:
        if st.button("프리미엄 종합 전략 보고서", use_container_width=True):
            with st.spinner("합격 시나리오와 4D 전략 분석을 포함한 최종 보고서를 생성중입니다..."):
                report_prompt = f"{AI_PROMPT}\n\n---\n[사용자 제출 자료]\n\n[생기부 내용]:\n{st.session_state.life_record}\n\n[자소서 내용]:\n{st.session_state.cover_letter}\n\n---\n[사용자 명령어]\nOn command: '생기부분석'"
                response = model.generate_content(report_prompt)
                st.session_state.premium_report = response.text

    with col3:
        if st.button("전략적 모범 답안 생성", use_container_width=True):
            if not st.session_state.initial_result and not st.session_state.additional_questions:
                st.warning("모범 답안을 생성하려면 먼저 질문이 추출되어야 합니다.")
            else:
                with st.spinner("모든 질문에 대한 전략적 모범 답안 패키지를 생성중입니다..."):
                    # 생성된 모든 질문을 취합
                    all_questions = st.session_state.initial_result + "\n\n" + st.session_state.additional_questions
                    answer_prompt = f"{AI_PROMPT}\n\n---\n[사용자 제출 자료]\n\n[생기부 내용]:\n{st.session_state.life_record}\n\n[자소서 내용]:\n{st.session_state.cover_letter}\n\n---\n[분석된 질문 목록]\n{all_questions}\n\n---\n[사용자 명령어]\nOn command: '모범답안생성'"
                    response = model.generate_content(answer_prompt)
                    st.session_state.model_answers = response.text

    # 각 기능의 결과가 존재하면 순서대로 화면에 표시
    if st.session_state.premium_report:
        st.divider()
        st.subheader("📑 프리미엄 종합 전략 보고서")
        st.markdown(st.session_state.premium_report)

    if st.session_state.additional_questions:
        st.divider()
        st.subheader("🔬 심층 해부 질문 (20개)")
        st.markdown(st.session_state.additional_questions)

    if st.session_state.model_answers:
        st.divider()
        st.subheader("💡 전략적 모범 답안 패키지")
        st.markdown(st.session_state.model_answers)