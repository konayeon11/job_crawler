# 채용공고 크롤러 에이전트 (Job Posting Crawler Agent)

한국 주요 기업들의 채용공고를 자동으로 수집하고, 메타데이터와 웹페이지 스크린샷을 저장하는 비동기 웹 크롤러 시스템입니다.

**완전 비동기 처리** | **CloudFlare 우회** | **PNG 이미지 캡처** | **HTML/JSON 메타데이터 저장**

## 주요 특징

### 비동기 아키텍처
- **AsyncPlaywrightOrchestrator**: 완전 비동기 처리로 높은 동시성 지원
- **Playwright 기반**: 동적 페이지 렌더링 및 JavaScript 실행 가능
- **CloudFlare 우회**: playwright-stealth + cloudscraper로 보안 우회

### 플러그인 아키텍처
- **Registry 패턴**: 새로운 회사 크롤러를 간단히 추가 가능
- **BaseCrawler**: 모든 크롤러가 구현해야 하는 공통 인터페이스
- **확장성**: 새 회사를 추가할 때 코어 로직 수정 불필요

### 데이터 저장 포맷
- **HTML**: 원본 HTML 파일 (`data/html/`)
- **JSON**: 구조화된 메타데이터 (`data/metadata/`)
- **PNG 이미지**: 웹페이지 전체 스크린샷 (`data/screenshots/`)

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
5. JSON 메타데이터 저장
   ↓
6. PNG 이미지 캡처 (Playwright - 병렬 처리)
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
- HTML + JSON 메타데이터 + PNG 이미지 동시 저장
- playwright-stealth를 통한 자동 감지 우회

**주요 메서드:**
- `crawl_company(company_name, max_jobs)`: 특정 회사 크롤링
  - `company_name`: 크롤러에 등록된 회사명 (예: "Coupang", "Woowahan")
  - `max_jobs`: 최대 크롤링 공고 수 (None이면 전체)
  - 반환값: 크롤링 결과 + 저장 경로 정보
- `crawl_all_companies(max_jobs)`: 모든 회사 병렬 크롤링
  - 모든 등록된 회사를 동시에 크롤링
  - 각 회사는 독립적인 asyncio 태스크로 실행

#### 4. PlaywrightCaptureAgent
Playwright 기반 웹페이지 스크린샷 캡처:
- **PNG/JPEG 형식 지원**: PNG는 고품질(~2.4MB), JPEG는 압축 포맷(~300KB)
- **전체 페이지 캡처**: `full_page=True`로 스크롤 영역까지 모두 캡처
- **동적 콘텐츠 처리**: 자동 스크롤로 lazy-loading 콘텐츠 로드
- **배치 처리**: 여러 URL을 병렬로 효율적으로 캡처
- **Chrome DevTools Protocol (CDP)**: 정확한 렌더링 지원

**주요 메서드**:
```python
# 단일 페이지 이미지 캡처
image_bytes = await capture_agent.capture_as_image(
    url="https://...",
    wait_time=5,           # 로드 후 대기시간 (초)
    image_format="png"     # "png" 또는 "jpeg"
)

# 여러 페이지 일괄 캡처
results = await capture_agent.capture_as_image_bulk(urls)

# 호환성 유지 (권장하지 않음)
image_bytes = await capture_agent.capture_as_pdf(url)  # 내부적으로 이미지 캡처
```

#### 5. StorageAgent
데이터 저장소 관리:
- **이미지 저장**: `save_image_locally()` - PNG/JPEG 포맷으로 로컬 저장
- **S3 클라우드 저장**: `save_image_to_s3()` - AWS S3에 이미지 업로드
- **HTML 저장**: 원본 웹페이지 HTML 저장
- **JSON 저장**: 구조화된 메타데이터 JSON 저장
- **한국어 파일명**: 한국어 공고 제목을 포함한 파일명 지원

