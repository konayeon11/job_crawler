# 통합 채용공고 크롤링 시스템

비동기 Playwright 기반 멀티 회사 채용공고 크롤링 시스템입니다.
완전 비동기 처리, CloudFlare 우회, PDF/HTML/JSON 메타데이터 저장을 지원합니다.

## 주요 특징

### 비동기 아키텍처
- **AsyncPlaywrightOrchestrator**: 완전 비동기 처리로 높은 동시성 지원
- **Playwright 기반**: 동적 페이지 렌더링 및 JavaScript 실행 가능
- **CloudFlare 우회**: playwright-stealth + cloudscraper로 보안 우회

### 플러그인 아키텍처
- **Registry 패턴**: 새로운 회사 크롤러를 간단히 추가 가능
- **BaseCrawler**: 모든 크롤러가 구현해야 하는 공통 인터페이스
- **확장성**: 새 회사를 추가할 때 코어 로직 수정 불필요

### AsyncPlaywrightOrchestrator 워크플로우
```
1. 채용 목록 페이지 오픈 (Playwright)
   ↓
2. 개별 공고 URL 추출 (크롤러별로 구현)
   ↓
3. 각 공고 상세 정보 파싱 (병렬 처리, Semaphore로 동시성 제어)
   ↓
4. HTML 원본 저장
   ↓
5. JSON 메타데이터 저장 (벡터 임베딩 지원)
   ↓
6. PDF 캡처 (병렬 처리)
```

### 주요 컴포넌트

#### 1. BaseCrawler (추상 클래스)
모든 회사 크롤러가 구현해야 하는 인터페이스:
- `get_company_name()`: 회사명 반환
- `get_job_list_urls()`: 채용 목록 URL 리스트
- `extract_job_urls(page)`: Playwright page에서 공고 URL 추출
- `parse_job_detail(page, url, idx)`: 상세 페이지 파싱
- `get_wait_time()`: 페이지 로드 대기 시간
- `get_max_concurrent_jobs()`: 동시 처리 공고 수
- `requires_playwright()`: Playwright 사용 여부

#### 2. CrawlerRegistry
플러그인 레지스트리 패턴 구현:
```python
registry = CrawlerRegistry()
registry.register(CoupangCrawler())
registry.register(WoowahanCrawler())
registry.get_crawler("Coupang")
```

#### 3. AsyncPlaywrightOrchestrator
완전 비동기 크롤링 오케스트레이터:
- Playwright 기반 동적 페이지 처리
- Semaphore를 이용한 동시성 제어
- 각 크롤러별로 최적화된 동시 작업 수 설정
- HTML + JSON 메타데이터 + PDF 동시 저장
- playwright-stealth를 통한 자동 감지 우회

**주요 메서드:**
- `crawl_company(company_name, max_jobs)`: 특정 회사 크롤링
- `crawl_all_companies(max_jobs)`: 모든 회사 병렬 크롤링

#### 4. PlaywrightCaptureAgent
Playwright 기반 PDF 캡처:
- Chrome DevTools Protocol (CDP) 사용
- 완전 렌더링 지원
- 동적 콘텐츠 포함 캡처

#### 5. StorageAgent
저장소 관리:
- HTML 파일 저장
- JSON 메타데이터 저장
- PDF 파일 저장
- 한국어 파일명 지원

#### 6. CloudFlare 우회 전략
**하이브리드 접근:**
- **목록 페이지**: cloudscraper로 JavaScript 챌린지 우회
- **상세 페이지**: playwright-stealth로 자동 감지 우회
- **User-Agent**: 실제 Chrome 브라우저와 동일하게 설정
- **Stealth 적용**: 모든 Playwright page 인스턴스에 적용

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

### 기본 사용 (AsyncPlaywrightOrchestrator)

