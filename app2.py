import streamlit as st
import google.generativeai as genai
from pathlib import Path
import PyPDF2
import io
import base64
import datetime

# --- 초기 설정 ---

# 💡 세션 상태 변수 정리 및 명확화
st.session_state.setdefault('analysis_complete', False)
st.session_state.setdefault('simulation_mode', False)
st.session_state.setdefault('pro_cache_name', None)
st.session_state.setdefault('flash_cache_name', None)
st.session_state.setdefault('messages', [])
st.session_state.setdefault('simulation_transcript', [])
st.session_state.setdefault('life_record', "")
st.session_state.setdefault('cover_letter', "")
st.session_state.setdefault('initial_result', "")
st.session_state.setdefault('additional_questions', "")
st.session_state.setdefault('premium_report', "")
st.session_state.setdefault('model_answers', "")
st.session_state.setdefault('simulation_report', "")

# Secrets에서 프롬프트 로드
try:
    AI_PROMPT = st.secrets["PROMPT_SECRET"]
except (FileNotFoundError, KeyError):
    st.error("프롬프트 내용을 찾을 수 없습니다. .streamlit/secrets.toml 파일을 확인해주세요.")
    st.stop()

# API 키 및 모델 이름 설정
try:
    api_key = st.secrets["GOOGLE_API_KEY"]
    genai.configure(api_key=api_key)
    # 💡 (중요) CachedContent를 지원하는 버전 명시 모델로 수정
    PRO_MODEL_NAME = 'models/gemini-2.5-pro'
    FLASH_MODEL_NAME = 'models/gemini-2.5-flash'
except (FileNotFoundError, KeyError):
    st.error("API 키를 찾을 수 없습니다. .streamlit/secrets.toml 파일을 확인해주세요.")
    st.stop()

# --- 유틸리티 함수 (변경 없음) ---
def extract_text_from_pdf(pdf_file):
    # ... (기존 코드와 동일)
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

def get_image_base64(path):
    # ... (기존 코드와 동일)
    try:
        with open(path, "rb") as img_file:
            return base64.b64encode(img_file.read()).decode('utf-8')
    except FileNotFoundError:
        return None

# --- 🎈 메인 앱 로직 ---

if st.session_state.simulation_mode:
    st.title("🤖 실시간 압박 면접 시뮬레이션")

    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])

    if user_input := st.chat_input("답변을 입력하세요... ('종료' 입력 시 리포트 생성)"):
        st.session_state.messages.append({"role": "user", "content": user_input})
        with st.chat_message("user"):
            st.markdown(user_input)

        with st.chat_message("assistant"):
            with st.spinner("면접관이 답변을 분석하고 다음 질문을 준비 중입니다..."):
                try:
                    # 💡 (중요) 올바른 함수로 Flash 캐시 불러오기
                    flash_cache = genai.caching.CachedContent.get(name=st.session_state.flash_cache_name)
                    model_flash_from_cache = genai.GenerativeModel.from_cached_content(flash_cache)
                    
                    simulation_prompt = f"""
                    [현재 면접 대화 기록]
                    {st.session_state.messages}
                    ---
                    [사용자 명령어]
                    사용자가 방금 '{user_input}'이라고 답변했습니다. 이 답변을 분석하고, 설정된 난이도와 피드백 모드에 맞춰 다음 꼬리 질문이나 피드백을 생성해주세요.
                    """
                    response = model_flash_from_cache.generate_content(simulation_prompt)
                    ai_response = response.text
                    st.markdown(ai_response)
                    st.session_state.messages.append({"role": "assistant", "content": ai_response})
                except Exception as e:
                    st.error(f"시뮬레이션 중 오류가 발생했습니다: {e}")

    if st.button("시뮬레이션 종료 및 최종 리포트 생성"):
        with st.spinner("면접 전체 내용을 바탕으로 최종 리포트를 생성하고 있습니다..."):
            try:
                # 💡 (중요) 올바른 함수로 Pro 캐시 불러오기
                pro_cache = genai.caching.CachedContent.get(name=st.session_state.pro_cache_name)
                model_pro_from_cache = genai.GenerativeModel.from_cached_content(pro_cache)

                report_prompt = f"""
                [면접 전체 대화 기록]
                {st.session_state.messages}
                ---
                [사용자 명령어]
                '종료' 명령입니다. 위 대화 내용을 바탕으로 [면접 시뮬레이션 최종 리포트]를 생성해주세요.
                """
                response = model_pro_from_cache.generate_content(report_prompt)
                
                st.session_state.simulation_transcript = st.session_state.messages.copy()
                st.session_state.simulation_report = response.text
                st.session_state.simulation_mode = False
                st.session_state.messages = []
                st.rerun()

            except Exception as e:
                st.error(f"리포트 생성 중 오류가 발생했습니다: {e}")

