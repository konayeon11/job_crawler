# 🤖 Smart Job Crawler - OpenAI 기반 지능형 채용공고 크롤러

## 📋 개요

**Smart Crawler**는 OpenAI를 활용하여 다양한 채용공고 웹사이트의 구조를 자동으로 분석하고, 각 페이지에 맞게 데이터를 추출하는 지능형 크롤러입니다.

```
URL 입력 → 페이지 다운로드 → OpenAI 분석 → 데이터 추출 → SQLite 저장
```

---

## ✨ 주요 기능

### 1. **자동 페이지 구조 분석**
- OpenAI (GPT-4)가 HTML을 분석하여 데이터 위치 자동 식별
- CSS 선택자 또는 API 필드명 동적 탐지
- 복잡한 웹사이트도 자동으로 처리

### 2. **유연한 데이터 추출**
- **API 기반 추출**: REST API가 있는 경우 자동으로 API 호출
- **HTML 기반 추출**: CSS 선택자를 사용한 정적 HTML 파싱
- **자동 선택**: 페이지 구조에 따라 최적의 방법 선택

### 3. **완벽한 데이터 저장**
저장되는 필드:
- `title` - 직무명
- `company` - 회사명
- `location` - 근무 위치
- `introduction` - 직무 소개
- `work_content` - 직무 설명
- `qualification` - 자격 요건
- `work_condition` - 근무 조건
- `recruitment_process` - 채용 절차
- `skills` - 기술 스택 (JSON 배열)

### 4. **신뢰성 있는 처리**
- 중복 방지 (job_id 기반 유니크 제약)
- 에러 핸들링 및 재시도 로직
- 상세한 로깅으로 진행 상황 파악

---

## 🚀 사용 방법

### 기본 사용법

```bash
python smart_crawler.py "<URL>"
```

### 예시

```bash
# Kakao careers
python smart_crawler.py "https://careers.kakao.com/jobs/P-14207"

# 다른 채용공고 사이트
python smart_crawler.py "https://example.com/job/12345"
```

### 프로그래밍으로 사용

```python
from smart_crawler import crawl_job_url

# 기본 사용
crawl_job_url("https://careers.kakao.com/jobs/P-14207")

# 커스텀 DB 경로 지정
crawl_job_url(
    "https://careers.kakao.com/jobs/P-14207",
    db_path="/path/to/jobs.db"
)
```

---

## 🔧 설정

### 필수 환경 변수

`.env` 파일에 OpenAI API 키 설정:

```env
OPENAI_API_KEY=sk-xxxxxxxxxxxxx
```

### 데이터베이스

- **경로**: `jobs.db` (SQLite)
- **자동 생성**: 처음 실행 시 자동으로 생성됨
- **위치**: 스크립트와 같은 디렉토리

---

## 📊 데이터 조회

### Python에서 조회

```python
import sqlite3
import json

conn = sqlite3.connect('jobs.db')
cursor = conn.cursor()

# 모든 공고 조회
cursor.execute('SELECT title, company FROM job_postings')
for row in cursor.fetchall():
    print(f"{row[0]} - {row[1]}")

# 특정 필드 조회 (JSON 파싱)
cursor.execute('SELECT title, introduction FROM job_postings')
for title, intro in cursor.fetchall():
    print(f"Title: {title}")
    print(f"Intro: {intro}")

conn.close()
```

### SQL 쿼리

```sql
-- 총 공고 수
SELECT COUNT(*) FROM job_postings;

-- 회사별 공고 수
SELECT company, COUNT(*)
FROM job_postings
GROUP BY company;

-- 특정 회사의 모든 공고
SELECT title, location
FROM job_postings
WHERE company = '카카오';

-- 스킬을 포함하는 공고
SELECT title, skills
FROM job_postings
WHERE skills IS NOT NULL AND skills != '[]';
```

---

## 🎯 작동 원리

### 1. 페이지 다운로드
```
📥 페이지 다운로드 중...
```
- httpx를 사용하여 웹페이지 HTML 다운로드
- User-Agent 설정으로 봇 차단 우회

### 2. 구조 분석
```
🤖 OpenAI 분석 중...
✅ 페이지 구조 분석 완료
```
- HTML의 처음 3000자를 OpenAI에 전송
- GPT-4가 데이터 위치를 JSON 형식으로 반환
- Kakao careers는 특수 처리로 API 자동 사용

### 3. 데이터 추출
```
🔄 API에서 데이터 추출 중...
📡 API 호출: https://careers.kakao.com/public/api/job-list
✅ 15개 공고 조회 완료
```
또는:
```
🔄 HTML에서 데이터 추출 중...
```

### 4. 데이터 저장
```
✓ [2026 신입공채] Tech - Tech 공통
✓ Data Engineer (경력)
...
✅ 15개 공고 저장 완료
```

---

## 📌 특수 처리

