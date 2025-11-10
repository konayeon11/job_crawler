# 🏗️ 시스템 아키텍처 및 설계 문서

## 📋 프로젝트 개요

대한민국 IT 채용공고 전문 크롤링 시스템으로, 다양한 사이트 패턴을 자동 감지하고 IT 직군만 정확히 수집하는 엔터프라이즈급 파이프라인입니다.

### 핵심 목표
1. **정확성**: IT 직군만 99% 정확도로 필터링
2. **안정성**: robots.txt 준수, 요청 제한, 에러 복구
3. **확장성**: 새로운 사이트 패턴 자동 학습
4. **추적성**: 모든 데이터의 출처와 경로 완전 기록

## 🎯 5가지 크롤링 패턴

### 1. Static Toggle (정적 토글)
- **특징**: 버튼 클릭 시 DOM 즉시 변경
- **예시**: 카테고리 필터 버튼
- **구현**: `StaticToggleHandler`
- **감지**: DOM 변경 전후 비교

### 2. A Link (링크 기반)
- **특징**: 각 공고가 개별 URL
- **예시**: 일반적인 채용 사이트
- **구현**: `ALinkHandler`
- **감지**: `<a href>` 태그 패턴

### 3. Function (함수형)
- **특징**: onclick, 모달, 다이얼로그
- **예시**: 클릭 시 팝업 표시
- **구현**: `FunctionHandler`
- **감지**: onclick 속성, modal 요소

### 4. Hash Routing (SPA)
- **특징**: URL 해시 변경으로 라우팅
- **예시**: React/Vue SPA
- **구현**: `HashRoutingHandler`
- **감지**: URL에 # 포함 + SPA 프레임워크

### 5. API Direct (API 직접)
- **특징**: REST API 또는 GraphQL
- **예시**: 헤드리스 API
- **구현**: `APIDirectHandler`
- **감지**: 네트워크 캡처로 API 엔드포인트 추출

## 🔄 자동 프로파일링 시퀀스

```
┌─────────────────────────────────────────────┐
│ 1. JSON-LD 탐지                             │
│    • <script type="application/ld+json">   │
│    • @type: "JobPosting"                   │
└─────┬───────────────────────────────────────┘
      │ 실패 ↓
┌─────▼───────────────────────────────────────┐
│ 2. API/GraphQL 캡처                         │
│    • 네트워크 요청 모니터링                  │
│    • /api/, /graphql 엔드포인트 추출        │
└─────┬───────────────────────────────────────┘
      │ 실패 ↓
┌─────▼───────────────────────────────────────┐
│ 3. DOM 패턴 감지 (4가지)                    │
│    • Hash Routing → Function → A Link →    │
│      Static Toggle 순차 시도                │
└─────┬───────────────────────────────────────┘
      │ 실패 ↓
┌─────▼───────────────────────────────────────┐
│ 4. BFS 탐색 (폴백)                          │
│    • 반복 요소가 가장 많은 컨테이너 찾기    │
│    • 최소 3개 이상 항목 필요                │
└─────────────────────────────────────────────┘
```

## 🤖 Facet Mapper 동작 원리

직군 버튼을 자동으로 찾고 검증하는 시스템:

```python
# 1. 버튼 후보 탐지
keywords = ["IT", "Engineering", "Tech", "Developer", "개발"]
candidates = detect_buttons_with_keywords(keywords)

# 2. 검증 루프
for button in candidates:
    before_hash = hash(current_job_list)  # 클릭 전
    click(button)
    after_hash = hash(current_job_list)   # 클릭 후
    
    if before_hash != after_hash:
        # 유효한 필터 버튼!
        capture_network_params()
        save_to_profile()
```

## 📊 데이터 플로우

```
사이트 페이지
    ↓
[Playwright 네트워크 캡처]
    ↓
[Pattern Detector] → 패턴 감지
    ↓
[Handler] → 공고 수집 (원문)
    ↓
[Extractor] → HTML/JSON 파싱
    ↓                  ↓
[원문 저장]    [표준화 변환]
    ↓                  ↓
         [IT Classifier]
         • Rule-based (키워드)
         • Model-based (ML)
              ↓
        [it_label 결정]
              ↓
      [PostgreSQL 저장]
      • 원문 + 표준화
      • 프로비넌스
      • 분류 근거
```

## 🗄️ 데이터베이스 스키마

### 핵심 설계 원칙

1. **원문 보존**: 사이트 원본 데이터 그대로 저장
2. **표준화 레이어**: 정규화된 필드 별도 관리
3. **프로비넌스**: 수집 경로 완전 추적
4. **분류 근거**: IT 판단 근거 JSON으로 저장

