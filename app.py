import streamlit as st
import requests
import json
from datetime import datetime, timedelta
import pytz
import calendar
import pandas as pd

# Firebase REST API URL
FIREBASE_URL = "https://house-75550-default-rtdb.firebaseio.com"

# 한국 시간대 설정
KST = pytz.timezone('Asia/Seoul')

def get_schedules():
    """Firebase에서 스케줄 데이터 가져오기"""
    response = requests.get(f"{FIREBASE_URL}/schedules.json")
    if response.status_code == 200:
        return response.json() or {}
    return {}

def save_schedule(schedule_data):
    """Firebase에 스케줄 데이터 저장하기"""
    response = requests.post(f"{FIREBASE_URL}/schedules.json", json=schedule_data)
    return response.status_code == 200

def delete_schedule(schedule_id):
    """Firebase에서 스케줄 삭제하기"""
    response = requests.delete(f"{FIREBASE_URL}/schedules/{schedule_id}.json")
    return response.status_code == 200

def update_schedule(schedule_id, schedule_data):
    """Firebase에서 스케줄 업데이트하기"""
    response = requests.patch(f"{FIREBASE_URL}/schedules/{schedule_id}.json", json=schedule_data)
    return response.status_code == 200

def save_finance(date, category, amount, description, type_):
    """Firebase에 가계부 데이터 저장"""
    finance_ref = f"{FIREBASE_URL}/finances.json"
    finance_data = {
        'date': date.strftime('%Y-%m-%d'),
        'category': category,
        'amount': amount,
        'description': description,
        'type': type_,
        'timestamp': datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    }
    response = requests.post(finance_ref, json=finance_data)
    return response.status_code == 200

def get_finances():
    """Firebase에서 가계부 데이터 가져오기"""
    finance_ref = f"{FIREBASE_URL}/finances.json"
    response = requests.get(finance_ref)
    if response.status_code == 200:
        return response.json() or {}
    return {}

def save_fixed_expense(title, category, amount, payment_day, description):
    """Firebase에 고정지출 저장"""
    fixed_expense_ref = f"{FIREBASE_URL}/fixed_expenses.json"
    fixed_expense_data = {
        'title': title,
        'category': category,
        'amount': amount,
        'payment_day': payment_day,
        'description': description,
        'created_at': datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    }
    response = requests.post(fixed_expense_ref, json=fixed_expense_data)
    return response.status_code == 200

def get_fixed_expenses():
    """Firebase에서 고정지출 가져오기"""
    fixed_expense_ref = f"{FIREBASE_URL}/fixed_expenses.json"
    response = requests.get(fixed_expense_ref)
    if response.status_code == 200:
        return response.json() or {}
    return {}

def show_calendar(schedules):
    """달력에 일정 표시"""
    st.subheader("📅 이번 달 일정")
    
    # 현재 월의 달력 생성
    today = datetime.datetime.now()
    first_day = today.replace(day=1)
    
    if first_day.month == 12:
        last_day = first_day.replace(year=first_day.year + 1, month=1, day=1) - datetime.timedelta(days=1)
    else:
        last_day = first_day.replace(month=first_day.month + 1, day=1) - datetime.timedelta(days=1)
    
    # 요일 헤더
    cols = st.columns(7)
    for i, day in enumerate(['일', '월', '화', '수', '목', '금', '토']):
        cols[i].markdown(f"**{day}**")
    
    # 첫 주 시작 전 빈 칸
    first_weekday = first_day.weekday()
    week = []
    for _ in range((first_weekday + 1) % 7):
        week.append(None)
    
    # 날짜 채우기
    current_date = first_day
    while current_date <= last_day:
        week.append(current_date)
        if len(week) == 7:
            # 한 주 표시
            cols = st.columns(7)
            for i, date in enumerate(week):
                if date is not None:
                    date_str = date.strftime('%Y-%m-%d')
                    has_schedule = any(
                        schedule['date'] == date_str
                        for schedule in schedules.values()
                    ) if schedules else False
                    
                    if has_schedule:
                        cols[i].markdown(f"**{date.day}** :calendar:")
                        # 해당 날짜의 일정 표시
                        schedules_for_date = [
                            schedule for schedule in schedules.values()
                            if schedule['date'] == date_str
                        ]
                        if schedules_for_date:
                            for schedule in schedules_for_date:
                                cols[i].markdown(f"_{schedule['title']}_")
                    else:
                        cols[i].write(date.day)
                else:
                    cols[i].write("")
            week = []
        current_date += datetime.timedelta(days=1)
    
    # 마지막 주 남은 날짜 처리
    if week:
        cols = st.columns(7)
        for i, date in enumerate(week):
            if date is not None:
                date_str = date.strftime('%Y-%m-%d')
                has_schedule = any(
                    schedule['date'] == date_str
                    for schedule in schedules.values()
                ) if schedules else False
                
                if has_schedule:
                    cols[i].markdown(f"**{date.day}** :calendar:")
                else:
                    cols[i].write(date.day)
            else:
                cols[i].write("")