**주요 메서드**:
```python
# 이미지를 로컬과 S3 모두 저장
result = storage_agent.save_image(
    image_bytes=image_data,
    company="KT",
    job_id="kt_232245",
    job_title="소프트웨어 개발자",
    subfolder="2025-11-18",
    image_format="png",        # "png" 또는 "jpeg"
    save_to_s3=True           # S3 저장 포함
)

# 결과: {
#   "success": True,
#   "local_path": "data/screenshots/KT/2025-11-18/...",
#   "s3_key": "KT/2025-11-18/..."
# }
```

**저장 경로 구조**:
```
data/
├── screenshots/          # PNG 이미지 저장
│   └── KT/
│       └── 2025-11-18/
│           ├── kt_232245_소프트웨어개발자_20251118_110414.png
│           └── kt_232369_데이터분석가_20251118_110524.png
├── html/                # 원본 HTML 저장
│   └── KT/2025-11-18/*.html
├── metadata/            # JSON 메타데이터
│   └── KT/2025-11-18/*_metadata.json
└── pdfs/                # 레거시 PDF (호환성)
    └── KT/2025-11-18/*.pdf
```

#### 6. CloudFlare 우회 전략
**하이브리드 접근:**
- **목록 페이지**: cloudscraper로 JavaScript 챌린지 우회
- **상세 페이지**: playwright-stealth로 자동 감지 우회
- **User-Agent**: 실제 Chrome 브라우저와 동일하게 설정
- **Stealth 적용**: 모든 Playwright page 인스턴스에 적용

## 빠른 시작 (5분 안에 시작하기)

### 1. 저장소 복제 및 기본 설정
```bash
# 1. 이 프로젝트 클론
git clone https://github.com/your-repo/crawler_agent
cd crawler_agent

# 2. Python 가상 환경 생성
python -m venv venv

# Windows
venv\Scripts\activate
# macOS/Linux
source venv/bin/activate

# 3. 의존성 설치
pip install -r requirements.txt
```

### 2. 5줄로 크롤링 시작하기
```python
import asyncio
from crawlers import CrawlerRegistry, CoupangCrawler
from async_orchestrator import AsyncPlaywrightOrchestrator

async def main():
    registry = CrawlerRegistry()
    registry.register(CoupangCrawler())
    orchestrator = AsyncPlaywrightOrchestrator(registry=registry)
    result = await orchestrator.crawl_company("Coupang", max_jobs=3)
    print(f"크롤링 완료! {result['total_jobs']}개 공고 저장")

asyncio.run(main())
```

### 3. 결과 확인
```bash
# 저장된 파일 확인
ls data/screenshots/Coupang/$(date +%Y-%m-%d)/  # PNG 이미지
ls data/html/Coupang/$(date +%Y-%m-%d)/         # HTML
ls data/metadata/Coupang/$(date +%Y-%m-%d)/     # JSON 메타데이터
```

## 설치

### 1. 의존성 설치
```bash
pip install -r requirements.txt
```

**주요 의존성:**
- `playwright`: 웹 브라우저 자동화
- `playwright-stealth`: CloudFlare 우회
- `cloudscraper`: CloudFlare JavaScript 챌린지 우회
- `aiohttp`: 비동기 HTTP 요청
- `beautifulsoup4`: HTML 파싱

### 2. Playwright 브라우저 설치
```bash
playwright install chromium
```

### 3. 환경 변수 설정 (선택사항)
```bash
cp .env.example .env
# .env 파일 수정 (S3, 프록시 등 설정)
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
├── crawlers/                     # 회사별 크롤러 구현
│   ├── __init__.py
│   ├── base_crawler.py           # 추상 기본 클래스 (필수 메서드 정의)
│   ├── registry.py               # Registry 패턴 (크롤러 관리)
│   ├── coupang.py                # Coupang 크롤러 (CloudFlare 우회)
│   ├── woowahan.py               # Woowahan 크롤러
│   ├── kt.py                     # KT 크롤러
│   ├── naver.py                  # Naver 크롤러
│   └── kakao.py                  # Kakao 크롤러
├── agents/                       # 데이터 처리 에이전트
│   ├── __init__.py
│   ├── playwright_capture.py     # Playwright 기반 이미지 캡처 (PNG/JPEG)
│   └── storage.py                # 저장소 에이전트 (로컬/S3)
├── async_orchestrator.py         # 비동기 오케스트레이터 (크롤링 조율)
├── orchestrator.py               # 레거시 LangGraph 오케스트레이터
├── config.py                     # 설정 관리
├── main.py                       # 메인 스크립트
├── requirements.txt              # Python 의존성
├── .env.example                  # 환경 변수 예제
├── test_image_capture.py         # 이미지 캡처 테스트
└── README.md                     # 이 파일
```

