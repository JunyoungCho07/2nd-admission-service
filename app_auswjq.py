import streamlit as st
import google.generativeai as genai
from pathlib import Path
import PyPDF2
import io
import base64
import datetime # 캐시 유효 기간 설정을 위해 추가

# --- 초기 설정 ---

# st.session_state 초기화 (캐시 이름 변수 추가)
if 'analysis_complete' not in st.session_state:
    st.session_state.analysis_complete = False
if 'simulation_mode' not in st.session_state:
    st.session_state.simulation_mode = False
if 'pro_cache_name' not in st.session_state:
    st.session_state.pro_cache_name = None
if 'flash_cache_name' not in st.session_state:
    st.session_state.flash_cache_name = None
if 'messages' not in st.session_state:
    st.session_state.messages = []
if 'simulation_transcript' not in st.session_state:
    st.session_state.simulation_transcript = []
if 'life_record' not in st.session_state: st.session_state.life_record = ""
if 'cover_letter' not in st.session_state: st.session_state.cover_letter = ""
if 'initial_result' not in st.session_state: st.session_state.initial_result = ""
if 'additional_questions' not in st.session_state: st.session_state.additional_questions = ""
if 'premium_report' not in st.session_state: st.session_state.premium_report = ""
if 'model_answers' not in st.session_state: st.session_state.model_answers = ""
if 'simulation_report' not in st.session_state: st.session_state.simulation_report = ""


# Secrets에서 프롬프트 로드
try:
    AI_PROMPT = st.secrets["PROMPT_SECRET"]
except (FileNotFoundError, KeyError):
    st.error("프롬프트 내용을 찾을 수 없습니다. .streamlit/secrets.toml 파일을 확인해주세요.")
    st.stop()

# API 키 설정
try:
    api_key = st.secrets["GOOGLE_API_KEY"]
    genai.configure(api_key=api_key)
    # 상세 분석용 Pro 모델
    # model_pro = genai.GenerativeModel('gemini-2.5-pro')
    PRO_MODEL_NAME = 'models/gemini-2.5-pro'
    # 실시간 대화용 Flash 모델
    # model_flash = genai.GenerativeModel('gemini-2.5-flash')
    FLASH_MODEL_NAME = 'models/gemini-2.5-flash'
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

# 이미지를 Base64로 인코딩하는 함수 (이 함수를 사용하면 안정적입니다)
def get_image_base64(path):
    try:
        with open(path, "rb") as img_file:
            return base64.b64encode(img_file.read()).decode('utf-8')
    except FileNotFoundError:
        return None

# --- 사용자 인터페이스 (UI) ---
# --- 🎈 메인 앱 로직: 시뮬레이션 모드 전환 ---

