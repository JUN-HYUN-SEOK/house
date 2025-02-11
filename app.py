import streamlit as st
import requests
from datetime import datetime
import calendar
import pandas as pd
import plotly.express as px
import pytz
from io import BytesIO

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
        year_month = st.date_input("날짜 선택")
        category = st.selectbox("분류", ["수입", "고정지출", "변동지출"])
        
        # 카테고리별 상세 항목
        if category == "수입":
            title = st.selectbox("항목", ["급여", "보너스", "기타수입"])
        elif category == "고정지출":
            title = st.selectbox("항목", ["월세", "관리비", "통신비", "보험료", "교통비", "기타고정지출"])
        else:  # 변동지출
            title = st.selectbox("항목", ["식비", "생활용품", "의류", "의료비", "문화생활", "기타변동지출"])
            
        amount = st.number_input("금액", min_value=0)
        memo = st.text_input("메모")
        
        if st.form_submit_button("저장"):
            data = {
                "date": year_month.strftime("%Y-%m-%d"),
                "year_month": year_month.strftime("%Y-%m"),
                "category": category,
                "title": title,
                "amount": amount,
                "memo": memo
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
            df['record_id'] = df.index  # 레코드 ID 저장
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
                        
                        for _, row in cat_df.iterrows():
                            col1, col2, col3, col4 = st.columns([3,2,1,1])
                            
                            with col1:
                                st.write(f"📅 {row.get('date', row['year_month'])}")
                                st.write(f"✍️ {row['title']}")
                            
                            with col2:
                                st.write(f"💰 {row['amount']:,}원")
                                if 'memo' in row:
                                    st.write(f"📝 {row['memo']}")
                            
                            with col3:
                                if st.button("수정", key=f"edit_{row['record_id']}"):
                                    st.session_state.editing = row['record_id']
                                    st.session_state.edit_data = row.to_dict()
                            
                            with col4:
                                if st.button("삭제", key=f"del_{row['record_id']}"):
                                    if requests.delete(f"{FIREBASE_URL}/budget/{row['record_id']}.json").status_code == 200:
                                        st.success("삭제되었습니다!")
                                        st.rerun()
                
                # 수정 폼
                if 'editing' in st.session_state:
                    st.markdown("### ✏️ 항목 수정")
                    with st.form(key="edit_form"):
                        edit_data = st.session_state.edit_data
                        
                        # date가 없으면 year_month 사용
                        initial_date = datetime.strptime(
                            edit_data.get('date', edit_data['year_month'] + "-01"), 
                            "%Y-%m-%d"
                        )
                        new_date = st.date_input("날짜", initial_date)
                        
                        new_category = st.selectbox("분류", 
                            ["수입", "고정지출", "변동지출"], 
                            index=["수입", "고정지출", "변동지출"].index(edit_data['category']))
                        
                        # 카테고리별 항목 선택
                        if new_category == "수입":
                            options = ["급여", "보너스", "기타수입"]
                        elif new_category == "고정지출":
                            options = ["월세", "관리비", "통신비", "보험료", "교통비", "기타고정지출"]
                        else:
                            options = ["식비", "생활용품", "의류", "의료비", "문화생활", "기타변동지출"]
                        
                        new_title = st.selectbox("항목", options, 
                            index=options.index(edit_data['title']) if edit_data['title'] in options else 0)
                        new_amount = st.number_input("금액", 
                            value=float(edit_data['amount']))
                        new_memo = st.text_input("메모", 
                            value=edit_data.get('memo', ''))
                        
                        col1, col2 = st.columns(2)
                        with col1:
                            if st.form_submit_button("수정 완료"):
                                update_data = {
                                    "date": new_date.strftime("%Y-%m-%d"),
                                    "year_month": new_date.strftime("%Y-%m"),
                                    "category": new_category,
                                    "title": new_title,
                                    "amount": new_amount,
                                    "memo": new_memo
                                }
                                
                                if requests.patch(f"{FIREBASE_URL}/budget/{st.session_state.editing}.json", 
                                    json=update_data).status_code == 200:
                                    st.success("수정되었습니다!")
                                    del st.session_state.editing
                                    del st.session_state.edit_data
                                    st.rerun()
                        
                        with col2:
                            if st.form_submit_button("취소"):
                                del st.session_state.editing
                                del st.session_state.edit_data
                                st.rerun()
                
                # 엑셀 다운로드 버튼
                if st.button("엑셀 다운로드"):
                    output = BytesIO()
                    with pd.ExcelWriter(output, engine='openpyxl') as writer:
                        for category in ['수입', '고정지출', '변동지출']:
                            cat_df = df[df['category'] == category]
                            if not cat_df.empty:
                                display_df = cat_df[['date', 'title', 'amount', 'memo']].copy()
                                display_df.columns = ['날짜', '항목', '금액', '메모']
                                display_df.to_excel(writer, sheet_name=category, index=False)
                    
                    output.seek(0)
                    st.download_button(
                        label="📥 엑셀 파일 다운로드",
                        data=output,
                        file_name=f'가계부_{selected_month}.xlsx',
                        mime='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
                    )

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
