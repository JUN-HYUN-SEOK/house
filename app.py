import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
import datetime

st.set_page_config(page_title="가족 가계부 & 일정 공유", layout="wide")

# 사이드바 메뉴
menu = st.sidebar.selectbox("메뉴 선택", ["🏠 홈", "💰 가계부", "📅 일정 공유", "📂 엑셀 파일 업로드"])

# 👉 1. 홈 화면
if menu == "🏠 홈":
    st.title("👨‍👩‍👧‍👦 가족 가계부 & 일정 공유")
    st.write("""
    가족 구성원들이 함께 사용할 수 있는 **가계부 & 일정 공유 웹앱**입니다.  
    - 💰 **가계부**: 수입/지출을 기록하고 월별 지출 분석  
    - 📅 **일정 공유**: 가족 일정 추가 및 달력에서 보기  
    - 📂 **엑셀 업로드**: 가계부 데이터를 엑셀로 저장 및 불러오기  
    """)
    st.image("https://source.unsplash.com/800x400/?family,finance", use_container_width=True)

# 👉 2. 가계부 기능
elif menu == "💰 가계부":
    st.title("💰 가계부 관리")

    # 가계부 데이터를 저장할 데이터프레임
    if 'data' not in st.session_state:
        st.session_state['data'] = pd.DataFrame(columns=['Date', 'Description', 'Amount'])

    # 일정 내용 입력 기능 추가
    st.header("일정 내용 입력")
    date = st.date_input("날짜 선택")
    description = st.text_input("설명 입력")
    amount = st.number_input("금액 입력", min_value=0)

    if st.button("추가"):
        new_data = pd.DataFrame({'Date': [date], 'Description': [description], 'Amount': [amount]})
        st.session_state['data'] = pd.concat([st.session_state['data'], new_data], ignore_index=True)
        st.success("데이터가 추가되었습니다.")

    # 가계부 데이터 표시
    st.header("가계부 데이터")
    st.dataframe(st.session_state['data'])

    # 가계부 데이터 삭제 기능 추가
    st.header("데이터 삭제")
    if len(st.session_state['data']) > 0:
        delete_index = st.number_input("삭제할 데이터의 인덱스 입력", 
                                     min_value=0, 
                                     max_value=len(st.session_state['data'])-1, 
                                     step=1)
        
        if st.button("삭제"):
            st.session_state['data'] = st.session_state['data'].drop(delete_index).reset_index(drop=True)
            st.success("데이터가 삭제되었습니다.")
    else:
        st.warning("삭제할 데이터가 없습니다.")

    # 지출 분석 차트
    st.write("### 📊 지출 분석")
    fig, ax = plt.subplots()
    st.session_state['data'].groupby("Description")["Amount"].sum().plot(kind="bar", ax=ax)
    st.pyplot(fig)

# 👉 3. 일정 공유 기능
elif menu == "📅 일정 상시 공유":
    show_calendar_page()

# 👉 4. 엑셀 파일 업로드 기능
elif menu == "📂 엑셀 파일 업로드":
    st.title("📂 엑셀 파일 업로드")

    uploaded_file = st.file_uploader("📤 엑셀 파일을 업로드하세요", type=["xlsx", "xls"])

    if uploaded_file is not None:
        df = pd.read_excel(uploaded_file)
        st.write("### 📊 업로드된 데이터 미리보기")
        st.dataframe(df)

def init_session_state():
    if 'events' not in st.session_state:
        st.session_state.events = []
    if 'edit_mode' not in st.session_state:
        st.session_state.edit_mode = None

def show_calendar_page():
    st.title("가족 일정 공유 :family:")
    st.markdown("<span style='color: #FF6B6B; background-color: #FFF3F3; padding: 4px 12px; border-radius: 20px;'>!우리가족 화이팅!</span>", unsafe_allow_html=True)
    
    # 새 일정 입력
    st.subheader("새 일정 추가")
    with st.form(key="add_event"):
        col1, col2 = st.columns([1, 2])
        with col1:
            date = st.date_input("날짜", datetime.datetime.now())
        with col2:
            title = st.text_input("제목")
        description = st.text_area("내용")
        submitted = st.form_submit_button("일정 추가")
        
        if submitted and title:
            st.session_state.events.append({
                'date': date,
                'title': title,
                'description': description
            })
            st.success("일정이 추가되었습니다!")
            st.rerun()

    # 일정 목록
    st.subheader("등록된 일정")
    if st.session_state.events:
        for idx, event in enumerate(st.session_state.events):
            col1, col2, col3 = st.columns([3, 1, 1])
            with col1:
                st.write(f"📅 {event['date'].strftime('%Y-%m-%d')} - {event['title']}")
            with col2:
                if st.button("수정", key=f"edit_{idx}"):
                    st.session_state.edit_mode = idx
            with col3:
                if st.button("삭제", key=f"delete_{idx}"):
                    st.session_state.events.pop(idx)
                    st.rerun()
            
            st.text_area("상세 내용", event['description'], key=f"desc_{idx}", disabled=True)
            st.divider()

            # 수정 모드
            if st.session_state.edit_mode == idx:
                with st.form(key=f"edit_form_{idx}"):
                    new_date = st.date_input("날짜 수정", event['date'])
                    new_title = st.text_input("제목 수정", event['title'])
                    new_desc = st.text_area("내용 수정", event['description'])
                    col1, col2 = st.columns(2)
                    with col1:
                        if st.form_submit_button("저장"):
                            st.session_state.events[idx] = {
                                'date': new_date,
                                'title': new_title,
                                'description': new_desc
                            }
                            st.session_state.edit_mode = None
                            st.success("수정되었습니다!")
                            st.rerun()
                    with col2:
                        if st.form_submit_button("취소"):
                            st.session_state.edit_mode = None
                            st.rerun()
    else:
        st.info("등록된 일정이 없습니다.")

    # 달력 뷰
    st.subheader("이번 달 일정")
    today = datetime.datetime.now()
    first_day = today.replace(day=1)
    
    # 다음 달의 첫 날을 구한 뒤, 하루를 빼서 이번 달의 마지막 날을 구합니다
    if first_day.month == 12:
        last_day = first_day.replace(year=first_day.year + 1, month=1, day=1) - datetime.timedelta(days=1)
    else:
        last_day = first_day.replace(month=first_day.month + 1, day=1) - datetime.timedelta(days=1)
    
    # 달력에 표시할 날짜 범위 생성
    month_dates = pd.date_range(start=first_day, end=last_day, freq='D')
    
    # 요일 헤더
    cols = st.columns(7)
    for i, day in enumerate(['일', '월', '화', '수', '목', '금', '토']):
        cols[i].markdown(f"**{day}**")
    
    # 첫 주의 시작 전 빈 칸 처리
    first_weekday = first_day.weekday()
    if first_weekday != 6:  # 일요일이 아니면
        cols = st.columns(7)
        for i in range(first_weekday + 1):
            cols[i].write("")
    
    # 날짜 표시
    current_col = (first_weekday + 1) % 7
    for date in month_dates:
        if current_col == 0:
            cols = st.columns(7)
        
        has_event = any(event['date'] == date.date() for event in st.session_state.events)
        if has_event:
            cols[current_col].markdown(f"**{date.day}** :calendar:")
        else:
            cols[current_col].write(date.day)
        
        current_col = (current_col + 1) % 7

if __name__ == "__main__":
    init_session_state()
    show_calendar_page()
# streamlit run app.py