# 시뮬레이션 모드가 활성화되었으면 채팅 UI를 표시
if st.session_state.simulation_mode:
    st.title("🤖 실시간 압박 면접 시뮬레이션")

    # 채팅 기록 표시
    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])

    # 사용자 입력 처리
    if user_input := st.chat_input("답변을 입력하세요... ('종료' 입력 시 리포트 생성)"):
        # 사용자 메시지 기록
        st.session_state.messages.append({"role": "user", "content": user_input})
        with st.chat_message("user"):
            st.markdown(user_input)

        # AI 응답 생성
        with st.chat_message("assistant"):
            with st.spinner("면접관이 답변을 분석하고 다음 질문을 준비 중입니다..."):
                try:
                    # Flash 캐시를 사용하여 응답 생성
                    flash_cache = genai.caching.CachedContent.from_name(st.session_state.flash_cache_name)
                    model_flash_from_cache = genai.GenerativeModel.from_cached_content(flash_cache)
                    
                    # 프롬프트에는 전체 대화 기록과 마지막 답변만 전달
                    simulation_prompt = f"""
                    [현재 면접 대화 기록]
                    {st.session_state.messages}

                    ---
                    [사용자 명령어]
                    사용자가 방금 '{user_input}'이라고 답변했습니다. 이 답변을 분석하고, 설정된 난이도와 피드백 모드에 맞춰 다음 꼬리 질문이나 피드백을 생성해주세요.
                    만약 사용자가 '종료'를 선언했다면, 전체 대화 내용을 바탕으로 [면접 시뮬레이션 최종 리포트]를 생성해주세요.
                    """
                    response = model_flash_from_cache.generate_content(simulation_prompt)
                    ai_response = response.text
                    st.markdown(ai_response)
                    st.session_state.messages.append({"role": "assistant", "content": ai_response})
                except Exception as e:
                    st.error(f"시뮬레이션 중 오류가 발생했습니다: {e}")
    
    if st.button("시뮬레이션 종료 및 분석 모드로 돌아가기"):
        st.session_state.simulation_mode = False
        st.rerun()
    
 # --- ✨ 시뮬레이션 종료 버튼 (캐싱 버전) ---
    if st.button("시뮬레이션 종료 및 최종 리포트 생성"):
        with st.spinner("면접 전체 내용을 바탕으로 최종 리포트를 생성하고 있습니다..."):
            try:
                # 1. Pro 모델 캐시를 불러옵니다.
                pro_cache = genai.caching.CachedContent.from_name(st.session_state.pro_cache_name)
                model_pro_from_cache = genai.GenerativeModel.from_cached_content(pro_cache)

                # 2. 새로운 정보(대화 기록, 최종 명령어)만 담아 프롬프트를 구성합니다.
                report_prompt = f"""
                [면접 전체 대화 기록]
                {st.session_state.messages}
                ---
                [사용자 명령어]
                '종료' 명령입니다. 위 대화 내용을 바탕으로 [면접 시뮬레이션 최종 리포트]를 생성해주세요.
                """
                
                # 3. 캐시를 사용하여 AI에 리포트 생성 요청
                response = model_pro_from_cache.generate_content(report_prompt)

                # 4. 결과물을 session_state에 저장하기 전에, 대화 내용을 복사합니다.
                st.session_state.simulation_transcript = st.session_state.messages
                
                # 5. 결과물을 session_state에 저장
                st.session_state.simulation_report = response.text
                
                # 6. 시뮬레이션 상태 초기화 및 분석 모드로 전환
                st.session_state.simulation_mode = False
                st.session_state.messages = []
                
                # 7. Flash 캐시는 시뮬레이션이 끝나면 삭제하여 자원 정리
                if st.session_state.flash_cache_name:
                    genai.caching.CachedContent.delete(name=st.session_state.flash_cache_name)
                    st.session_state.flash_cache_name = None
                
                st.rerun()

            except Exception as e:
                st.error(f"리포트 생성 중 오류가 발생했습니다: {e}")