```python
import asyncio
from crawlers import CrawlerRegistry, CoupangCrawler, WoowahanCrawler
from async_orchestrator import AsyncPlaywrightOrchestrator
from agents import StorageAgent, PlaywrightCaptureAgent

async def crawl():
    # 레지스트리 설정
    registry = CrawlerRegistry()
    registry.register(CoupangCrawler())
    registry.register(WoowahanCrawler())

    # 에이전트 초기화
    storage_agent = StorageAgent()
    playwright_capture_agent = PlaywrightCaptureAgent(headless=True)

    # 오케스트레이터 생성
    orchestrator = AsyncPlaywrightOrchestrator(
        registry=registry,
        storage_agent=storage_agent,
        playwright_capture_agent=playwright_capture_agent,
        headless=True,
        use_vector_embedding=False,
    )

    # 특정 회사 크롤링 (최대 5개 공고)
    result = await orchestrator.crawl_company("Coupang", max_jobs=5)
    print(f"Total jobs: {result['total_jobs']}")
    print(f"Saved: {result['successful_saves']}")

    # 모든 회사 병렬 크롤링
    all_results = await orchestrator.crawl_all_companies(max_jobs=3)

    return result

# 실행
asyncio.run(crawl())
```

### 저장 경로 구조

```
data/
├── html/
│   ├── Coupang/
│   │   └── 2025-11-13/
│   │       ├── coupang_001_Software_Engineer.html
│   │       └── coupang_002_Data_Scientist.html
│   └── Woowahan/
│       └── 2025-11-13/
│           ├── R2508018_...html
│           └── R2511004_...html
├── metadata/
│   ├── Coupang/
│   │   └── 2025-11-13/
│   │       ├── coupang_001_metadata.json
│   │       └── coupang_002_metadata.json
│   └── Woowahan/
│       └── 2025-11-13/
│           ├── R2508018_metadata.json
│           └── R2511004_metadata.json
└── pdfs/
    ├── Coupang/
    │   └── 2025-11-13/
    │       ├── coupang_001_...20251113_200927.pdf
    │       └── coupang_002_...20251113_200928.pdf
    └── Woowahan/
        └── 2025-11-13/
            ├── R2508018_...pdf
            └── R2511004_...pdf
```

### 결과 JSON 형식

```json
{
  "success": true,
  "company_name": "Coupang",
  "total_jobs": 5,
  "successful_saves": 5,
  "failed_saves": 0,
  "job_listings": [
    {
      "url": "https://www.coupang.jobs/kr/jobs/...",
      "job_id": "coupang_123",
      "title": "Software Engineer",
      "company": "Coupang",
      "location": "Seoul, South Korea",
      "posting_date": "2025-11-13",
      "closing_date": "2025-12-13",
      "job_description": "...",
      "metadata": {...}
    }
  ],
  "storage_results": [
    {
      "success": true,
      "job_id": "coupang_123",
      "title": "Software Engineer",
      "html_path": "data/html/Coupang/2025-11-13/...",
      "json_path": "data/metadata/Coupang/2025-11-13/...",
      "pdf_path": "data/pdfs/Coupang/2025-11-13/..."
    }
  ],
  "elapsed_seconds": 65.98,
  "timestamp": "2025-11-13T20:09:35.121000"
}
```

## 새로운 회사 크롤러 추가하기

### 1. 새 크롤러 클래스 작성