**저장 디렉토리:**
```
data/
├── screenshots/   # PNG 이미지 (2.4MB/개) - 메인 저장소
├── html/          # 원본 HTML 파일
├── metadata/      # JSON 메타데이터 (구조화된 정보)
└── pdfs/          # 레거시 PDF 파일 (호환성용)
```

## 코드 이해하기 (초보자 가이드)

### 1. 실행 흐름 이해하기

**크롤링이 시작되면 다음과 같은 순서로 실행됩니다:**

```
메인 스크립트
    ↓
CrawlerRegistry에서 크롤러 등록
    ↓
AsyncPlaywrightOrchestrator 생성
    ↓
crawl_company() 호출
    ↓
┌─────────────────────────────────┐
│ 1️⃣  채용 목록 페이지 열기        │
│   (Playwright 사용)              │
└──────────┬──────────────────────┘
           ↓
┌─────────────────────────────────┐
│ 2️⃣  공고 URL 추출               │
│   (크롤러별 고유 로직)            │
└──────────┬──────────────────────┘
           ↓
┌─────────────────────────────────┐
│ 3️⃣  각 공고 상세 페이지 파싱     │
│   (병렬 처리, Semaphore로 제어)  │
└──────────┬──────────────────────┘
           ↓
┌─────────────────────────────────┐
│ 4️⃣  HTML, JSON, PNG 병렬 저장   │
│   (각각 다른 디렉토리)            │
└──────────┬──────────────────────┘
           ↓
결과 반환 (성공 여부, 저장 경로 등)
```

### 2. 각 파일의 역할

#### `crawlers/base_crawler.py`
**역할**: 모든 크롤러가 따를 공통 인터페이스 정의
**핵심 개념**: 추상 클래스 (Abstract Base Class)
**이것이 필요한 이유**: 새로운 크롤러를 추가할 때 어떤 메서드를 구현해야 하는지 명확함

```python
# 모든 크롤러는 이 클래스를 상속
class BaseCrawler:
    async def extract_job_urls(self, page):
        """필수 구현: URL 추출"""
        pass

# 새 크롤러 만들 때
class AmazonCrawler(BaseCrawler):
    async def extract_job_urls(self, page):
        # Amazon 맞춤 로직 작성
        pass
```

#### `crawlers/registry.py`
**역할**: 등록된 크롤러들을 관리하는 저장소
**핵심 개념**: Registry 패턴 (동적으로 객체 등록/조회)
**이것이 필요한 이유**: 메인 코드 수정 없이 새 크롤러 추가 가능

```python
registry = CrawlerRegistry()
registry.register(CoupangCrawler())    # 등록
registry.register(WoowahanCrawler())
crawler = registry.get_crawler("Coupang")  # 조회
```

#### `agents/playwright_capture.py`
**역할**: 웹페이지를 PNG/JPEG 이미지로 캡처
**핵심 개념**: 이미지 캡처 (PDF → PNG/JPEG로 마이그레이션)
**이것이 필요한 이유**: 웹페이지를 증거 자료로 보존

```python
# 단일 페이지 캡처
image_bytes = await capture_agent.capture_as_image(url)

# 여러 페이지 일괄 캡처
results = await capture_agent.capture_as_image_bulk(urls)
```

#### `agents/storage.py`
**역할**: 캡처한 이미지, HTML, JSON을 저장소에 보관
**핵심 개념**: 다중 저장소 지원 (로컬 + S3)
**이것이 필요한 이유**: 유연한 저장소 선택 (개발 시 로컬, 프로덕션 시 S3)

