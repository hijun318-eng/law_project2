MOCK_USERS = [
    {"id": 1, "name": "김민준", "email": "minjun@example.com", "join_date": "2024-01-15", "last_login": "2026-06-30", "status": "active", "questions": 12},
    {"id": 2, "name": "이서연", "email": "seoyeon@example.com", "join_date": "2024-02-20", "last_login": "2026-06-28", "status": "active", "questions": 8},
    {"id": 3, "name": "박지호", "email": "jiho@example.com", "join_date": "2024-03-10", "last_login": "2026-05-15", "status": "suspended", "questions": 3},
    {"id": 4, "name": "최유진", "email": "yujin@example.com", "join_date": "2024-04-05", "last_login": "2026-06-29", "status": "active", "questions": 24},
    {"id": 5, "name": "정다은", "email": "daeun@example.com", "join_date": "2024-05-12", "last_login": "2026-06-27", "status": "active", "questions": 6},
    {"id": 6, "name": "한승호", "email": "seungho@example.com", "join_date": "2024-06-01", "last_login": "2026-04-10", "status": "suspended", "questions": 1},
    {"id": 7, "name": "오미래", "email": "mirae@example.com", "join_date": "2024-06-15", "last_login": "2026-06-30", "status": "active", "questions": 15},
    {"id": 8, "name": "임태양", "email": "taeyang@example.com", "join_date": "2024-07-20", "last_login": "2026-06-25", "status": "active", "questions": 9},
]

MOCK_QUESTIONS = [
    {"id": 1, "user": "김민준", "category": "임금체불", "question": "3개월째 급여를 받지 못했습니다. 어떻게 신고하나요?", "date": "2026-06-30 14:23", "likes": 45, "dislikes": 2},
    {"id": 2, "user": "이서연", "category": "부당해고", "question": "갑자기 해고 통보를 받았는데 정당한 이유가 없습니다.", "date": "2026-06-30 11:05", "likes": 38, "dislikes": 4},
    {"id": 3, "user": "최유진", "category": "퇴직금", "question": "1년 2개월 근무 후 퇴직합니다. 퇴직금 계산 방법이 궁금합니다.", "date": "2026-06-29 16:40", "likes": 62, "dislikes": 1},
    {"id": 4, "user": "정다은", "category": "연차휴가", "question": "입사 후 1년이 안 됐는데 연차가 몇 개인가요?", "date": "2026-06-29 09:15", "likes": 29, "dislikes": 3},
    {"id": 5, "user": "오미래", "category": "최저임금", "question": "2026년 최저임금이 얼마인가요? 현재 9,500원을 받고 있습니다.", "date": "2026-06-28 20:30", "likes": 18, "dislikes": 12},
    {"id": 6, "user": "임태양", "category": "포괄임금제", "question": "회사가 포괄임금제라며 야근수당을 안 줍니다.", "date": "2026-06-28 15:00", "likes": 11, "dislikes": 19},
    {"id": 7, "user": "한승호", "category": "직장내괴롭힘", "question": "상사의 지속적인 폭언과 따돌림으로 고통받고 있습니다.", "date": "2026-06-27 13:22", "likes": 33, "dislikes": 5},
    {"id": 8, "user": "박지호", "category": "산업재해", "question": "업무 중 부상을 당했는데 산재 신청 절차가 어떻게 되나요?", "date": "2026-06-27 10:11", "likes": 47, "dislikes": 2},
]

FAQ_DATA = [
    {"name": "임금체불", "count": 342},
    {"name": "부당해고", "count": 287},
    {"name": "퇴직금", "count": 198},
    {"name": "연차휴가", "count": 156},
    {"name": "최저임금", "count": 134},
    {"name": "직장내괴롭힘", "count": 98},
    {"name": "산업재해", "count": 76},
]

CATEGORY_PIE = [
    {"name": "임금체불", "value": 28},
    {"name": "부당해고", "value": 23},
    {"name": "퇴직금", "value": 16},
    {"name": "연차휴가", "value": 13},
    {"name": "최저임금", "value": 11},
    {"name": "기타", "value": 9},
]

DAILY_DATA = [
    {"date": "6/25", "questions": 47, "users": 12},
    {"date": "6/26", "questions": 52, "users": 15},
    {"date": "6/27", "questions": 61, "users": 18},
    {"date": "6/28", "questions": 58, "users": 14},
    {"date": "6/29", "questions": 73, "users": 21},
    {"date": "6/30", "questions": 84, "users": 27},
    {"date": "7/1", "questions": 38, "users": 9},
]