```python
# crawlers/amazon.py
from typing import List, Dict, Optional, Any
from playwright.async_api import Page
from .base_crawler import BaseCrawler

class AmazonCrawler(BaseCrawler):
    def get_company_name(self) -> str:
        return "Amazon"

    def get_job_list_urls(self) -> List[str]:
        return ["https://amazon.jobs/en/search"]

    async def extract_job_urls(self, page: Page) -> List[Dict[str, str]]:
        """Playwright page에서 공고 URL 추출"""
        try:
            job_urls = []
            # JavaScript 실행 또는 CSS 선택자로 URL 추출
            links = await page.query_selector_all('a[href*="/jobs/"]')
            for link in links:
                href = await link.get_attribute('href')
                if href:
                    job_urls.append({
                        "url": self._normalize_url(href),
                        "job_id": self._extract_job_id(href),
                        "title": ""
                    })
            return job_urls
        except Exception as e:
            self.logger.error(f"Failed to extract job URLs: {e}")
            return []

    async def parse_job_detail(self, page: Page, url: str, idx: int) -> Optional[Dict[str, Any]]:
        """상세 페이지 파싱"""
        try:
            await page.goto(url, wait_until='domcontentloaded', timeout=self.get_timeout())
            await asyncio.sleep(self.get_wait_time())

            job_data = {
                "url": url,
                "job_id": self._extract_job_id(url),
                "company": self.get_company_name(),
                "title": "",
                "location": "",
                "job_description": "",
                # ... 기타 필드
                "metadata": {}
            }

            # JavaScript로 데이터 추출
            result = await page.evaluate("""
                () => {
                    return {
                        title: document.querySelector('h1')?.textContent || '',
                        location: document.querySelector('[class*="location"]')?.textContent || '',
                    };
                }
            """)

            job_data.update(result)
            return job_data
        except Exception as e:
            self.logger.error(f"Failed to parse job detail: {e}")
            return None

    def get_wait_time(self) -> int:
        return 3

    def get_max_concurrent_jobs(self) -> int:
        return 3

    def get_timeout(self) -> int:
        return 30000

    def requires_playwright(self) -> bool:
        return True

    def _normalize_url(self, href: str) -> str:
        if href.startswith("http"):
            return href
        elif href.startswith("/"):
            return "https://amazon.jobs" + href
        else:
            return "https://amazon.jobs/" + href

    def _extract_job_id(self, url: str) -> str:
        # URL에서 job_id 추출 로직
        job_id = url.rstrip('/').split('/')[-1]
        return f"amazon_{job_id}"
```

### 2. 레지스트리에 등록

```python
import asyncio
from crawlers import CrawlerRegistry, AmazonCrawler
from async_orchestrator import AsyncPlaywrightOrchestrator

async def main():
    registry = CrawlerRegistry()
    registry.register(AmazonCrawler())

    orchestrator = AsyncPlaywrightOrchestrator(registry=registry)
    result = await orchestrator.crawl_company("Amazon", max_jobs=5)

asyncio.run(main())
```

### 3. 크롤러 구현 체크리스트

- ✅ `get_company_name()`: 회사명 반환
- ✅ `get_job_list_urls()`: 채용 목록 페이지 URL 반환
- ✅ `extract_job_urls(page)`: Playwright page에서 URL 추출
- ✅ `parse_job_detail(page, url, idx)`: 상세 페이지 파싱
- ✅ `get_wait_time()`: 페이지 로드 대기 시간 (초)
- ✅ `get_max_concurrent_jobs()`: 동시 처리 수
- ✅ `get_timeout()`: 타임아웃 (밀리초)
- ✅ `requires_playwright()`: True 반환
- ✅ `_normalize_url()`: 상대 URL을 절대 URL로 변환
- ✅ `_extract_job_id()`: URL에서 고유 job_id 추출

## 프로젝트 구조

```
crawler_agent/
├── crawlers/
│   ├── __init__.py
│   ├── base_crawler.py           # 추상 기본 클래스
│   ├── registry.py               # Registry 패턴
│   ├── coupang.py                # Coupang 크롤러 (CloudFlare 우회)
│   ├── woowahan.py               # Woowahan 크롤러
│   ├── naver.py                  # Naver 크롤러 (예제)
│   └── kakao.py                  # Kakao 크롤러 (예제)
├── agents/
│   ├── __init__.py
│   ├── playwright_capture.py     # Playwright 기반 PDF 캡처 Agent
│   └── storage.py                # 저장소 Agent (HTML/JSON/PDF)
├── async_orchestrator.py         # 비동기 Playwright 오케스트레이터
├── orchestrator.py               # 레거시 LangGraph 오케스트레이터
├── config.py                     # 설정 관리
├── main.py                       # 메인 스크립트 (레거시)
├── requirements.txt              # Python 의존성
├── .env.example                  # 환경 변수 예제
└── README.md                     # 이 파일
```

