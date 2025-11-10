# SQLite 로컬 데이터베이스 설정 및 사용 가이드

## 📋 개요

PostgreSQL 없이 **SQLite 로컬 데이터베이스**를 사용하여 정제된 채용공고 데이터를 저장하고 조회합니다.

---

## 1️⃣ 데이터베이스 설정

### 1.1 초기 설정

```bash
cd C:\Users\SKAX\Desktop\kr-job-crawler\kr-job-crawler
python setup_local_db.py
```

**실행 결과:**
- ✅ SQLite 테이블 생성 (job_postings)
- ✅ 샘플 데이터 2개 삽입
- ✅ 인덱스 생성
- ✅ 초기 조회 테스트

### 1.2 데이터베이스 파일

```
경로: C:\Users\SKAX\Desktop\kr-job-crawler\kr-job-crawler\job_crawler.db
크기: ~100KB (샘플 데이터 기준)
타입: SQLite 3
```

---

## 2️⃣ 데이터 저장 구조

### 2.1 테이블 구조 (job_postings)

| 필드명 | 타입 | 설명 |
|--------|------|------|
| **id** | TEXT | 고유 ID (UUID) |
| **domain** | VARCHAR(255) | 채용 사이트 도메인 |
| **source_url** | TEXT | 공고 URL |
| **canonical_job_id** | VARCHAR(500) | 공고 고유 ID (UNIQUE) |
| **company_name_raw** | VARCHAR(500) | 회사명 |
| **job_title_raw** | VARCHAR(1000) | 직무명 |
| **title** | VARCHAR(1000) | 표준화 직무명 |
| **employment_type** | VARCHAR(100) | 고용형태 |
| **location_city** | VARCHAR(200) | 도시 |
| **is_active** | BOOLEAN | 활성 여부 |
| **skills** | TEXT (JSON) | 기술 스택 배열 |
| **it_label** | BOOLEAN | IT 분류 여부 |
| **label_confidence** | REAL | 분류 신뢰도 |
| **detail_json** | TEXT (JSON) | ⭐️ **정제된 모든 상세정보** |
| **api_endpoint** | TEXT | API 엔드포인트 |
| **api_params** | TEXT (JSON) | API 파라미터 |
| **created_at** | TIMESTAMP | 생성 시간 |
| **updated_at** | TIMESTAMP | 수정 시간 |

### 2.2 detail_json 구조

```json
{
  "introduction": "직무 소개",
  "work_content_desc": "직무 설명",
  "qualification": "자격 요건",
  "work_type_desc": "근무 조건",
  "job_offer_process": "채용 절차",
  "skills_cleaned": ["Python", "Django"],
  "recruit_count": 1,
  "job_part_name": "테크",
  "job_type_name": "신입"
}
```

---

## 3️⃣ 데이터 조회

### 3.1 모든 공고 조회

```bash
python query_local_db.py
```

**출력 예시:**
```
총 공고 수: 2개
IT 공고 수: 2개 (100.0%)
활성 공고 수: 1개

[1] [2026 신입공채] Tech - Tech 공통
    회사: 카카오
    위치: 판교
    활성: ❌
    IT: ✅ (신뢰도: 0.95)
```

### 3.2 Python에서 프로그래밍

#### 기본 연결

```python
import sqlite3
import json

DB_PATH = r'C:\Users\SKAX\Desktop\kr-job-crawler\kr-job-crawler\job_crawler.db'
conn = sqlite3.connect(DB_PATH)
conn.row_factory = sqlite3.Row
cursor = conn.cursor()

# 쿼리 실행
cursor.execute('SELECT * FROM job_postings')
rows = cursor.fetchall()

# 결과 처리
for row in rows:
    print(f"공고: {row['job_title_raw']}")
    detail = json.loads(row['detail_json'])
    print(f"소개: {detail['introduction']}")

conn.close()
```

#### IT 공고만 조회

```python
cursor.execute('SELECT * FROM job_postings WHERE it_label = 1')

for row in cursor.fetchall():
    detail = json.loads(row['detail_json'])
    print(f"공고: {row['job_title_raw']}")
    print(f"신뢰도: {row['label_confidence']:.2f}")
    print(f"기술: {', '.join(json.loads(row['skills']))}")
```

