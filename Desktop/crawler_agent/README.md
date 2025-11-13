# 통합 채용공고 크롤링 시스템

LangGraph 기반 Agent 아키텍처로 구현된 멀티 회사 채용공고 크롤링 시스템입니다.

## 주요 특징

### 플러그인 아키텍처
- **Registry 패턴**: 새로운 회사 크롤러를 간단히 추가 가능
- **BaseCrawler**: 모든 크롤러가 구현해야 하는 공통 인터페이스
- **확장성**: 새 회사를 추가할 때 코어 로직 수정 불필요

### LangGraph Agent 워크플로우
```
fetch_job_list_page
    ↓
extract_job_urls
    ↓
capture_pdfs
    ↓
store_pdfs
```

### 주요 컴포넌트

#### 1. BaseCrawler (추상 클래스)
모든 회사 크롤러가 구현해야 하는 인터페이스:
- `get_company_name()`: 회사명 반환
- `get_job_list_urls()`: 채용 목록 URL 리스트
- `extract_job_urls(html)`: HTML에서 공고 URL 추출
- `get_wait_time()`: PDF 캡처 대기 시간
- `requires_selenium()`: 동적 페이지 여부

#### 2. CrawlerRegistry
플러그인 레지스트리 패턴 구현:
```python
registry = CrawlerRegistry()
registry.register(CoupangCrawler())
registry.register(NaverCrawler())
registry.get_crawler("Coupang")
```

#### 3. PDFCaptureAgent
Selenium을 사용한 PDF 캡처:
- 동적 페이지 지원
- 전체 페이지 스크롤로 lazy-loading 콘텐츠 로드
- Chrome DevTools Protocol 사용

#### 4. StorageAgent
PDF 저장 관리:
- 로컬 파일 시스템 저장
- S3 저장소 통합 (boto3)
- 메타데이터 저장

#### 5. IntegratedCrawlerOrchestrator
LangGraph 기반 통합 오케스트레이터:
- 워크플로우 자동화
- 에러 처리 및 로깅
- 결과 JSON 저장

## 설치

### 1. 의존성 설치
```bash
pip install -r requirements.txt
```

### 2. ChromeDriver 설정
```bash
# webdriver-manager가 자동으로 설치해줍니다
# 또는 수동으로 CHROME_DRIVER_PATH 설정
```

### 3. 환경 변수 설정
```bash
cp .env.example .env
# .env 파일 수정
```

## 사용법

### 기본 사용

```bash
# 특정 회사 크롤링
python main.py --company Coupang

# 모든 회사 크롤링
python main.py --all

# 등록된 크롤러 목록 확인
python main.py --list

# 결과 파일 지정
python main.py --company Naver --output results.json

# PDF 저장 디렉토리 지정
python main.py --all --pdf-dir ./my_pdfs
```

### Python 코드에서 사용

```python
from crawlers import CrawlerRegistry, CoupangCrawler, NaverCrawler
from agents import PDFCaptureAgent, StorageAgent
from orchestrator import IntegratedCrawlerOrchestrator

# 레지스트리 설정
registry = CrawlerRegistry()
registry.register(CoupangCrawler())
registry.register(NaverCrawler())

# 에이전트 초기화
pdf_capture = PDFCaptureAgent(headless=True)
storage = StorageAgent(local_base_path="./data/pdfs")

# 오케스트레이터 생성
orchestrator = IntegratedCrawlerOrchestrator(registry, storage, pdf_capture)

# 크롤링 실행
results = orchestrator.run_company("Coupang")
# 또는
all_results = orchestrator.run_all_companies()

# 결과 저장
orchestrator.save_results_to_json(results, "results.json")
```

## 새로운 회사 크롤러 추가하기

### 1. 새 크롤러 클래스 작성

```python
# crawlers/amazon.py
from typing import List, Dict
from bs4 import BeautifulSoup
from .base_crawler import BaseCrawler

class AmazonCrawler(BaseCrawler):
    def get_company_name(self) -> str:
        return "Amazon"

    def get_job_list_urls(self) -> List[str]:
        return ["https://amazon.jobs/..."]

    def extract_job_urls(self, html: str) -> List[Dict[str, str]]:
        soup = BeautifulSoup(html, "html.parser")
        # HTML 파싱 로직...
        return job_list

    def get_wait_time(self) -> int:
        return 5

    def requires_selenium(self) -> bool:
        return True
```

### 2. 레지스트리에 등록

```python
from crawlers import CrawlerRegistry, AmazonCrawler

registry = CrawlerRegistry()
registry.register(AmazonCrawler())

# 또는 main.py에서 setup_registry()를 수정
```

## 프로젝트 구조

```
crawler_agent/
├── crawlers/
│   ├── __init__.py
│   ├── base_crawler.py      # 추상 기본 클래스
│   ├── registry.py          # Registry 패턴
│   ├── coupang.py           # Coupang 크롤러
│   ├── naver.py             # Naver 크롤러
│   └── kakao.py             # Kakao 크롤러
├── agents/
│   ├── __init__.py
│   ├── pdf_capture.py       # PDF 캡처 Agent
│   └── storage.py           # 저장소 Agent
├── orchestrator.py          # LangGraph 기반 오케스트레이터
├── config.py                # 설정 관리
├── main.py                  # 메인 스크립트
├── requirements.txt         # Python 의존성
├── .env.example             # 환경 변수 예제
└── README.md               # 이 파일
```

## 설정 옵션

### 크롤러 설정
```env
CRAWLER_LOG_LEVEL=INFO
CRAWLER_TIMEOUT=30
CRAWLER_RETRY_COUNT=3
```

### PDF 캡처 설정
```env
PDF_HEADLESS_MODE=true
PDF_WAIT_TIME=5
CHROME_DRIVER_PATH=
```

### 저장소 설정
```env
STORAGE_TYPE=local          # 'local', 's3', 'both'
LOCAL_PDF_PATH=./data/pdfs
AWS_REGION=us-east-1
AWS_ACCESS_KEY_ID=
AWS_SECRET_ACCESS_KEY=
S3_BUCKET_NAME=
```

## 에러 처리

- **크롤링 중 한 공고 실패**: 해당 공고만 스킵하고 계속 진행
- **페이지 로드 타임아웃**: 설정된 재시도 횟수만큼 재시도
- **S3 접근 오류**: 로컬 저장으로 자동 폴백

## 로깅

- `crawler.log`: 모든 작업 로그 저장
- 콘솔에도 실시간 로그 출력
- 로그 레벨은 환경 변수로 조정 가능

## 결과 출력

### JSON 형식
```json
{
  "success": true,
  "company_name": "Coupang",
  "total_jobs": 50,
  "pdfs_captured": 45,
  "pdfs_stored": 45,
  "storage_results": [
    {
      "job_id": "001",
      "job_url": "...",
      "job_title": "Software Engineer",
      "local_path": "./data/pdfs/Coupang/...",
      "s3_key": null,
      "success": true
    }
  ],
  "error_logs": [],
  "timestamp": "2024-01-15T10:30:00"
}
```

## 성능 팁

1. **헤드리스 모드 활성화**: PDF 캡처 속도 증가
2. **대기 시간 조정**: 각 회사별로 최적의 대기 시간 설정
3. **병렬 처리**: 여러 프로세스에서 다른 회사 크롤링 가능
4. **S3 사용**: 대규모 PDF 저장 시 권장

## 라이선스

MIT License

## 지원

문제가 발생하면 이슈를 등록하거나 로그 파일(`crawler.log`)을 확인하세요.