else:

    # 1. 이미지 삽입 (중앙 정렬)
    image_path = "JYC_clear.png"  # 👈 여기에 실제 이미지 파일 이름을 정확하게 입력하세요.
    image_base64 = get_image_base64(image_path)

    if image_base64:
        # 이미지 파일 확장자에 따라 'image/png' 또는 'image/jpeg'로 자동 변경
        file_extension = Path(image_path).suffix.lower().replace('.', '')
        if file_extension in ['jpg', 'jpeg']:
            image_type = 'image/jpeg'
        else:
            image_type = 'image/png'

        st.markdown(
            f"""
            <div style="text-align: center;">
                <img src="data:{image_type};base64,{image_base64}" 
                    alt="로고" style="width:180px; margin-bottom: 20px;">
            </div>
            """,
            unsafe_allow_html=True
        )
    else:
        st.warning(f"'{image_path}' 파일을 찾을 수 없습니다. app.py와 같은 폴더에 있는지 확인해주세요.")

    # 2. 제목 및 설명
    st.markdown("<h1 style='text-align: center;'>면접관 AI</h1>", unsafe_allow_html=True)
    st.markdown("<p style='text-align: center;'>Developed by JunyoungCho</p>", unsafe_allow_html=True)

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
            # 1. 파일이 모두 업로드 되었는지 먼저 확인합니다.
            if life_record_file and cover_letter_file:
                with st.spinner("PDF 파일을 분석하고 텍스트를 추출하는 중..."):
                    # 2. 텍스트 추출은 여기서 딱 한 번만 실행합니다.
                    life_record_text = extract_text_from_pdf(life_record_file)
                    cover_letter_text = extract_text_from_pdf(cover_letter_file)

                # 3. 텍스트 추출이 성공했는지 확인합니다.
                if life_record_text and cover_letter_text:
                    with st.spinner("AI가 분석을 위해 서류를 캐싱 중입니다...(잠시만 기다려주세요 5분 이내 완료)"):
                        try:
                            # --- 💡 1. 캐시 생성 (role 추가) ---
                            cache = genai.caching.CachedContent.create(
                                model=PRO_MODEL_NAME,
                                system_instruction=AI_PROMPT,
                                contents=[{
                                    'role': 'user', # 👈 이 텍스트 덩어리는 'user'가 제공했음을 명시
                                    'parts': [
                                        {'text': "--- [사용자 제출 자료] ---"},
                                        {'text': f"[생활기록부 내용]:\n{life_record_text}"},
                                        {'text': f"[자기소개서 내용]:\n{cover_letter_text}"}
                                    ]
                                }],
                                ttl=datetime.timedelta(hours=1)
                            )
                            st.session_state.cache_name = cache.name
                            
                            # --- 💡 2. 생성된 캐시를 바로 사용해 첫 분석 실행 ---
                            model_pro_from_cache = genai.GenerativeModel.from_cached_content(cache)
                            response = model_pro_from_cache.generate_content("이제 초기 분석을 시작하고 [초기 분석 보고서 및 대표 질문 5개]를 생성해주세요.")
                            
                            st.session_state.life_record = life_record_text
                            st.session_state.cover_letter = cover_letter_text
                            st.session_state.initial_result = response.text
                            st.session_state.analysis_complete = True
                            st.rerun()

                        except Exception as e:
                            st.error(f"캐시 생성 또는 AI 분석 중 오류가 발생했습니다: {e}")
                # (텍스트 추출 실패 시 extract_text_from_pdf 함수 내부에서 오류 메시지가 표시됩니다)
            else:
                st.error("PDF에서 텍스트를 추출하지 못했습니다.")
        else:
            st.warning("두 개의 PDF 파일을 모두 업로드해주세요.")
    # 초기 분석이 완료되면 결과 및 추가 기능 버튼 표시
    else:
        # --- 💡 3. 모든 기능에서 캐시를 사용하도록 로직 수정 ---
        st.subheader("📊 초기 분석 보고서 및 대표 질문")
        st.markdown(st.session_state.initial_result)
        
        # 새로운 분석 시작 (캐시 삭제 포함) 버튼
        if st.button("새로운 분석 시작하기", type="secondary"):
            if st.session_state.cache_name:
                with st.spinner("기존 캐시를 삭제하는 중..."):
                    genai.caching.CachedContent.delete(name=st.session_state.cache_name)
            # 모든 세션 상태 초기화
            for key in st.session_state.keys():
                del st.session_state[key]
            st.rerun()

        st.divider()
        st.subheader("⚙️ 프리미엄 기능")
        st.write("서류의 모든 잠재적 약점을 파고드는 심층 분석을 통해 면접을 완벽하게 대비하세요.")


        # 캐시된 콘텐츠로 Pro 모델 초기화
        cached_content_pro = genai.caching.get_cached_content(name=st.session_state.cache_name)
        model_pro_from_cache = genai.GenerativeModel.from_cached_content(cached_content_pro)

        col1, col2, col3 = st.columns(3)
        with col1:
            if st.button("추가 질문 추출 (20개)", use_container_width=True):
                with st.spinner("서류의 특정 문장과 단어까지 파고드는 20개의 정밀 타격 질문을 생성중입니다..."):
                    response = model_pro_from_cache.generate_content("On command: '추가질문추출'")
                    st.session_state.additional_questions = response.text
        with col2:
            if st.button("프리미엄 종합 전략 보고서", use_container_width=True):
                with st.spinner("합격 시나리오와 4D 전략 분석을 포함한 최종 보고서를 생성중입니다..."):
                    response = model_pro_from_cache.generate_content("On command: '생기부분석'")
                    st.session_state.premium_report = response.text
        with col3:
                if st.button("전략적 모범 답안 생성", use_container_width=True):
                    if not st.session_state.initial_result:
                        st.warning("모범 답안을 생성하려면 먼저 초기 분석이 필요합니다.")
                    else:
                        with st.spinner("모든 질문과 보고서 내용을 바탕으로 모범 답안을 생성중입니다..."):
                            try:
                                # 1. Pro 모델 캐시를 불러옵니다.
                                pro_cache = genai.caching.CachedContent.from_name(st.session_state.pro_cache_name)
                                model_pro_from_cache = genai.GenerativeModel.from_cached_content(pro_cache)

                                # 2. session_state에 저장된 모든 결과물을 취합합니다.
                                dynamic_context = [st.session_state.initial_result]
                                if st.session_state.additional_questions:
                                    dynamic_context.append(st.session_state.additional_questions)
                                if st.session_state.premium_report:
                                    dynamic_context.append(st.session_state.premium_report)

                                # ✨ 오류 해결: .join() 결과를 별도의 변수로 먼저 만듭니다.
                                joined_context = "\n\n---\n\n".join(dynamic_context)
                                
                                # 3. 새로운 정보(동적 컨텍스트, 최종 명령어)만 담아 프롬프트를 구성합니다.
                                answer_prompt = f"""
                                [이전 단계에서 생성된 분석 및 질문 목록]
                                {joined_context}
                        
                                ---
                                [사용자 명령어]
                                On command: '모범답안생성'
                                이제 위 분석 내용과 질문 전체에 대한 [전략적 모범 답안 패키지]를 생성해주세요.
                                """

                                # 4. 캐시를 사용하여 AI에 요청
                                response = model_pro_from_cache.generate_content(answer_prompt)
                                st.session_state.model_answers = response.text

                            except Exception as e:
                                st.error(f"모범 답안 생성 중 오류가 발생했습니다: {e}")

        st.divider()

        # --- ✨ 면접 시뮬레이션 시작 섹션 (캐시 내용 강화 버전) ---
        st.subheader("🤖 실시간 압박 면접 시뮬레이션 시작")
        st.write("AI 면접관과 함께 실제와 같은 압박 면접을 경험하고, 당신의 논리를 최종 점검하세요.")

        difficulty = st.slider("면접 난이도 설정 (1~10)", 1, 10, 5)
        feedback_mode = st.toggle("답변 후 실시간 피드백 ON/OFF", value=True)
        
        if st.button("면접 시뮬레이션 시작하기", use_container_width=True, type="primary"):
            with st.spinner("실시간 대화를 위해 Flash 모델용 캐시를 생성 중입니다... (모든 분석 내용 포함)"):
                try:
                    # --- 💡 Flash 모델용 캐시에 담을 콘텐츠 목록 준비 ---
                    flash_cache_contents = [
                        {'parts': [{'text': f"[생활기록부 내용]:\n{st.session_state.life_record}"}]},
                        {'parts': [{'text': f"[자기소개서 내용]:\n{st.session_state.cover_letter}"}]},
                        {'parts': [{'text': f"[초기 분석 보고서 및 대표 질문]:\n{st.session_state.initial_result}"}]}
                    ]
                    
                    # 추가 질문이 생성되었다면, 캐시 내용에 추가
                    if st.session_state.additional_questions:
                        flash_cache_contents.append(
                            {'parts': [{'text': f"[심층 해부 질문 (20개)]:\n{st.session_state.additional_questions}"}]}
                        )

                    # --- 💡 Flash 모델용 캐시 생성 (role 추가) ---
                    flash_cache = genai.caching.CachedContent.create(
                        model=FLASH_MODEL_NAME,
                        system_instruction=AI_PROMPT,
                        contents=[{
                            'role': 'user', # 👈 모든 사전 정보를 'user'의 컨텍스트로 제공
                            'parts': [item['parts'][0] for item in flash_cache_contents]
                        }],
                        ttl=datetime.timedelta(hours=1)
                    )
                    st.session_state.flash_cache_name = flash_cache.name

                    # --- 💡 생성된 Flash 캐시로 첫 질문 생성 ---
                    model_flash_from_cache = genai.GenerativeModel.from_cached_content(flash_cache)
                    feedback_status = "ON" if feedback_mode else "OFF"
                    start_prompt = f"""
                    [사용자 명령어]
                    On command: '면접시뮬레이션시작'
                    Parameters: difficulty: {difficulty}, feedback_mode: '{feedback_status}'
                    
                    이제 당신에게 제공된 모든 사전 정보(서류 원본, 초기 분석, 심층 질문 목록)를 완벽히 숙지한 상태에서, 
                    위 파라미터에 맞춰 [시작 멘트]와 함께 첫 번째 질문을 생성해주세요.
                    """
                    response = model_flash_from_cache.generate_content(start_prompt)
                    first_question = response.text
                    
                    st.session_state.messages = [{"role": "assistant", "content": first_question}]
                    st.session_state.simulation_mode = True
                    st.rerun()
                except Exception as e:
                    st.error(f"시뮬레이션 준비 중 오류가 발생했습니다: {e}")