else: # 분석 모드 UI
    # ... (이미지, 제목 등 UI 부분은 기존 코드와 동일)
    image_path = "JYC_clear.png"
    image_base64 = get_image_base64(image_path)
    if image_base64:
        st.markdown(f"""<div style="text-align: center;"><img src="data:image/png;base64,{image_base64}" alt="로고" style="width:180px; margin-bottom: 20px;"></div>""", unsafe_allow_html=True)
    st.markdown("<h1 style='text-align: center;'>압박 면접 전략 분석가</h1>", unsafe_allow_html=True)

    if not st.session_state.analysis_complete:
        st.markdown("<p style='text-align: center; font-size: 1.1em;'>당신의 서류를 기반으로 가장 날카로운 예상 질문을 추출하고, 완벽한 방어 논리를 설계합니다.</p>", unsafe_allow_html=True)
        st.divider()
        st.subheader("1. 분석 자료 업로드")
        
        col1, col2 = st.columns(2)
        with col1:
            life_record_file = st.file_uploader("📄 생활기록부 PDF 업로드", type=['pdf'])
        with col2:
            cover_letter_file = st.file_uploader("✍️ 자기소개서 PDF 업로드", type=['pdf'])
        
        if st.button("초기 분석 및 대표 질문 추출", use_container_width=True, type="primary"):
            if life_record_file and cover_letter_file:
                with st.spinner("PDF 텍스트를 추출하는 중..."):
                    life_record_text = extract_text_from_pdf(life_record_file)
                    cover_letter_text = extract_text_from_pdf(cover_letter_file)

                if life_record_text and cover_letter_text:
                    st.session_state.life_record = life_record_text
                    st.session_state.cover_letter = cover_letter_text
                    
                    with st.spinner("AI 분석을 위해 Pro/Flash 모델용 캐시를 생성 중입니다..."):
                        try:
                            # 💡 Pro와 Flash 캐시에 공통으로 사용할 콘텐츠 정의
                            cache_contents = [{
                                'role': 'user',
                                'parts': [
                                    {'text': "--- [사용자 제출 자료] ---"},
                                    {'text': f"[생활기록부 내용]:\n{life_record_text}"},
                                    {'text': f"[자기소개서 내용]:\n{cover_letter_text}"}
                                ]
                            }]

                            # 💡 Pro 모델용 캐시 생성
                            pro_cache = genai.caching.CachedContent.create(
                                model=PRO_MODEL_NAME,
                                system_instruction=AI_PROMPT,
                                contents=cache_contents,
                                ttl=datetime.timedelta(hours=1)
                            )
                            st.session_state.pro_cache_name = pro_cache.name
                            st.info("Pro 모델용 캐시 생성 완료!")

                            # 💡 Flash 모델용 캐시도 동시에 생성
                            flash_cache = genai.caching.CachedContent.create(
                                model=FLASH_MODEL_NAME,
                                system_instruction=AI_PROMPT,
                                contents=cache_contents,
                                ttl=datetime.timedelta(hours=1)
                            )
                            st.session_state.flash_cache_name = flash_cache.name
                            st.info("Flash 모델용 캐시 생성 완료!")
                            
                            # 💡 생성된 Pro 캐시를 바로 사용해 첫 분석 실행
                            model_pro_from_cache = genai.GenerativeModel.from_cached_content(pro_cache)
                            response = model_pro_from_cache.generate_content("이제 초기 분석을 시작하고 [초기 분석 보고서 및 대표 질문 5개]를 생성해주세요.")
                            
                            st.session_state.initial_result = response.text
                            st.session_state.analysis_complete = True
                            st.rerun()

                        except Exception as e:
                            st.error(f"캐시 생성 또는 AI 분석 중 오류가 발생했습니다: {e}")
                else:
                    st.error("PDF에서 텍스트를 추출하지 못했습니다.")
            else:
                st.warning("두 개의 PDF 파일을 모두 업로드해주세요.")
    else: # 분석 완료 후 UI
        st.subheader("📊 초기 분석 보고서 및 대표 질문")
        st.markdown(st.session_state.initial_result)
        
        if st.button("새로운 분석 시작하기", type="secondary"):
            with st.spinner("기존 캐시를 삭제하는 중..."):
                try:
                    # 💡 Pro/Flash 캐시 모두 삭제
                    if st.session_state.pro_cache_name:
                        genai.caching.CachedContent.delete(name=st.session_state.pro_cache_name)
                    if st.session_state.flash_cache_name:
                        genai.caching.CachedContent.delete(name=st.session_state.flash_cache_name)
                except Exception as e:
                    st.warning(f"캐시 삭제 중 오류 발생: {e}")
            
            for key in list(st.session_state.keys()):
                del st.session_state[key]
            st.rerun()

        st.divider()
        st.subheader("⚙️ 프리미엄 기능")
        
        try:
            # 💡 (중요) 올바른 함수와 변수 이름으로 Pro 캐시 불러오기
            pro_cache = genai.caching.CachedContent.get(name=st.session_state.pro_cache_name)
            model_pro_from_cache = genai.GenerativeModel.from_cached_content(pro_cache)

            col1, col2, col3 = st.columns(3)
            with col1:
                if st.button("추가 질문 추출 (20개)", use_container_width=True):
                    with st.spinner("..."):
                        response = model_pro_from_cache.generate_content("On command: '추가질문추출'")
                        st.session_state.additional_questions = response.text
                        st.rerun()
            with col2:
                if st.button("프리미엄 종합 전략 보고서", use_container_width=True):
                    with st.spinner("..."):
                        response = model_pro_from_cache.generate_content("On command: '생기부분석'")
                        st.session_state.premium_report = response.text
                        st.rerun()
            with col3:
                if st.button("전략적 모범 답안 생성", use_container_width=True):
                    with st.spinner("..."):
                        # ... (모범 답안 생성 로직)
                        all_questions = st.session_state.initial_result + "\n\n" + st.session_state.additional_questions
                        answer_prompt = f"[분석된 질문 목록]\n{all_questions}\n\n---\n[사용자 명령어]\nOn command: '모범답안생성'"
                        response = model_pro_from_cache.generate_content(answer_prompt)
                        st.session_state.model_answers = response.text
                        st.rerun()

        except Exception as e:
            st.error(f"프리미엄 기능 실행 중 오류가 발생했습니다: {e}")
            st.warning("캐시가 만료되었을 수 있습니다. '새로운 분석 시작하기'를 눌러 다시 시도해주세요.")


        st.divider()

        st.subheader("🤖 실시간 압박 면접 시뮬레이션 시작")
        difficulty = st.slider("면접 난이도 설정 (1~10)", 1, 10, 5)
        feedback_mode = st.toggle("답변 후 실시간 피드백 ON/OFF", value=True)
        
        if st.button("면접 시뮬레이션 시작하기", use_container_width=True, type="primary"):
            try:
                # 💡 캐시는 이미 생성되어 있으므로 바로 Flash 캐시를 불러와서 사용
                flash_cache = genai.caching.CachedContent.get(name=st.session_state.flash_cache_name)
                model_flash_from_cache = genai.GenerativeModel.from_cached_content(flash_cache)
                
                feedback_status = "ON" if feedback_mode else "OFF"
                start_prompt = f"""
                [사용자 명령어]
                On command: '면접시뮬레이션시작'
                Parameters: difficulty: {difficulty}, feedback_mode: '{feedback_status}'
                이제 당신에게 제공된 서류 정보를 바탕으로 첫 번째 질문을 생성해주세요.
                """
                with st.spinner("AI 면접관을 준비 중입니다..."):
                    response = model_flash_from_cache.generate_content(start_prompt)
                    first_question = response.text
                
                st.session_state.messages = [{"role": "assistant", "content": first_question}]
                st.session_state.simulation_mode = True
                st.rerun()
            except Exception as e:
                st.error(f"시뮬레이션 준비 중 오류가 발생했습니다: {e}")
                st.warning("캐시가 만료되었거나 존재하지 않습니다. '새로운 분석 시작하기'를 눌러 다시 시도해주세요.")
        
        # --- 결과물 시각화 부분 (변경 없음) ---
        if st.session_state.initial_result or st.session_state.premium_report or st.session_state.additional_questions or st.session_state.model_answers or st.session_state.simulation_report:
            st.markdown("---")
            st.subheader("📋 분석 결과 및 리포트")

            if st.session_state.initial_result:
                with st.expander("📊 초기 분석 보고서 및 대표 질문", expanded=True):
                    st.markdown(st.session_state.initial_result)
            if st.session_state.premium_report:
                with st.expander("📑 프리미엄 종합 전략 보고서"):
                    st.markdown(st.session_state.premium_report)
            if st.session_state.additional_questions:
                with st.expander("🔬 심층 해부 질문 (20개)"):
                    st.markdown(st.session_state.additional_questions)
            if st.session_state.model_answers:
                with st.expander("💡 전략적 모범 답안 패키지"):
                    st.markdown(st.session_state.model_answers)
            if st.session_state.simulation_report:
                with st.expander("📋 면접 시뮬레이션 최종 리포트", expanded=True):
                    st.markdown(st.session_state.simulation_report)
            if st.session_state.simulation_transcript:
                with st.expander("💬 면접 시뮬레이션 전체 대화 다시보기"):
                    for message in st.session_state.simulation_transcript:
                        with st.chat_message(message["role"]):
                            st.markdown(message["content"])