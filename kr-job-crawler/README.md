# 🚀 대한민국 IT 채용공고 크롤링 시스템

안정적이고 확장 가능한 엔터프라이즈급 채용공고 수집 파이프라인

## ✨ 주요 특징

- **🎯 IT 직군 특화**: 사이트 필터 + 사후 분류기로 IT 공고만 정확히 수집
- **🔄 5가지 패턴 지원**: 정적 토글, A 링크, 함수형, 해시 라우팅, API 직접 호출
- **🤖 자동 프로파일링**: JSON-LD → API → DOM → BFS 순차 탐지
- **📊 완전한 프로비넌스**: 모든 수집 경로/파라미터 추적 가능
- **🔍 Facet Mapper**: 직군 버튼 자동 탐지 및 검증
- **💾 PostgreSQL 저장**: 완전한 스키마 (원문 + 표준화 + 메타데이터)

## 🏗️ 아키텍처

```
┌─────────────┐
│  Playwright │ ──> 네트워크 캡처
└──────┬──────┘
       │
┌──────▼──────────┐
│ Pattern Detector │ ──> 5가지 패턴 자동 감지
└──────┬──────────┘
       │
┌──────▼─────────┐
│   Handlers     │ ──> 패턴별 전문 크롤러
└──────┬─────────┘
       │
┌──────▼─────────┐
│  Extractors    │ ──> HTML/JSON → 스키마 변환
└──────┬─────────┘
       │
┌──────▼─────────┐
│  IT Classifier │ ──> 룰 + 모델 기반 분류
└──────┬─────────┘
       │
┌──────▼─────────┐
│   PostgreSQL   │ ──> 통합 저장
└────────────────┘
```

## 🚀 빠른 시작

### 1. 사전 요구사항

- Python 3.11+
- Docker & Docker Compose
- PostgreSQL 15+

### 2. 설치

```bash
# 저장소 클론
git clone <repository-url>
cd kr-job-crawler

# 가상환경 생성
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# 의존성 설치
pip install -r requirements.txt

# Playwright 브라우저 설치
playwright install chromium
```

### 3. 데이터베이스 설정

```bash
# Docker Compose로 PostgreSQL 실행
docker-compose up -d

# 연결 확인
docker-compose ps

# (옵션) 직접 마이그레이션 실행
psql -U crawler -d job_crawler -f migrations/init_schema.sql
```

### 4. 환경 변수 설정

```bash
cp .env.example .env
# .env 파일 편집 (필요시)
```

### 5. 크롤링 실행

```bash
# 기본 사용법
python -m src.runner.cli crawl \
  --domain careers.example.com \
  --base-url https://careers.example.com/jobs \
  --country KR \
  --target IT \
  --limit 100

# 자동 프로파일링 활성화
python -m src.runner.cli crawl \
  --domain careers.kakao.com \
  --base-url https://careers.kakao.com/jobs \
  --auto-profile \
  --target IT

# 헤드리스 모드 비활성화 (디버깅용)
python -m src.runner.cli crawl \
  --domain careers.example.com \
  --base-url https://careers.example.com/jobs \
  --no-headless
```

## 📋 CLI 명령어

### crawl - 크롤링 실행

```bash
python -m src.runner.cli crawl [OPTIONS]

Options:
  --domain TEXT          도메인 (필수)
  --base-url TEXT        시작 URL (필수)
  --country TEXT         국가 필터 [기본: KR]
  --target TEXT          대상 직군 [기본: IT]
  --limit INTEGER        수집 제한 개수
  --auto-profile         자동 프로파일링 활성화
  --headless/--headed    헤드리스 모드 [기본: headless]
```

### list-profiles - 프로파일 목록

```bash
python -m src.runner.cli list-profiles
```

### stats - 수집 통계

```bash
# 전체 통계
python -m src.runner.cli stats

# 도메인별 통계
python -m src.runner.cli stats --domain careers.kakao.com
```

## 📊 데이터 스키마

### job_postings 테이블

| 카테고리 | 필드 | 설명 |
|---------|------|------|
| **식별/출처** | id, domain, source_url, canonical_job_id | 고유 식별자 |
| **원문** | company_name_raw, job_title_raw, detail_html, detail_json | 원본 데이터 |
| **표준화** | title, employment_type, location_country, post_date | 정규화된 데이터 |
| **IT 분류** | it_label, label_source, label_confidence, label_evidence | 분류 결과 |
| **프로비넌스** | pattern_detected, api_endpoint, selectors_used, profile_version | 수집 메타데이터 |

## 🔧 설정 파일

### 사이트 프로파일 (YAML)

```yaml
# src/profiles/sites/careers.example.com.yaml
domain: careers.example.com
name: Example Careers
version: "1.0.0"
pattern: static_toggle

it_filter:
  selector: "button:has-text('IT')"
  route: null
  api_params: null

selectors:
  job_list: "article.job-posting"
  title: "h2.title"
  company: ".company-name"

api_config: null

extraction_rules:
  date_format: "%Y-%m-%d"
  
last_verified: "2025-11-07T10:00:00"
notes: "정적 토글 버튼으로 IT 필터링"
```

## 🧪 테스트

```bash
# 기본 테스트 실행
pytest

# 커버리지 포함
pytest --cov=src

# 특정 모듈 테스트
pytest tests/test_basic.py -v
```

## 📁 프로젝트 구조

```
kr-job-crawler/
├── src/
│   ├── detector/          # 패턴 감지
│   ├── handlers/          # 5가지 핸들러
│   ├── facets/            # Facet Mapper
│   ├── autoprofiler/      # 자동 프로파일링
│   ├── extractors/        # HTML/JSON 추출
│   ├── classifier/        # IT 분류기
│   ├── profiles/          # 프로파일 관리
│   ├── storage/           # DB 저장
│   ├── utils/             # 공통 유틸
│   └── runner/            # CLI
├── migrations/            # DDL
├── tests/                 # 테스트
└── docker-compose.yml     # PostgreSQL
```

## 🔍 디버깅

### 로그 확인

```bash
# 로그 레벨 변경 (.env)
LOG_LEVEL=DEBUG

# 로그 파일 확인
tail -f logs/crawler.log
```

### 네트워크 캡처 확인

```python
with PlaywrightLauncher(headless=False) as launcher:
    page = launcher.new_page(capture_network=True)
    page.goto(url)
    
    # 캡처된 API 호출 확인
    api_calls = launcher.get_api_calls()
    for call in api_calls:
        print(f"{call.method} {call.url}")
```

### DB 직접 확인

```bash
# PostgreSQL 접속
docker exec -it job_crawler_db psql -U crawler -d job_crawler

# 쿼리 예시
SELECT domain, COUNT(*) as total, 
       COUNT(*) FILTER (WHERE it_label = true) as it_count
FROM job_postings 
GROUP BY domain;
```

## 🛠️ 확장 가이드

### 새 핸들러 추가

```python
# src/handlers/my_handler.py
from src.handlers.base import BaseHandler

class MyHandler(BaseHandler):
    def crawl(self, target_category, limit):
        # 구현
        pass
    
    def apply_it_filter(self, category):
        # 구현
        pass
```

### 커스텀 분류기 추가

```python
# src/classifier/custom_classifier.py
class CustomClassifier:
    def classify(self, posting):
        # ML 모델 또는 룰 추가
        return (is_it, confidence, evidence)
```

## 📝 라이선스

MIT License

## 🤝 기여

이슈와 PR을 환영합니다!

## 📞 지원

문제가 있으시면 GitHub Issues에 등록해주세요.
