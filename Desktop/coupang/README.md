# 쿠팡 채용사이트 크롤러

쿠팡 채용사이트(https://www.coupang.jobs/kr/jobs/)의 채용공고를 자동으로 수집하고 정보를 추출하는 Python CLI 도구입니다.

## 주요 기능

- ✅ CloudScraper를 사용한 CloudFlare 우회 크롤링
- ✅ 메인 페이지에서 모든 채용공고 링크 수집
- ✅ 각 공고 페이지의 `article.cms-content` 영역에서 본문 크롤링
- ✅ 공고게시일, 마감일, 지역, 고용형태 등 정보 자동 추출
- ✅ 재시도 로직과 에러 처리
- ✅ Claude API를 통한 지능형 텍스트 파싱 (선택사항)
- ✅ JSON 형식으로 데이터 저장
- ✅ 실시간 진행상황 표시 (이모지 포함)
- ✅ 크롤링 통계 출력 (수집 개수, 소요시간, 평균 처리시간)
- ✅ 한국 채용공고만 필터링 (`--korea` 옵션)
- ✅ 최신 공고 먼저 정렬 (최신 크롤링 순서로 배열)

## 설치

### 1. 필수 요구사항

- Python 3.8 이상

### 2. 패키지 설치

```bash
pip install -r requirements.txt
```

또는 개별 설치:

```bash
pip install requests beautifulsoup4 cloudscraper anthropic
```

## 사용법

### 기본 사용

```bash
python coupang_crawler.py
```

### 주요 옵션

| 옵션 | 설명 | 기본값 |
|------|------|--------|
| `-o`, `--output` | JSON 출력 파일 경로 | `coupang_jobs.json` |
| `--max` | 최대 수집 개수 | 제한 없음 |
| `--delay` | 요청 간 대기시간 (초) | `2.0` |
| `--location` | 위치 필터 (서버 필터링, 페이지네이션 지원) | 없음 |
| `--korea` | 한국 채용만 수집 (클라이언트 필터링) | 비활성화 |
| `--ai` | Claude API 파싱 활성화 | - |
| `--api-key` | Anthropic API 키 | - |

### 사용 예시

#### 1. 모든 공고 수집

```bash
python coupang_crawler.py
```

#### 2. South Korea 위치 필터로 모든 공고 수집 (서버 필터링, 권장)

```bash
python coupang_crawler.py --location "South Korea"
```

#### 3. 다른 위치로 필터링 (예: Seoul, Busan)

```bash
python coupang_crawler.py --location Seoul
python coupang_crawler.py --location Busan
```

#### 4. 한국 채용만 수집 (클라이언트 필터링, 모든 페이지 크롤링)

```bash
python coupang_crawler.py --korea
```

#### 5. 위치 필터 + 최대 개수 제한

```bash
python coupang_crawler.py --location "South Korea" --max 30
```

#### 6. 빠르게 크롤링 (대기시간 감소)

```bash
python coupang_crawler.py --location "South Korea" --delay 1
```

#### 7. 커스텀 출력 파일

```bash
python coupang_crawler.py --location "South Korea" -o results/korea_jobs.json
```

#### 8. Claude API를 사용한 지능형 파싱

```bash
python coupang_crawler.py --location "South Korea" --ai --api-key your-api-key
```

또는 환경변수 설정:

```bash
export ANTHROPIC_API_KEY=your-api-key
python coupang_crawler.py --location "South Korea" --ai
```

## 출력 데이터 구조

크롤링된 데이터는 JSON 형식으로 저장되며, 각 채용공고는 다음 정보를 포함합니다:

```json
{
  "url": "채용공고 URL",
  "title": "채용공고 제목",
  "posting_date": "공고게시일 (YYYY-MM-DD)",
  "closing_date": "마감일 (YYYY-MM-DD)",
  "location": "근무지역",
  "employment_type": "고용형태",
  "required_qualifications": "필수조건",
  "preferred_qualifications": "우대조건",
  "job_description": "직무소개",
  "company_description": "회사소개",
  "content": "전체 본문 텍스트",
  "crawled_at": "크롤링 시각 (ISO 8601)"
}
```

### 정렬 순서

출력되는 JSON 배열은 **최신 크롤링 순서로 정렬**되어 있습니다. 즉, 가장 최신으로 발견된 공고가 배열의 첫 번째에 위치합니다.

### 페이지네이션

`--location` 옵션 사용 시 **자동으로 모든 페이지를 크롤링**합니다:

- 예: `--location "South Korea"`는 South Korea 위치의 모든 공고를 수집 (약 29개, 2페이지)
- 내부적으로 이진 탐색을 사용하여 마지막 페이지를 자동으로 탐지
- 각 페이지를 순차적으로 크롤링하여 모든 공고를 수집

**--korea 옵션 사용 시:**
- 메인 페이지(페이지 1)에서 공고를 수집한 후
- 클라이언트 필터링으로 한국 공고만 추출
- 페이지네이션을 지원하지 않음

## 기술 스택

- **requests**: HTTP 요청
- **BeautifulSoup4**: HTML 파싱
- **cloudscraper**: CloudFlare 우회
- **anthropic**: Claude AI API (선택사항)
- **argparse**: CLI 인터페이스

## 주요 기능 설명

### 1. CloudFlare 우회 크롤링

CloudScraper를 사용하여 CloudFlare 봇 차단을 자동으로 우회합니다.

### 2. 재시도 로직

- 최대 3회 재시도
- 지수 백오프 방식의 대기 시간
- HTTP 429 (Too Many Requests) 자동 처리
- 네트워크 오류 자동 복구

### 3. 정보 추출

정규식과 HTML 파싱을 통해 다음 정보를 자동으로 추출합니다:
- 공고게시일
- 마감일
- 근무지역
- 고용형태
- 필수조건 / 우대조건
- 직무소개 / 회사소개

### 4. Claude AI 파싱

`--ai` 옵션 사용 시 Claude API가 크롤링된 텍스트를 분석하여 더 정확한 정보 추출을 수행합니다.

## 크롤링 통계

크롤링 완료 후 다음 통계가 출력됩니다:

```
✅ 수집 완료: 5개 | ❌ 수집 실패: 0개
📁 저장 경로: coupang_jobs.json
⏱️  총 소요 시간: 9.97초
⚡ 평균 처리시간: 1.99초/개
```

## 중요 사항

### 한국어 헤더 설정

다음과 같은 한국어 관련 헤더를 설정하여 한국 사이트에서 적절한 콘텐츠를 수신합니다:

```python
'Accept-Language': 'ko-KR,ko;q=0.9,en-US;q=0.8,en;q=0.7'
```

### 에러 처리

- 페이지 접속 실패 시 자동 재시도
- 네트워크 타임아웃 자동 처리
- 404/403 오류는 건너뛰고 계속 진행

### 과부하 방지

- 각 요청 간 2초 기본 대기 (조정 가능)
- CloudFlare 레이트 리미트 자동 처리
- 사이트 서버에 미치는 부하 최소화

## 주의사항

1. **이용약관 준수**: 웹사이트의 이용약관과 robots.txt를 확인하세요.
2. **개인정보 보호**: 수집된 데이터의 저장 및 사용 시 개인정보 보호법을 준수하세요.
3. **과도한 크롤링 자제**: 적절한 `--delay` 값을 설정하여 서버에 부담을 주지 않으세요.

## 문제 해결

### CloudScraper 초기화 실패

CloudScraper 설치 후에도 초기화 실패 시, 일반 requests 라이브러리로 자동으로 폴백됩니다.

### 타임아웃 오류

네트워크가 느린 경우 `--delay` 값을 늘려보세요:

```bash
python coupang_crawler.py --delay 5
```

### API 키 오류

Claude API 파싱 사용 시 API 키가 필요합니다:

```bash
# 옵션 1: 커맨드라인에서 전달
python coupang_crawler.py --ai --api-key sk-...

# 옵션 2: 환경변수 설정
export ANTHROPIC_API_KEY=sk-...
python coupang_crawler.py --ai
```

## 라이선스

MIT License

## 기여

이슈와 PR은 언제나 환영합니다!
