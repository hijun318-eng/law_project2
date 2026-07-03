# Django MVT 설계를 위한 화면 설계

> 각 화면의 URL, View, Template, Model을 함께 정의하여 MVT 구조 설계 및 역할 분담이 가능하도록 작성한다.

---

# 1. Home App

## 1.1 홈

| 항목 | 내용 |
|------|------|
| URL | `/` |
| View | `home` |
| Template | `home.html` |
| Model | - |

### 기능
- 서비스 소개
- 주요 기능 안내
- 최신 노동 뉴스 미리보기
- AI 상담 시작
- 로그인 / 회원가입 이동

---

# 2. Accounts App

## 2.1 로그인

| 항목 | 내용 |
|------|------|
| URL | `/accounts/login/` |
| View | `login_view` |
| Template | `login.html` |
| Model | `User` |

### 기능
- 로그인
- 회원가입 이동
- 아이디 찾기
- 비밀번호 재설정

---

## 2.2 회원가입

| 항목 | 내용 |
|------|------|
| URL | `/accounts/signup/` |
| View | `signup` |
| Template | `signup.html` |
| Model | `User` |

### 기능
- 회원가입
- 중복 확인
- 회원 정보 저장

---

## 2.3 마이페이지

| 항목 | 내용 |
|------|------|
| URL | `/accounts/mypage/` |
| View | `mypage` |
| Template | `mypage.html` |
| Model | `User` |

### 기능
- 개인정보 조회
- 개인정보 수정
- 비밀번호 변경
- 상담 내역 조회
- 계산기 이용 기록
- 뉴스 스크랩
- 회원 탈퇴

---

# 3. Chat App

## 3.1 AI 상담

| 항목 | 내용 |
|------|------|
| URL | `/chat/` |
| View | `chat` |
| Template | `chat.html` |
| Model | `ChatHistory` |

### 기능
- 질문 입력
- AI 답변 출력
- 추천 질문 제공
- 상담 저장

---

## 3.2 상담 결과

| 항목 | 내용 |
|------|------|
| URL | `/chat/result/<id>/` |
| View | `chat_result` |
| Template | `result.html` |
| Model | `ChatHistory` |

### 기능
- 답변 조회
- 법령 및 판례 근거 확인
- 대응 절차 안내

---

## 3.3 상담 내역

| 항목 | 내용 |
|------|------|
| URL | `/chat/history/` |
| View | `history` |
| Template | `history.html` |
| Model | `ChatHistory` |

### 기능
- 상담 목록 조회
- 상담 검색
- 상담 삭제

---

# 4. Calculator App

## 4.1 수당 계산기

| 항목 | 내용 |
|------|------|
| URL | `/calculator/` |
| View | `calculator` |
| Template | `calculator.html` |
| Model | `CalculatorHistory` |

### 기능
- 퇴직금 계산
- 연차수당 계산
- 주휴수당 계산
- 연장·야간·휴일수당 계산
- 최저임금 계산

---

## 4.2 계산 결과

| 항목 | 내용 |
|------|------|
| URL | `/calculator/result/` |
| View | `result` |
| Template | `result.html` |
| Model | `CalculatorHistory` |

### 기능
- 계산 결과 출력
- 계산 내역 저장
- 계산 기록 조회

---

# 5. News App

## 5.1 최신 뉴스

| 항목 | 내용 |
|------|------|
| URL | `/news/` |
| View | `news_list` |
| Template | `news.html` |
| Model | `NewsBookmark` |

### 기능
- 노동 뉴스 조회
- 키워드 검색
- AI 요약 제공

---

## 5.2 뉴스 상세

| 항목 | 내용 |
|------|------|
| URL | `/news/<id>/` |
| View | `news_detail` |
| Template | `detail.html` |
| Model | `NewsBookmark` |

### 기능
- 뉴스 본문 조회
- 관련 기사 보기
- 스크랩

---

# 6. Admin Dashboard App

## 6.1 관리자 대시보드

| 항목 | 내용 |
|------|------|
| URL | `/dashboard/` |
| View | `dashboard` |
| Template | `dashboard.html` |
| Model | `User`, `ChatHistory`, `Feedback` |

### 기능
- 사용자 수
- 상담 건수
- 피드백 현황
- 시스템 통계

---

## 6.2 사용자 관리

| 항목 | 내용 |
|------|------|
| URL | `/dashboard/users/` |
| View | `user_list` |
| Template | `users.html` |
| Model | `User` |

### 기능
- 회원 조회
- 회원 검색
- 회원 정보 수정
- 회원 권한 변경
- 계정 비활성화

---

## 6.3 피드백 관리

| 항목 | 내용 |
|------|------|
| URL | `/dashboard/feedback/` |
| View | `feedback_list` |
| Template | `feedback.html` |
| Model | `Feedback` |

### 기능
- 피드백 조회
- 피드백 검색
- 처리 상태 변경
- 관리자 답변 작성

---

# Django App 구성

```
project/
│
├── home/
│
├── accounts/
│
├── chat/
│
├── calculator/
│
├── news/
│
├── dashboard/
│
└── config/
```

# App별 역할

| App | 담당 기능 |
|------|-----------|
| **home** | 메인 화면 및 서비스 소개 |
| **accounts** | 로그인, 회원가입, 마이페이지 |
| **chat** | AI 상담, 상담 기록 |
| **calculator** | 노동 수당 계산기 |
| **news** | 최신 노동 뉴스 |
| **dashboard** | 관리자 기능(통계, 사용자, 피드백) |