import streamlit as st
st.set_page_config(page_title="가족 일정 및 가계부", layout="wide")

from firebase_admin import credentials, initialize_app, db
import datetime
import os
import firebase_admin
import pandas as pd
import plotly.express as px

# Firebase 초기화
current_dir = os.path.dirname(os.path.abspath(__file__))
key_path = os.path.join(current_dir, 'serviceAccountKey.json')

if not firebase_admin._apps:
    cred = credentials.Certificate(key_path)
    firebase_app = initialize_app(cred, {
        'databaseURL': 'https://house-75550-default-rtdb.firebaseio.com'
    })

# Firebase 데이터베이스 참조
schedule_ref = db.reference('schedules')
finance_ref = db.reference('finances')
fixed_expense_ref = db.reference('fixed_expenses')

def save_schedule(date, title, description):
    """Firebase에 일정 저장"""
    schedule_ref.push({
        'date': date.strftime('%Y-%m-%d'),
        'title': title,
        'description': description,
        'timestamp': datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    })

def get_schedules():
    """Firebase에서 일정 가져오기"""
    schedules = schedule_ref.get()
    return schedules if schedules else {}

def save_finance(date, category, amount, description, type_):
    """Firebase에 가계부 데이터 저장"""
    finance_ref.push({
        'date': date.strftime('%Y-%m-%d'),
        'category': category,
        'amount': amount,
        'description': description,
        'type': type_,
        'timestamp': datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    })

def get_finances():
    """Firebase에서 가계부 데이터 가져오기"""
    finances = finance_ref.get()
    return finances if finances else {}

def save_fixed_expense(title, category, amount, payment_day, description):
    """Firebase에 고정지출 저장"""
    fixed_expense_ref.push({
        'title': title,
        'category': category,
        'amount': amount,
        'payment_day': payment_day,
        'description': description,
        'created_at': datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    })

def get_fixed_expenses():
    """Firebase에서 고정지출 가져오기"""
    fixed_expenses = fixed_expense_ref.get()
    return fixed_expenses if fixed_expenses else {}

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

def main():
    # 탭 생성
    tab1, tab2, tab3 = st.tabs(["📅 일정 관리", "💰 가계부", "⚙️ 고정지출 설정"])
    
    # 일정 관리 탭
    with tab1:
        st.title("가족 일정 공유 :family:")
        
        # 좌우 컬럼으로 분리
        left_col, right_col = st.columns([1, 2])
        
        # 왼쪽 컬럼: 일정 입력 및 목록
        with left_col:
            # 일정 입력
            with st.form("schedule_form"):
                date = st.date_input("날짜 선택", datetime.datetime.now())
                title = st.text_input("일정 제목")
                description = st.text_area("일정 내용")
                submitted = st.form_submit_button("일정 추가")
                
                if submitted and title:
                    save_schedule(date, title, description)
                    st.success("일정이 추가되었습니다!")
                    st.rerun()
            
            # 일정 목록
            st.subheader("📝 등록된 일정")
            schedules = get_schedules()
            if schedules:
                for key, schedule in sorted(schedules.items(), 
                                         key=lambda x: x[1]['date'],
                                         reverse=True):
                    with st.expander(f"{schedule['date']}: {schedule['title']}"):
                        st.write(schedule['description'])
                        if st.button("삭제", key=f"delete_schedule_{key}"):
                            schedule_ref.child(key).delete()
                            st.success("일정이 삭제되었습니다!")
                            st.rerun()
            else:
                st.info("등록된 일정이 없습니다.")
        
        # 오른쪽 컬럼: 달력
        with right_col:
            show_calendar(schedules)

    # 가계부 탭
    with tab2:
        st.title("가족 가계부 💰")
        
        # 입력 폼과 통계를 구분하기 위한 컬럼
        input_col, stats_col = st.columns([1, 2])
        
        with input_col:
            # 가계부 입력 폼
            with st.form("finance_form"):
                finance_date = st.date_input("날짜", datetime.datetime.now())
                finance_type = st.selectbox("유형", ["수입", "지출"])
                amount = st.number_input("금액", min_value=0)
                category = st.selectbox(
                    "분류",
                    ["급여", "상여금", "기타수입"] if finance_type == "수입" else 
                    ["식비", "교통비", "주거비", "의료비", "교육비", "문화생활", "기타지출"]
                )
                finance_description = st.text_area("내용")
                
                if st.form_submit_button("등록"):
                    if amount > 0:
                        save_finance(
                            finance_date,
                            category,
                            amount,
                            finance_description,
                            'income' if finance_type == "수입" else 'expense'
                        )
                        st.success("등록되었습니다!")
                        st.rerun()
                    else:
                        st.error("금액을 입력해주세요.")
        
        with stats_col:
            # 가계부 통계
            finances = get_finances()
            fixed_expenses = get_fixed_expenses()
            show_monthly_statistics(finances, fixed_expenses)
        
        # 상세 내역
        st.subheader("📝 상세 내역")
        if finances:
            for key, finance in sorted(finances.items(), 
                                     key=lambda x: x[1]['date'],
                                     reverse=True):
                with st.expander(
                    f"{finance['date']} - {finance['category']} "
                    f"({finance['amount']:,}원)"
                ):
                    st.write(f"유형: {'수입' if finance['type']=='income' else '지출'}")
                    st.write(f"내용: {finance['description']}")
                    if st.button("삭제", key=f"delete_finance_{key}"):
                        finance_ref.child(key).delete()
                        st.success("삭제되었습니다!")
                        st.rerun()

    # 고정지출 설정 탭
    with tab3:
        st.title("고정지출 설정 ⚙️")
        
        # 고정지출 입력
        with st.form("fixed_expense_form"):
            col1, col2 = st.columns(2)
            with col1:
                fixed_title = st.text_input("지출 항목")
                fixed_category = st.selectbox(
                    "분류",
                    ["주거비", "관리비", "통신비", "보험료", "교육비", "기타고정지출"]
                )
            with col2:
                fixed_amount = st.number_input("금액", min_value=0)
                payment_day = st.number_input(
                    "매월 결제일",
                    min_value=1,
                    max_value=31,
                    value=1
                )
            fixed_description = st.text_area("설명")
            
            if st.form_submit_button("고정지출 등록"):
                if fixed_amount > 0 and fixed_title:
                    save_fixed_expense(
                        fixed_title,
                        fixed_category,
                        fixed_amount,
                        payment_day,
                        fixed_description
                    )
                    st.success("고정지출이 등록되었습니다!")
                    st.rerun()
                else:
                    st.error("항목과 금액을 입력해주세요.")
        
        # 등록된 고정지출 목록
        st.subheader("등록된 고정지출 목록")
        fixed_expenses = get_fixed_expenses()
        
        if fixed_expenses:
            total_fixed = sum(item['amount'] for item in fixed_expenses.values())
            st.info(f"월 고정지출 총액: {total_fixed:,}원")
            
            for key, expense in fixed_expenses.items():
                with st.expander(
                    f"{expense['title']} - {expense['category']} "
                    f"({expense['amount']:,}원)"
                ):
                    st.write(f"결제일: 매월 {expense['payment_day']}일")
                    st.write(f"설명: {expense['description']}")
                    if st.button("삭제", key=f"delete_fixed_{key}"):
                        fixed_expense_ref.child(key).delete()
                        st.success("삭제되었습니다!")
                        st.rerun()
        else:
            st.info("등록된 고정지출이 없습니다.")

if __name__ == "__main__":
    main()