### Kakao Careers
- Kakao 채용 사이트는 React SPA이므로 특수하게 처리됨
- 자동으로 공식 API(`https://careers.kakao.com/public/api/job-list`) 사용
- CSS 선택자 대신 API 필드명 매핑 사용

### 다른 웹사이트
- OpenAI가 HTML을 분석하여 CSS 선택자 자동 탐지
- HTML 파싱 방식으로 데이터 추출
- API가 있다면 자동으로 감지 및 사용

---

## ⚠️ 제약사항 및 주의사항

### OpenAI API 비용
- 각 페이지 분석마다 ~0.01-0.05 USD 소비
- 프로덕션 환경에서는 비용 모니터링 권장

### 성능
- 동시에 여러 URL 처리 불가 (순차 처리)
- 대량 크롤링 시 API 비용 증가
- Kakao 공고는 최대 15개까지만 조회 (API 기본값)

### 데이터 정합성
- 일부 필드가 없을 수 있음 (NULL 값)
- 스킬 정보는 JSON 배열 형식으로 저장
- 중복 제거 기능: job_id가 같으면 갱신

---

## 🔍 예제: 전체 워크플로우

### Step 1: Kakao careers 크롤링

```bash
python smart_crawler.py "https://careers.kakao.com/jobs/P-14207"
```

**출력:**
```
====================================================================================================
🚀 스마트 크롤러 시작: https://careers.kakao.com/jobs/P-14207
====================================================================================================

📥 페이지 다운로드 중...

🔍 Kakao careers 페이지 감지 - Kakao API 사용

🔄 API에서 데이터 추출 중...
   📡 API 호출: https://careers.kakao.com/public/api/job-list
   ✅ 15개 공고 조회 완료 (jobList 필드)
   ✓ [2026 신입공채] Tech - Tech 공통
   ✓ Data Engineer (경력)
   ...
✅ 15개 공고 저장 완료
💾 DB: /path/to/jobs.db
```

### Step 2: 데이터 확인

```python
import sqlite3

conn = sqlite3.connect('jobs.db')
cursor = conn.cursor()

cursor.execute('SELECT COUNT(*) FROM job_postings')
total = cursor.fetchone()[0]
print(f"저장된 공고: {total}개")

cursor.execute('SELECT title, company FROM job_postings LIMIT 5')
for title, company in cursor.fetchall():
    print(f"  - {title} ({company})")

conn.close()
```

**출력:**
```
저장된 공고: 15개
  - [2026 신입공채] Tech - Tech 공통 (카카오)
  - Data Engineer (경력) (카카오)
  - 추천 시스템 연구/개발 (경력) (카카오)
  ...
```

---

## 🛠️ 문제 해결

### Q: "OpenAI API 오류" 발생
**A:**
- `.env` 파일에 유효한 OPENAI_API_KEY 확인
- API 키가 활성화되었는지 확인
- 네트워크 연결 확인

### Q: "제목을 찾을 수 없습니다" 에러
**A:**
- 해당 웹사이트가 JavaScript 기반인지 확인 (SSR이 아닌 경우 HTML에 콘텐츠 없음)
- 특수 처리 필요 시 smart_crawler.py의 `crawl_job_url` 함수에 추가

### Q: 같은 URL을 여러 번 크롤링하면?
**A:**
- job_id가 같으면 자동으로 갱신됨 (UNIQUE 제약)
- 중복 저장 걱정 없음

### Q: 데이터베이스 초기화
```python
import os
os.remove('jobs.db')
# 다시 실행하면 자동으로 새 DB 생성
```

---

## 📈 향후 개선 사항

- [ ] 배치 크롤링 (여러 URL 동시 처리)
- [ ] 데이터 정제 및 표준화 (직무명, 회사명 등)
- [ ] 유사도 측정 (공고 간 유사성)
- [ ] 트렌드 분석 (시간별 공고 변화)
- [ ] 다국어 지원
- [ ] 프록시 지원

---

## 📞 기술 정보

### 사용 라이브러리
- `openai` - OpenAI API
- `httpx` - HTTP 클라이언트
- `beautifulsoup4` - HTML 파싱
- `sqlite3` - 로컬 데이터베이스
- `python-dotenv` - 환경 변수 관리

### 데이터베이스 스키마

```sql
CREATE TABLE job_postings (
    id TEXT PRIMARY KEY,
    domain VARCHAR(255) NOT NULL,
    job_id VARCHAR(500) NOT NULL UNIQUE,
    title VARCHAR(1000) NOT NULL,
    company VARCHAR(500),
    location VARCHAR(200),
    source_url TEXT,
    introduction TEXT,
    work_content TEXT,
    qualification TEXT,
    work_condition TEXT,
    recruitment_process TEXT,
    skills TEXT,
    required_skills TEXT,
    recruitment_count INT,
    employment_type VARCHAR(100),
    job_category VARCHAR(100),
    raw_json TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

---

## 📝 라이선스

자유롭게 사용, 수정, 배포 가능합니다.

---

**마지막 업데이트**: 2025-11-10
**버전**: 1.0.0