```python
# 로컬 저장소에만 저장
result = storage.save_image(image_bytes, ..., save_to_s3=False)

# 로컬 + S3 모두 저장
result = storage.save_image(image_bytes, ..., save_to_s3=True)
```

#### `async_orchestrator.py`
**역할**: 크롤링 전체 프로세스를 조율
**핵심 개념**: 오케스트레이터 패턴 (여러 에이전트 조율)
**이것이 필요한 이유**: 복잡한 워크플로우를 단순하게 관리

```python
# 한 줄로 크롤링 시작
result = await orchestrator.crawl_company("Coupang", max_jobs=5)
# 내부적으로는 URL 추출 → 파싱 → 캡처 → 저장을 모두 수행
```

### 3. 비동기 프로그래밍 이해하기

**async/await가 중요한 이유**: 여러 웹페이지를 **동시에** 처리

```python
# ❌ 느림: 순차 처리 (1페이지 5초 × 10페이지 = 50초)
for url in urls:
    await crawl_page(url)  # 하나 끝나야 다음 시작

# ✅ 빠름: 병렬 처리 (동시에 10개 처리 = 약 5초)
tasks = [crawl_page(url) for url in urls]
await asyncio.gather(*tasks)  # 모두 동시 실행
```

### 4. Semaphore로 동시 처리 제한하기

**문제**: 동시에 너무 많은 요청을 하면 서버가 차단 (CloudFlare)

```python
# Semaphore: "최대 3개씩만 동시 처리"
semaphore = asyncio.Semaphore(3)

async def crawl_with_limit(url):
    async with semaphore:  # 최대 3개까지만 이 코드 실행
        await crawl_page(url)
```

### 5. 에러 처리 이해하기

```python
# 하나 실패해도 다른 것은 계속
tasks = [crawl_page(url) for url in urls]
results = await asyncio.gather(*tasks, return_exceptions=True)
# results: [data1, data2, Exception(...), data4, ...]
```

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
3. **이미지 캡처 실패**: HTML/JSON은 저장, 이미지만 스킵
4. **파일 저장 실패**: 로그만 기록, 계속 진행

### 예외 처리
- 모든 async 작업은 `try-except`로 감싸짐
- 에러는 `error_logs` 배열에 수집
- 부분 실패도 성공으로 간주 (일부 데이터는 저장됨)

## 트러블슈팅

### 문제 1: "CloudFlare 보호로 인해 접근 불가"
**증상**: `Error 1020: Access Denied` 또는 `Error 1009: Country Restricted`
**원인**: 웹사이트가 CloudFlare 보호를 하고 있음
**해결책**:
1. `get_max_concurrent_jobs()` 값을 더 작게 설정 (보수적으로)
2. `get_wait_time()` 값을 더 크게 설정 (로드 시간 증가)
3. playwright-stealth가 적용되는지 확인: `crawlers/base_crawler.py` 참고

```python
def get_max_concurrent_jobs(self) -> int:
    return 2  # CloudFlare 대비 보수적 설정

def get_wait_time(self) -> int:
    return 5  # 로드 대기시간 증가
```

### 문제 2: "Timeout 에러"
**증상**: `Timeout waiting for page load` 또는 `Navigation timeout`
**원인**: 페이지 로드가 너무 오래 걸림
**해결책**:
```python
# 1. Timeout 값 증가
image_bytes = await capture_agent.capture_as_image(
    url=url,
    timeout=90000  # 기본값: 60000ms (1분), 1.5분으로 증가
)

# 2. wait_time 증가
capture_as_image(..., wait_time=10)  # 로드 후 10초 대기

# 3. 네트워크 상황 개선 (프록시 사용, 시간 변경)
```

