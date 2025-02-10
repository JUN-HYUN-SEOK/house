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
elif menu == "📅 일정 공유":
    st.title("📅 가족 일정 공유")

    # 일정 입력 폼
    with st.form("calendar_form"):
        event_date = st.date_input("📅 일정 날짜 선택")
        event_desc = st.text_input("✏️ 일정 내용 입력")
        submit = st.form_submit_button("✅ 추가")

        if submit:
            st.success(f"📌 일정 추가됨: {event_date} - {event_desc}")

    # 일정 목록 (임시 데이터)
    st.write("### 📝 가족 일정 목록")
    st.write("📌 2025-02-10: 아빠 생일 🎂")
    st.write("📌 2025-02-15: 가족 여행 🏝️")

# 👉 4. 엑셀 파일 업로드 기능
elif menu == "📂 엑셀 파일 업로드":
    st.title("📂 엑셀 파일 업로드")

    uploaded_file = st.file_uploader("📤 엑셀 파일을 업로드하세요", type=["xlsx", "xls"])

    if uploaded_file is not None:
        df = pd.read_excel(uploaded_file)
        st.write("### 📊 업로드된 데이터 미리보기")
        st.dataframe(df)