**주요 디렉토리:**
- `data/html/`: 원본 HTML 파일
- `data/metadata/`: JSON 메타데이터
- `data/pdfs/`: PDF 파일

## 핵심 설계 패턴

### 1. Registry 패턴
새로운 회사 크롤러를 동적으로 등록하고 관리:
```python
registry = CrawlerRegistry()
registry.register(CoupangCrawler())  # 새 크롤러 추가
crawler = registry.get_crawler("Coupang")  # 조회
```

### 2. Strategy 패턴 (BaseCrawler)
각 회사별로 다른 크롤링 전략을 구현:
- URL 추출 로직 (크롤러별로 다름)
- 데이터 파싱 (페이지 구조가 다름)
- 동시성 설정 (CloudFlare 등 제약이 다름)

### 3. Semaphore 기반 동시성 제어
각 크롤러의 `get_max_concurrent_jobs()`에 따라 동시 요청 수 제한:
```python
# Coupang: 2개 (CloudFlare 보호로 보수적)
# Woowahan: 3개 (안정적)
# Kakao: 3개 (일반적)
```

### 4. 하이브리드 CloudFlare 우회
- **목록 페이지**: `cloudscraper` (요청 기반)
- **상세 페이지**: `playwright-stealth` (브라우저 에뮬레이션)
- **효과**: CloudFlare의 JavaScript 챌린지 + 봇 감지 모두 우회

### 5. 데이터 저장 전략
3가지 형식으로 병렬 저장:
- **HTML**: 원본 페이지 (검색/분석용)
- **JSON**: 구조화된 메타데이터 (처리용)
- **PDF**: 시각적 증거 (보관용)

## 성능 특성

### 동시성 모델
- **비동기/병렬**: asyncio + asyncio.Semaphore
- **스레드 사용**: `asyncio.to_thread()` for I/O 작업
- **오버헤드**: 미니멀 (이벤트 루프 기반)

### 처리 시간 예상
- **Woowahan** (20개): ~50초
- **Coupang** (3개): ~65초
- 총 크롤링 + PDF 캡처 포함

### 메모리 사용
- **브라우저 인스턴스**: 회사당 1개 (컨텍스트 재사용)
- **페이지**: Semaphore로 동시 생성 제어
- **PDF 메모리**: streaming으로 최적화

## 에러 처리

### 크롤링 실패 시나리오
1. **URL 추출 실패**: 해당 회사 전체 스킵
2. **개별 공고 파싱 실패**: 해당 공고만 스킵, 나머지 계속
3. **PDF 캡처 실패**: HTML/JSON은 저장, PDF만 스킵
4. **파일 저장 실패**: 로그만 기록, 계속 진행

### 예외 처리
- 모든 async 작업은 `try-except`로 감싸짐
- 에러는 `error_logs` 배열에 수집
- 부분 실패도 성공으로 간주 (일부 데이터는 저장됨)

## 확장 가능성

### 벡터 임베딩
```python
orchestrator = AsyncPlaywrightOrchestrator(
    ...,
    use_vector_embedding=True  # 활성화
)
# JobPostingData.vector_embedding에 저장됨
```

### 데이터베이스 연동
StorageAgent 상속 후 `save_to_db()` 메서드 추가:
```python
class DatabaseStorageAgent(StorageAgent):
    def save_json_locally(self, ...):
        # DB에도 저장
```

### 스케줄링
Celery, APScheduler 등과 통합 가능 (asyncio 호환)

## 라이선스

MIT License

## 지원

문제가 발생하면 이슈를 등록하거나 로그 파일(`crawler.log`)을 확인하세요.
