# ⚡ 빠른 시작 가이드

## 5분 안에 시작하기

### 1️⃣ 설치 (1분)

```bash
# 디렉토리 이동
cd kr-job-crawler

# 라이브러리 설치
pip install -r requirements.txt
```

### 2️⃣ 설정 (1분)

`.env` 파일 생성:
```
OPENAI_API_KEY=sk-xxxxxxxxxxxxx
```

### 3️⃣ 실행 (3분)

```bash
# 채용공고 크롤링
python smart_crawler.py "https://careers.kakao.com/jobs/P-14207"

# 저장된 데이터 확인
python query_jobs.py
```

**완료! 🎉**

---

## 자주 사용하는 명령어

### 크롤링
```bash
# Kakao careers
python smart_crawler.py "https://careers.kakao.com/jobs/P-14207"

# 다른 채용 사이트
python smart_crawler.py "https://example.com/job/12345"
```

### 데이터 조회
```bash
# 모든 공고
python query_jobs.py

# 특정 회사
python query_jobs.py --company 카카오

# 키워드 검색
python query_jobs.py --keyword 파이썬
```

### 데이터베이스 초기화
```bash
# Windows
del jobs.db

# Mac/Linux
rm jobs.db
```

---

## 주요 파일

| 파일명 | 용도 |
|--------|------|
| `smart_crawler.py` | 🚀 메인 크롤러 |
| `query_jobs.py` | 📊 데이터 조회 |
| `jobs.db` | 💾 데이터베이스 |
| `.env` | 🔑 API 키 설정 |

---

## 다음 단계

- ✅ 완료: 공고 크롤링
- ⏭️ 예정: 유사도 측정 (`similarity_analysis.py`)
- ⏭️ 예정: 트렌드 분석 (`trend_analysis.py`)

더 자세한 정보는 `SMART_CRAWLER_README.md` 참고