### 문제 3: "메모리 부족 (Out of Memory)"
**증상**: `MemoryError` 또는 시스템이 응답 없음
**원인**: 동시 처리 공고가 너무 많음, PNG 이미지가 큼
**해결책**:
```python
# 1. 동시성 감소
registry.register(MyCrawler())  # get_max_concurrent_jobs() = 2

# 2. JPEG 포맷 사용 (PNG 보다 90% 더 작음)
image_bytes = await capture_agent.capture_as_image(
    url=url,
    image_format="jpeg"  # PNG 대신 JPEG 사용
)

# 3. 최대 공고 수 제한
result = await orchestrator.crawl_company("MyCompany", max_jobs=5)
```

### 문제 4: "이미지가 저장되지 않음"
**증상**: HTML/JSON은 저장되지만 이미지 파일이 없음
**원인**: 이미지 캡처 실패 또는 저장소 권한 문제
**확인 사항**:
```bash
# 1. 디렉토리 생성 확인
ls -la data/screenshots/

# 2. 파일 시스템 권한 확인
ls -la data/

# 3. 로그 확인
grep "Image captured" crawler.log
grep "Failed to capture image" crawler.log
```

### 문제 5: "중복된 데이터 저장"
**증상**: 같은 공고가 여러 번 저장됨
**원인**: 크롤러가 중복된 URL을 추출함
**해결책**:
```python
# BaseCrawler에서 중복 제거
async def extract_job_urls(self, page: Page) -> List[Dict[str, str]]:
    job_urls = []
    seen_urls = set()  # 중복 추적

    for url in raw_urls:
        normalized = url.rstrip('/')  # 정규화
        if normalized not in seen_urls:
            job_urls.append({"url": normalized, "job_id": ...})
            seen_urls.add(normalized)

    return job_urls
```

## 자주 묻는 질문 (FAQ)

### Q1: PNG와 JPEG 형식 중 어떤 것을 사용해야 하나?
**A**:
- **PNG** (기본값): 손실 없는 고품질 (~2.4MB/개)
  - 장점: 압축하지 않은 정확한 시각화
  - 단점: 파일 크기 큼, 저장소 많이 필요
- **JPEG**: 손실 압축 (~300KB/개, ~90% 더 작음)
  - 장점: 파일 크기 작음, 빠른 저장
  - 단점: 약간의 품질 손실

**추천**: 저장소 제약이 없으면 PNG, 저장소 제약이 있으면 JPEG 사용

### Q2: 새 회사를 추가하려면 어떻게 해야 하나?
**A**: 5단계로 진행:
1. `crawlers/` 디렉토리에 새 파일 생성 (예: `amazon.py`)
2. `BaseCrawler` 상속하는 클래스 작성
3. 필수 메서드 구현 (위의 "새로운 회사 크롤러 추가하기" 섹션 참고)
4. `crawlers/__init__.py`에서 import
5. 메인 스크립트에서 레지스트리에 등록

### Q3: 크롤링한 데이터를 데이터베이스에 저장할 수 있나?
**A**: 가능합니다! 두 가지 방법:
1. **StorageAgent 상속**:
```python
class DatabaseStorageAgent(StorageAgent):
    def save_json_locally(self, job, company, job_id, subfolder):
        # 파일 저장
        local_path = super().save_json_locally(job, company, job_id, subfolder)
        # + DB 저장
        self.db.insert("jobs", job)
        return local_path
```

2. **결과 후처리**:
```python
result = await orchestrator.crawl_company("Coupang")
for job in result['job_listings']:
    database.insert(job)
```

### Q4: 프록시를 사용할 수 있나?
**A**: Playwright에서 지원합니다:
```python
browser = await p.chromium.launch(
    proxy="http://proxy.example.com:8080"
)
```

### Q5: 크롤러를 스케줄링해서 매일 실행할 수 있나?
**A**: APScheduler나 Celery 사용:
```python
from apscheduler.schedulers.asyncio import AsyncIOScheduler

scheduler = AsyncIOScheduler()
scheduler.add_job(crawl_job, 'cron', hour=9)  # 매일 9시 실행
```

### Q6: 로그를 파일에 저장하고 싶어요
**A**: 로깅 설정:
```python
import logging

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('crawler.log'),
        logging.StreamHandler()
    ]
)
```

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