FEEDBACK_DATA = [
    {"id": 1, "question": "퇴직금 계산 방법이 궁금합니다", "category": "퇴직금", "likes": 87, "dislikes": 3, "score": 96.7, "memo": ""},
    {"id": 2, "question": "임금체불 신고 절차는?", "category": "임금체불", "likes": 65, "dislikes": 8, "score": 89.0, "memo": ""},
    {"id": 3, "question": "부당해고 구제신청 방법", "category": "부당해고", "likes": 54, "dislikes": 6, "score": 90.0, "memo": ""},
    {"id": 4, "question": "연차 계산 (1년 미만)", "category": "연차휴가", "likes": 42, "dislikes": 7, "score": 85.7, "memo": ""},
    {"id": 5, "question": "최저임금 위반 시 처벌 규정", "category": "최저임금", "likes": 38, "dislikes": 9, "score": 80.9, "memo": ""},
    {"id": 6, "question": "포괄임금제가 합법인가요?", "category": "포괄임금제", "likes": 11, "dislikes": 19, "score": 36.7, "memo": ""},
    {"id": 7, "question": "수습 기간 중 해고 가능한가요?", "category": "부당해고", "likes": 14, "dislikes": 16, "score": 46.7, "memo": ""},
    {"id": 8, "question": "프리랜서도 퇴직금 받을 수 있나요?", "category": "퇴직금", "likes": 8, "dislikes": 18, "score": 30.8, "memo": ""},
]

NEWS_DATA = [
    {"id": 1, "title": "2026년 최저임금 10,030원으로 확정", "date": "2026-06-28", "category": "최저임금", "summary": "고용노동부는 2026년 적용 최저임금을 시간당 10,030원으로 최종 고시했습니다. 전년 대비 1.8% 인상된 수치로, 월 209시간 기준 약 209만 6천 원에 해당합니다."},
    {"id": 2, "title": "직장 내 괴롭힘 신고 건수 역대 최고치", "date": "2026-06-25", "category": "직장내괴롭힘", "summary": "상반기 직장 내 괴롭힘 신고 건수가 전년 동기 대비 34% 증가하며 역대 최고치를 기록했습니다. 고용노동부는 사업장 실태조사를 강화할 방침입니다."},
    {"id": 3, "title": "포괄임금제 남용 방지 지침 개정", "date": "2026-06-20", "category": "임금", "summary": "고용노동부가 포괄임금제 남용 방지를 위한 행정지침을 개정했습니다. 상시 연장근로가 없는 업종에서 포괄임금 약정을 맺을 경우 근로감독 대상이 될 수 있습니다."},
    {"id": 4, "title": "육아휴직 급여 상한액 월 200만 원으로 상향", "date": "2026-06-15", "category": "육아휴직", "summary": "7월부터 육아휴직 급여 상한액이 월 150만 원에서 200만 원으로 인상됩니다. 첫 3개월은 통상임금의 80%, 나머지 기간은 50%가 지급됩니다."},
    {"id": 5, "title": "대기업 노조 임금교섭 본격화", "date": "2026-06-12", "category": "노조", "summary": "주요 대기업 노동조합이 하반기 임금교섭 요구안을 확정하고 교섭 절차에 들어갔습니다. 임금 인상률과 근로시간 개편, 성과급 산정 기준이 핵심 쟁점으로 꼽힙니다."},
    {"id": 6, "title": "부당해고 구제신청 온라인 접수 증가", "date": "2026-06-08", "category": "해고", "summary": "노동위원회 온라인 구제신청 이용이 늘면서 해고 사유와 절차 적법성에 관한 상담 수요도 증가하고 있습니다. 전문가들은 해고 통지서와 근무기록 보관을 강조했습니다."},
    {"id": 7, "title": "퇴직연금 미가입 사업장 점검 확대", "date": "2026-06-03", "category": "퇴직금", "summary": "정부가 퇴직급여 제도 운영 실태 점검을 확대합니다. 계속근로기간 1년 이상 근로자의 퇴직급여 보장 여부와 적립금 운용 현황이 주요 점검 대상입니다."},
    {"id": 8, "title": "산업재해 신청 절차 간소화 논의", "date": "2026-05-30", "category": "산재", "summary": "업무상 질병과 사고에 대한 산재 신청 절차를 간소화하는 방안이 논의되고 있습니다. 입증 자료 제출 부담과 처리 기간 단축이 주요 과제로 제시됐습니다."},
]