### 주요 필드 그룹

| 그룹 | 필드 예시 | 목적 |
|------|-----------|------|
| 식별/출처 | domain, source_url, canonical_job_id | 중복 방지 |
| 원문 | job_title_raw, detail_html, detail_json | 원본 데이터 |
| 표준화 | title, post_date, location_country | 쿼리/분석용 |
| IT 분류 | it_label, label_confidence, label_evidence | 분류 결과 |
| 프로비넌스 | pattern_detected, api_endpoint, selectors_used | 수집 메타 |

## 🔍 IT 분류 알고리즘

### Rule-based Classifier

```python
점수 = (
    사이트_카테고리_매칭 * 3.0 +  # 가중치 높음
    제목_키워드_매칭 * 2.0 +
    스킬_키워드_매칭 * 2.5 +
    부서명_매칭 * 1.0 -
    제외_키워드_패널티
)

confidence = 점수 / 최대_점수
it_label = confidence >= 0.3  # Threshold
```

### IT 키워드 예시

**포함 키워드**:
- 제목: 개발자, developer, engineer, programmer, 소프트웨어, frontend, backend
- 스킬: Python, Java, React, AWS, Docker, Kubernetes
- 카테고리: IT, Engineering, Tech, 기술

**제외 키워드**:
- 영업, sales, 마케팅, marketing, 인사, HR, 회계, finance

## 🛡️ 안정성 및 예외 처리

### 1. robots.txt 준수
```python
checker = RobotsChecker(base_url)
if checker.can_fetch(url):
    crawl(url)
```

### 2. 요청 제한
- 랜덤 지연: 1-3초 (설정 가능)
- 지수 백오프: 실패 시 재시도 간격 증가
- Max retries: 3회 (기본값)

### 3. 네트워크 타임아웃
- 기본: 30초
- Playwright 페이지 로드: networkidle 대기

### 4. 중복 방지
- UNIQUE 제약: `(domain, canonical_job_id)`
- IntegrityError 핸들링

## 📈 확장 포인트

### 1. 새 핸들러 추가
```python
from src.handlers.base import BaseHandler

class CustomHandler(BaseHandler):
    def crawl(self, target_category, limit):
        # 커스텀 로직
        pass
```

### 2. 분류기 개선
```python
from src.classifier.rule_classifier import RuleClassifier

class EnhancedClassifier(RuleClassifier):
    IT_KEYWORDS = {
        # 키워드 확장
    }
```

### 3. Extractor 추가
```python
from src.extractors.html_extractor import HTMLExtractor

class AdvancedExtractor(HTMLExtractor):
    def extract(self):
        # 고급 추출 로직
        pass
```

## 🧪 테스트 전략

### Unit Tests
- 각 핸들러 독립 테스트
- Classifier 정확도 검증
- Extractor 파싱 검증

### Integration Tests
- 전체 파이프라인 테스트
- DB 저장/조회 테스트
- Profile 로드/저장 테스트

### E2E Tests (향후)
- 실제 사이트 크롤링
- 자동 프로파일링 검증
- IT 분류 정확도 측정

## 📦 배포 고려사항

### Docker 컨테이너화
```dockerfile
FROM python:3.11-slim
RUN playwright install-deps chromium
COPY requirements.txt .
RUN pip install -r requirements.txt
COPY . /app
WORKDIR /app
CMD ["python", "-m", "src.runner.cli"]
```

### 스케일링
- Worker 프로세스로 병렬 크롤링
- Redis Queue로 작업 분산
- Celery로 스케줄링

### 모니터링
- Prometheus 메트릭 수집
- Grafana 대시보드
- Sentry 에러 추적

## 🔮 향후 개선 방향

1. **ML 모델 통합**: 
   - BERT 기반 IT 직군 분류
   - 스킬 자동 추출 (NER)

2. **실시간 크롤링**:
   - WebSocket 지원
   - RSS/Atom 피드 구독

3. **데이터 품질**:
   - 자동 검증 파이프라인
   - 중복 제거 알고리즘 개선

4. **UI/대시보드**:
   - 크롤링 진행 상황 시각화
   - 프로파일 관리 인터페이스

## 📚 참고 자료

- Playwright 문서: https://playwright.dev/python/
- SQLAlchemy ORM: https://docs.sqlalchemy.org/
- Pydantic 검증: https://docs.pydantic.dev/
- Typer CLI: https://typer.tiangolo.com/