# --- ✨ 결과물 시각화 개선 ---
        st.markdown("---") # 시각적 구분선
        st.subheader("📋 분석 결과 및 프리미엄 리포트")
        st.write("아래 섹션을 클릭하여 각 분석 내용을 확인하세요.")

        # 1. 초기 분석 보고서 및 대표 질문
        if st.session_state.initial_result:
            with st.expander("📊 초기 분석 보고서 및 대표 질문", expanded=True): # 기본적으로 열려있게
                st.markdown(st.session_state.initial_result)

        # 2. 프리미엄 종합 전략 보고서
        if st.session_state.premium_report:
            with st.expander("📑 프리미엄 종합 전략 보고서"):
                st.markdown(st.session_state.premium_report)

        # 3. 심층 해부 질문 (20개)
        if st.session_state.additional_questions:
            with st.expander("🔬 심층 해부 질문 (20개)"):
                st.markdown(st.session_state.additional_questions)

        # 4. 전략적 모범 답안 패키지
        if st.session_state.model_answers:
            with st.expander("💡 전략적 모범 답안 패키지"):
                st.markdown(st.session_state.model_answers)

        # 5. 면접 시뮬레이션 최종 리포트 (시뮬레이션 후 생성)
        if st.session_state.simulation_report:
            with st.expander("📋 면접 시뮬레이션 최종 리포트", expanded=True): # 시뮬레이션 후 강조
                st.markdown(st.session_state.simulation_report)
                
        # 6. 면접 시뮬레이션 대화 기록 (신규 추가)
        if st.session_state.simulation_transcript:
            with st.expander("💬 면접 시뮬레이션 전체 대화 다시보기"):
                for message in st.session_state.simulation_transcript:
                    with st.chat_message(message["role"]):
                        st.markdown(message["content"])

        st.markdown("---") # 시각적 구분선