#### 정제된 내용 조회

```python
cursor.execute('SELECT job_title_raw, detail_json FROM job_postings')

for row in cursor.fetchall():
    detail = json.loads(row['detail_json'])
    print(f"\n공고: {row['job_title_raw']}")
    print(f"소개: {detail['introduction']}")
    print(f"직무: {detail['work_content_desc']}")
    print(f"자격: {detail['qualification']}")
    print(f"근무: {detail['work_type_desc']}")
```

#### 키워드 검색

```python
keyword = "데이터"
cursor.execute('''
    SELECT job_title_raw, company_name_raw, detail_json
    FROM job_postings
    WHERE detail_json LIKE ?
       OR job_title_raw LIKE ?
''', (f'%{keyword}%', f'%{keyword}%'))

for row in cursor.fetchall():
    print(f"공고: {row['job_title_raw']}")
```

### 3.3 SQL 쿼리

#### 기본 조회

```sql
SELECT
    job_title_raw,
    company_name_raw,
    location_city,
    it_label,
    label_confidence
FROM job_postings
ORDER BY created_at DESC
LIMIT 10;
```

#### detail_json에서 필드 추출

```sql
SELECT
    job_title_raw,
    json_extract(detail_json, '$.introduction') AS 소개,
    json_extract(detail_json, '$.work_content_desc') AS 직무설명,
    json_extract(detail_json, '$.qualification') AS 자격요건
FROM job_postings;
```

#### IT 공고 + 기술 필터

```sql
SELECT
    job_title_raw,
    skills,
    label_confidence
FROM job_postings
WHERE it_label = 1
  AND json_array_length(json_extract(skills, '$')) > 0
ORDER BY label_confidence DESC;
```

#### JSON 배열 필터

```sql
SELECT
    job_title_raw,
    json_extract(detail_json, '$.skills_cleaned') AS skills
FROM job_postings
WHERE json_type(json_extract(detail_json, '$.skills_cleaned')) = 'array'
  AND json_array_length(json_extract(detail_json, '$.skills_cleaned')) > 0;
```

### 3.4 SQLite 명령줄

```bash
sqlite3 C:\Users\SKAX\Desktop\kr-job-crawler\kr-job-crawler\job_crawler.db

# 테이블 목록
.tables

# 열 정보
.schema job_postings

# 열 단위 출력
.mode column
.headers on
SELECT job_title_raw, location_city, it_label FROM job_postings;

# JSON 데이터 조회
SELECT job_title_raw, json_extract(detail_json, '$.introduction') FROM job_postings;

# 종료
.exit
```

---

## 4️⃣ 데이터 내보내기

### 4.1 JSON 내보내기

```bash
python query_local_db.py
```

**생성 파일:** `exported_jobs_sqlite.json`

```json
{
  "metadata": {
    "total_count": 2,
    "it_count": 2,
    "export_format": "SQLite"
  },
  "postings": [
    {
      "title": "[2026 신입공채] Tech - Tech 공통",
      "company": "카카오",
      "detail": {
        "introduction": "...",
        "work_content_desc": "...",
        "qualification": "..."
      },
      "skills": [],
      "it_label": true,
      "label_confidence": 0.95
    }
  ]
}
```

### 4.2 CSV 내보내기

**생성 파일:** `exported_jobs_sqlite.csv`

| 공고ID | 제목 | 회사 | 도시 | URL | 고용형태 | 소개 | IT여부 | 신뢰도 | 기술스택 |
|--------|------|------|------|-----|---------|------|--------|--------|---------|
| 14207 | [2026 신입공채] Tech - Tech 공통 | 카카오 | 판교 | https://... | 정규직 | Server... | IT | 0.95 | N/A |

---

## 5️⃣ 크롤러와 DB 통합

### 5.1 크롤러에서 데이터 저장

