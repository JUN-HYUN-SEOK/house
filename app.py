import streamlit as st
# 가장 먼저 페이지 설정을 해야 합니다
st.set_page_config(page_title="가족 일정 및 가계부", layout="wide")

import pandas as pd
import matplotlib.pyplot as plt
import datetime
from firebase_admin import credentials, initialize_app, db
import os
import firebase_admin
import plotly.express as px

# 사이드바 메뉴
menu = st.sidebar.selectbox("메뉴 선택", ["🏠 홈", "💰 가계부", "📅 일정 공유", "📂 엑셀 파일 업로드"])

# 현재 파일의 디렉토리 경로를 사용
current_dir = os.path.dirname(os.path.abspath(__file__))
key_path = os.path.join(current_dir, 'serviceAccountKey.json')

st.write("현재 디렉토리:", current_dir)
st.write("찾고 있는 키 파일:", key_path)

# 파일 존재 여부 확인
if os.path.exists(key_path):
    st.success(f"키 파일을 찾았습니다: {key_path}")
    
    # Firebase 초기화 시도
    try:
        if not firebase_admin._apps:
            cred = credentials.Certificate(key_path)
            firebase_app = initialize_app(cred, {
                'databaseURL': 'https://house-75550-default-rtdb.firebaseio.com'
            })
            st.success("Firebase 연결 성공!")
        
        # Firebase Realtime Database 참조 생성
        ref = db.reference('/')
        
    except Exception as e:
        st.error(f"Firebase 초기화 오류: {str(e)}")
else:
    st.error(f"키 파일을 찾을 수 없습니다: {key_path}")
    st.error("현재 디렉토리의 파일 목록:")
    st.write(os.listdir(current_dir))

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

def show_monthly_statistics(finances, fixed_expenses):
    """월별 수입/지출 통계 표시 (고정지출 포함)"""
    if not finances and not fixed_expenses:
        st.info("등록된 가계부 내역이 없습니다.")
        return

    # 일반 지출/수입 데이터프레임 생성
    records = []
    for key, value in finances.items():
        records.append({
            'date': datetime.datetime.strptime(value['date'], '%Y-%m-%d'),
            'amount': value['amount'],
            'type': value['type'],
            'category': value['category'],
            'is_fixed': False
        })
    
    # 고정지출 데이터 추가
    today = datetime.datetime.now()
    if fixed_expenses:
        for key, value in fixed_expenses.items():
            # 현재 월의 고정지출 날짜 생성
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
            event_data = {
                'date': date.strftime('%Y-%m-%d'),
                'title': title,
                'description': description
            }
            save_event(event_data)
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

    # 가계부 탭 (이전 코드와 동일)
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

    # 고정지출 설정 탭 (이전 코드와 동일)
    with tab3:
        # ... (이전 코드와 동일)
        pass

if __name__ == "__main__":
    main()
# streamlit run app.py