def show_monthly_statistics(finances, fixed_expenses):
    """월별 수입/지출 통계 표시"""
    if not finances and not fixed_expenses:
        st.info("등록된 가계부 내역이 없습니다.")
        return

    # 데이터프레임 생성
    records = []
    
    # 일반 지출/수입 데이터
    if finances:
        for key, value in finances.items():
            records.append({
                'date': datetime.datetime.strptime(value['date'], '%Y-%m-%d'),
                'amount': value['amount'],
                'type': value['type'],
                'category': value['category'],
                'is_fixed': False
            })
    
    # 고정지출 데이터
    if fixed_expenses:
        today = datetime.datetime.now()
        for key, value in fixed_expenses.items():
            payment_date = datetime.datetime(
                today.year,
                today.month,
                int(value['payment_day'])
            )
            records.append({
                'date': payment_date,
                'amount': value['amount'],
                'type': 'expense',
                'category': value['category'],
                'is_fixed': True
            })
    
    if records:
        df = pd.DataFrame(records)
        df['year_month'] = df['date'].dt.strftime('%Y-%m')
        
        # 월별 집계
        monthly_stats = df.pivot_table(
            values='amount',
            index='year_month',
            columns='type',
            aggfunc='sum',
            fill_value=0
        ).reset_index()

        # 통계 표시
        st.subheader("📊 월별 통계")
        
        # 그래프 표시
        fig = px.bar(monthly_stats, 
                     x='year_month',
                     y=['income', 'expense'],
                     title='월별 수입/지출 현황',
                     labels={'value': '금액', 'year_month': '월'},
                     barmode='group')
        st.plotly_chart(fig)

        # 상세 통계
        for _, row in monthly_stats.iterrows():
            with st.expander(f"{row['year_month']} 상세 내역"):
                st.write(f"수입 총액: {row['income']:,}원")
                st.write(f"지출 총액: {row['expense']:,}원")
                st.write(f"수지 차액: {row['income'] - row['expense']:,}원")
                
                # 해당 월의 카테고리별 지출 현황
                month_data = df[df['year_month'] == row['year_month']]
                
                # 고정지출과 변동지출 분리
                fixed_expenses_month = month_data[
                    (month_data['type'] == 'expense') & 
                    (month_data['is_fixed'] == True)
                ]
                variable_expenses_month = month_data[
                    (month_data['type'] == 'expense') & 
                    (month_data['is_fixed'] == False)
                ]

                col1, col2 = st.columns(2)
                
                # 고정지출 파이 차트
                with col1:
                    if not fixed_expenses_month.empty:
                        fig_fixed = px.pie(
                            fixed_expenses_month,
                            values='amount',
                            names='category',
                            title='고정지출 비율'
                        )
                        st.plotly_chart(fig_fixed)
                    else:
                        st.info("고정지출 내역이 없습니다.")

                # 변동지출 파이 차트
                with col2:
                    if not variable_expenses_month.empty:
                        fig_variable = px.pie(
                            variable_expenses_month,
                            values='amount',
                            names='category',
                            title='변동지출 비율'
                        )
                        st.plotly_chart(fig_variable)
                    else:
                        st.info("변동지출 내역이 없습니다.")

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
