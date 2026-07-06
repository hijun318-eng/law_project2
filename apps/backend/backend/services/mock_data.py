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

NEWS_DATA = [
    {"id": 1, "title": "2026년 최저임금 10,030원으로 확정", "date": "2026-06-28",  "summary": "고용노동부는 2026년 적용 최저임금을 시간당 10,030원으로 최종 고시했습니다. 전년 대비 1.8% 인상된 수치로, 월 209시간 기준 약 209만 6천 원에 해당합니다."},
    {"id": 2, "title": "직장 내 괴롭힘 신고 건수 역대 최고치", "date": "2026-06-25", "summary": "상반기 직장 내 괴롭힘 신고 건수가 전년 동기 대비 34% 증가하며 역대 최고치를 기록했습니다. 고용노동부는 사업장 실태조사를 강화할 방침입니다."},
    {"id": 3, "title": "포괄임금제 남용 방지 지침 개정", "date": "2026-06-20",  "summary": "고용노동부가 포괄임금제 남용 방지를 위한 행정지침을 개정했습니다. 상시 연장근로가 없는 업종에서 포괄임금 약정을 맺을 경우 근로감독 대상이 될 수 있습니다."},
    {"id": 4, "title": "육아휴직 급여 상한액 월 200만 원으로 상향", "date": "2026-06-15", "summary": "7월부터 육아휴직 급여 상한액이 월 150만 원에서 200만 원으로 인상됩니다. 첫 3개월은 통상임금의 80%, 나머지 기간은 50%가 지급됩니다."},
    {"id": 5, "title": "대기업 노조 임금교섭 본격화", "date": "2026-06-12",  "summary": "주요 대기업 노동조합이 하반기 임금교섭 요구안을 확정하고 교섭 절차에 들어갔습니다. 임금 인상률과 근로시간 개편, 성과급 산정 기준이 핵심 쟁점으로 꼽힙니다."},
    {"id": 6, "title": "부당해고 구제신청 온라인 접수 증가", "date": "2026-06-08",  "summary": "노동위원회 온라인 구제신청 이용이 늘면서 해고 사유와 절차 적법성에 관한 상담 수요도 증가하고 있습니다. 전문가들은 해고 통지서와 근무기록 보관을 강조했습니다."},
    {"id": 7, "title": "퇴직연금 미가입 사업장 점검 확대", "date": "2026-06-03", "summary": "정부가 퇴직급여 제도 운영 실태 점검을 확대합니다. 계속근로기간 1년 이상 근로자의 퇴직급여 보장 여부와 적립금 운용 현황이 주요 점검 대상입니다."},
    {"id": 8, "title": "산업재해 신청 절차 간소화 논의", "date": "2026-05-30",  "summary": "업무상 질병과 사고에 대한 산재 신청 절차를 간소화하는 방안이 논의되고 있습니다. 입증 자료 제출 부담과 처리 기간 단축이 주요 과제로 제시됐습니다."},
]


PROMPT_TEMPLATES = {
    "answer_prompt": {
        "id": "answer_prompt",
        "name": "answer_prompt",
        "description": "AI 상담 답변 생성 프롬프트",
        "version": 3,
        "content": "당신은 노동법 전문 AI입니다. 아래 컨텍스트를 반드시 참고하여 정확하게 답변하세요.\n질문: {question}\n컨텍스트: {context}",
        "placeholders": ["{question}", "{context}"],
        "updated_at": "2026-06-28 14:20",
        "updated_by": "관리자",
        "history": [
            {
                "version": 3,
                "updated_at": "2026-06-28 14:20",
                "updated_by": "관리자",
                "summary": "컨텍스트 강조 문구 추가",
                "content": "당신은 노동법 전문 AI입니다. 아래 컨텍스트를 반드시 참고하여 정확하게 답변하세요.\n질문: {question}\n컨텍스트: {context}",
            },
            {
                "version": 2,
                "updated_at": "2026-06-20 09:10",
                "updated_by": "관리자",
                "summary": "초기 버전 개선",
                "content": "당신은 노동법 전문 AI입니다.\n질문: {question}\n컨텍스트: {context}",
            },
            {
                "version": 1,
                "updated_at": "2026-06-10 11:00",
                "updated_by": "관리자",
                "summary": "최초 등록",
                "content": "노동법 관련 질문에 답변하세요.\n질문: {question}",
            },
        ],
    },
}