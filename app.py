import streamlit as st
import requests
from datetime import datetime
import calendar
import pandas as pd
import plotly.express as px
import pytz

# Firebase URL
FIREBASE_URL = "https://house-75550-default-rtdb.firebaseio.com"

# 한국 시간대 설정
KST = pytz.timezone('Asia/Seoul')

def create_calendar(events):
    # 현재 선택된 년월 가져오기
    selected_date = st.session_state.get('selected_date', datetime.today())
    col1, col2 = st.columns([6,1])
    with col1:
        selected_date = st.date_input("월 선택", selected_date)
    st.session_state.selected_date = selected_date
    
    # 달력 생성
    cal = calendar.monthcalendar(selected_date.year, selected_date.month)
    
    # 달력 헤더
    cols = st.columns(7)
    days = ['월', '화', '수', '목', '금', '토', '일']
    for col, day in zip(cols, days):
        col.markdown(f"**{day}**")
    
    # 달력 내용
    for week in cal:
        cols = st.columns(7)
        for col, day in zip(cols, week):
            if day != 0:
                date_str = f"{selected_date.year}-{selected_date.month:02d}-{day:02d}"
                
                # 해당 날짜에 이벤트가 있는지 확인
                has_event = any(event['date'] == date_str for event in events.values())
                
                # 날짜 버튼 생성 (이벤트가 있으면 노란색 배경)
                if has_event:
                    col.markdown(f"""
                        <div style='background-color: #FFE5B4; padding: 10px; border-radius: 5px;'>
                            <strong>{day}</strong>
                            {"📅" if has_event else ""}
                        </div>
                    """, unsafe_allow_html=True)
                else:
                    if col.button(f"{day}", key=f"day_{date_str}"):
                        st.session_state.selected_day = date_str
                        st.session_state.show_event_form = True

def show_budget_form():
    st.subheader("💰 가계부 입력")
    with st.form("budget_form"):
        year_month = st.date_input("년월 선택").strftime("%Y-%m")
        category = st.selectbox("분류", ["수입", "고정지출", "변동지출"])
        title = st.text_input("항목")
        amount = st.number_input("금액", min_value=0)
        
        if st.form_submit_button("저장"):
            data = {
                "year_month": year_month,
                "category": category,
                "title": title,
                "amount": amount
            }
            
            response = requests.post(f"{FIREBASE_URL}/budget.json", json=data)
            if response.status_code == 200:
                st.success("저장되었습니다!")
                st.rerun()

def show_event_form():
    if st.session_state.get('show_event_form', False):
        st.subheader("📅 일정 등록")
        selected_day = st.session_state.get('selected_day', datetime.today().strftime("%Y-%m-%d"))
        
        with st.form("event_form"):
            st.write(f"선택된 날짜: {selected_day}")
            title = st.text_input("일정 제목")
            memo = st.text_area("메모")
            
            if st.form_submit_button("저장"):
                data = {
                    "date": selected_day,
                    "title": title,
                    "memo": memo
                }
                
                response = requests.post(f"{FIREBASE_URL}/events.json", json=data)
                if response.status_code == 200:
                    st.success("일정이 저장되었습니다!")
                    st.session_state.show_event_form = False
                    st.rerun()

def show_budget_summary():
    response = requests.get(f"{FIREBASE_URL}/budget.json")
    if response.status_code == 200:
        records = response.json() or {}
        
        if records:
            df = pd.DataFrame.from_dict(records, orient='index')
            selected_month = st.session_state.selected_date.strftime("%Y-%m")
            
            # 선택된 월의 데이터만 필터링
            df = df[df['year_month'] == selected_month]
            
            if not df.empty:
                st.subheader(f"💰 {selected_month} 가계부 요약")
                
                # 카테고리별 합계
                income = df[df['category'] == '수입']['amount'].sum()
                fixed_exp = df[df['category'] == '고정지출']['amount'].sum()
                var_exp = df[df['category'] == '변동지출']['amount'].sum()
                
                col1, col2, col3, col4 = st.columns(4)
                col1.metric("수입", f"{income:,}원")
                col2.metric("고정지출", f"{fixed_exp:,}원")
                col3.metric("변동지출", f"{var_exp:,}원")
                col4.metric("잔액", f"{income - fixed_exp - var_exp:,}원")
                
                # 상세 내역
                st.markdown("### 상세 내역")
                for category in ['수입', '고정지출', '변동지출']:
                    cat_df = df[df['category'] == category]
                    if not cat_df.empty:
                        st.markdown(f"#### {category}")
                        st.dataframe(cat_df[['title', 'amount']])

def main():
    st.title("💰 우리집 가계부 & 일정")
    
    tab1, tab2 = st.tabs(["📅 일정관리", "💰 가계부"])
    
    with tab1:
        # 일정 데이터 가져오기
        response = requests.get(f"{FIREBASE_URL}/events.json")
        events = response.json() or {}
        
        # 달력 표시
        create_calendar(events)
        
        # 일정 등록 폼
        show_event_form()
        
        # 일정 목록
        st.markdown("### 📋 일정 목록")
        for event_id, event in events.items():
            col1, col2 = st.columns([3,1])
            with col1:
                st.markdown(f"""
                    📅 {event['date']}<br>
                    ✍️ {event['title']}
                """, unsafe_allow_html=True)
            with col2:
                if st.button("삭제", key=f"del_event_{event_id}"):
                    requests.delete(f"{FIREBASE_URL}/events/{event_id}.json")
                    st.rerun()
    
    with tab2:
        show_budget_form()
        show_budget_summary()

if __name__ == "__main__":
    main()