```python
# crawler_with_db_insertion.py 수정 부분
import sqlite3
import json
import uuid

def save_to_sqlite(postings):
    """SQLite DB에 저장"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    for posting in postings:
        try:
            cursor.execute('''
                INSERT INTO job_postings (
                    id, domain, source_url, canonical_job_id, company_name_raw,
                    job_title_raw, title, employment_type, location_city,
                    is_active, skills, it_label, label_confidence,
                    detail_json, api_endpoint, api_params
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                str(uuid.uuid4()),
                posting.domain,
                posting.source_url,
                posting.canonical_job_id,
                posting.company_name_raw,
                posting.job_title_raw,
                posting.title,
                posting.employment_type,
                posting.location_city,
                posting.is_active,
                json.dumps(posting.skills or []),
                posting.it_label,
                posting.label_confidence,
                json.dumps(posting.detail_json or {}),
                posting.api_endpoint,
                json.dumps(posting.api_params or {})
            ))
        except Exception as e:
            print(f"❌ 저장 오류: {str(e)}")

    conn.commit()
    conn.close()
    print(f"✅ {len(postings)}개 공고 저장 완료")
```

---

## 6️⃣ 주요 기능

| 기능 | 설명 | 사용 방법 |
|------|------|---------|
| **초기 설정** | SQLite DB 생성 및 샘플 데이터 삽입 | `python setup_local_db.py` |
| **데이터 조회** | 모든 공고 목록 및 상세 정보 조회 | `python query_local_db.py` |
| **JSON 내보내기** | 모든 데이터를 JSON으로 변환 | 자동 생성: `exported_jobs_sqlite.json` |
| **CSV 내보내기** | 공고 목록을 CSV로 변환 (Excel 호환) | 자동 생성: `exported_jobs_sqlite.csv` |
| **키워드 검색** | 공고명, 회사명, 상세정보에서 검색 | Python API 사용 |
| **SQL 쿼리** | 임의의 SQL 쿼리 실행 | `sqlite3 job_crawler.db` |

---

## 7️⃣ 예시: 전체 워크플로우

### Step 1: 데이터베이스 초기화
```bash
python setup_local_db.py
```

### Step 2: 크롤러 실행 (API → 정제 → DB 저장)
```bash
python crawler_with_db_insertion.py
```

### Step 3: 데이터 조회
```bash
python query_local_db.py
```

### Step 4: 데이터 분석
```python
import sqlite3
import json

conn = sqlite3.connect('job_crawler.db')
cursor = conn.cursor()

# IT 공고 중 Python 기술을 요구하는 공고 찾기
cursor.execute('''
    SELECT job_title_raw, company_name_raw, skills
    FROM job_postings
    WHERE it_label = 1
    AND skills LIKE '%Python%'
''')

for row in cursor.fetchall():
    print(f"공고: {row[0]}")
    print(f"회사: {row[1]}")
    print(f"기술: {row[2]}")

conn.close()
```

---

## 8️⃣ 성능 및 제약사항

| 항목 | 설명 |
|------|------|
| **최대 데이터 크기** | ~2GB (SQLite 한계) |
| **동시 쓰기** | 1개 연결만 가능 |
| **최대 연결 수** | 제한 없음 (읽기) |
| **인덱스** | 5개 (domain, is_active, it_label, api_endpoint, source_url) |
| **추천 행 수** | 10,000개 이하 |
| **복잡한 JOIN** | 권장하지 않음 |

---

## 9️⃣ 문제 해결

### Q: 데이터베이스가 손상됨
```bash
# DB 재구성
python setup_local_db.py
```

### Q: 데이터가 저장되지 않음
```python
# 트랜잭션 커밋 확인
conn.commit()
conn.close()
```

### Q: JSON 조회가 느림
```sql
-- 인덱스 추가
CREATE INDEX idx_detail_json ON job_postings(detail_json);
```

### Q: 특정 데이터 삭제
```python
conn.execute("DELETE FROM job_postings WHERE canonical_job_id = ?", ('14207',))
conn.commit()
```

---

## 🔟 요약

✅ **PostgreSQL 없이 로컬에서 작동**
✅ **간단한 초기 설정** (1줄 명령)
✅ **정제된 모든 데이터 저장** (detail_json)
✅ **Python, SQL, CLI로 유연하게 조회**
✅ **JSON/CSV로 간편하게 내보내기**
✅ **확장 가능** (추후 PostgreSQL 마이그레이션 용이)

이제 **PostgreSQL 없이도 완전히 작동하는 채용공고 크롤러 시스템**을 갖추셨습니다! 🚀

