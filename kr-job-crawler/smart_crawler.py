"""
OpenAI를 사용한 범용 채용공고 크롤러 (Selenium 지원)
- URL을 입력받아 OpenAI가 페이지 구조를 분석
- 동적으로 필요한 데이터 추출 위치 파악
- HTML 또는 Selenium으로 JavaScript 렌더링 처리
- API/HTML에서 공고별 상세 내용 크롤링
- DB에 저장

지원하는 사이트:
- Kakao careers (API 기반)
- Naver recruit (Selenium 렌더링)
- 기타 일반 웹사이트 (자동 감지)
"""

import sys
import os
import json
import uuid
import sqlite3
import hashlib
import time
import re
from datetime import datetime
from typing import Optional, Dict, Any, List

os.environ['PYTHONIOENCODING'] = 'utf-8'
sys.stdout.reconfigure(encoding='utf-8')

sys.path.insert(0, r'C:\Users\SKAX\Desktop\kr-job-crawler\kr-job-crawler')

from dotenv import load_dotenv
load_dotenv(override=True)

import httpx
from bs4 import BeautifulSoup
from openai import OpenAI

# Selenium 임포트 (필요시만 사용)
try:
    from selenium import webdriver
    from selenium.webdriver.common.by import By
    from selenium.webdriver.support.ui import WebDriverWait
    from selenium.webdriver.support import expected_conditions as EC
    from selenium.webdriver.chrome.options import Options
    SELENIUM_AVAILABLE = True
except ImportError:
    SELENIUM_AVAILABLE = False
    print("⚠️  Selenium not available. Install with: pip install selenium")

# OpenAI API 설정
client = OpenAI(api_key=os.getenv('OPENAI_API_KEY'))


# ============================================================================
# OpenAI를 사용한 페이지 구조 분석
# ============================================================================

def analyze_page_structure(url: str, html_content: str) -> Dict[str, Any]:
    """OpenAI가 페이지 구조를 분석하여 데이터 추출 방법 제시"""

    print(f"\n🤖 OpenAI 분석 중: {url}")

    # HTML의 처음 3000자를 전송 (더 많은 구조 정보 포함)
    sample_html = html_content[:3000]

    prompt = f"""
너는 HTML 웹페이지 분석 전문가다. 주어진 채용공고 페이지의 HTML을 분석하고 데이터 추출 위치를 정확하게 찾아줘.

URL: {url}

HTML 샘플:
```html
{sample_html}
```

다음을 JSON 형식으로 답변해줘:
{{
  "page_type": "개별공고 또는 목록",
  "api_endpoint": "API URL (없으면 null)",
  "selectors": {{
    "title": "직무명을 포함하는 CSS 선택자",
    "company": "회사명을 포함하는 CSS 선택자",
    "location": "위치를 포함하는 CSS 선택자",
    "introduction": "직무소개를 포함하는 CSS 선택자",
    "work_content": "직무설명을 포함하는 CSS 선택자",
    "qualification": "자격요건을 포함하는 CSS 선택자",
    "work_condition": "근무조건을 포함하는 CSS 선택자",
    "recruitment_process": "채용절차를 포함하는 CSS 선택자",
    "skills": "기술스택을 포함하는 CSS 선택자"
  }},
  "fields": {{
    "title": "API 응답에서 직무명 필드",
    "company": "API 응답에서 회사명 필드",
    "location": "API 응답에서 위치 필드",
    "introduction": "API 응답에서 소개 필드",
    "work_content": "API 응답에서 직무설명 필드",
    "qualification": "API 응답에서 자격요건 필드",
    "work_condition": "API 응답에서 근무조건 필드",
    "recruitment_process": "API 응답에서 채용절차 필드",
    "skills": "API 응답에서 기술스택 필드"
  }}
}}

반드시 유효한 JSON만 답변해줘.
    """

    try:
        response = client.chat.completions.create(
            model="gpt-4",
            messages=[
                {"role": "system", "content": "You are a web scraping expert. Always respond with valid JSON only."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.3,
            max_tokens=1500
        )

        result_text = response.choices[0].message.content

        # JSON 추출
        try:
            # ```json ... ``` 형식 제거
            if '```json' in result_text:
                result_text = result_text.split('```json')[1].split('```')[0]
            elif '```' in result_text:
                result_text = result_text.split('```')[1].split('```')[0]

            result = json.loads(result_text)
            print(f"✅ 페이지 구조 분석 완료")
            return result

        except json.JSONDecodeError as e:
            print(f"❌ JSON 파싱 오류: {str(e)}")
            return {"error": "Failed to parse OpenAI response"}

    except Exception as e:
        print(f"❌ OpenAI API 오류: {str(e)}")
        return {"error": str(e)}


# ============================================================================
# 크롤링 함수
# ============================================================================

def fetch_page(url: str, use_selenium: bool = False) -> Optional[str]:
    """웹페이지 HTML 가져오기 (httpx 또는 Selenium)"""
    if use_selenium:
        return fetch_page_with_selenium(url)
    else:
        return fetch_page_with_httpx(url)


def fetch_page_with_httpx(url: str) -> Optional[str]:
    """httpx를 사용한 정적 HTML 다운로드"""
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }
        response = httpx.get(url, headers=headers, follow_redirects=True, timeout=30)
        response.raise_for_status()
        return response.text
    except Exception as e:
        print(f"   ❌ httpx 다운로드 실패: {str(e)}")
        return None


def fetch_page_with_selenium(url: str, wait_time: int = 10, return_driver: bool = False) -> tuple:
    """Selenium을 사용한 JavaScript 렌더링된 페이지 다운로드

    Args:
        url: 크롤링할 URL
        wait_time: 최대 대기 시간 (초)
        return_driver: driver를 반환할지 여부 (True면 (html, driver) 반환, False면 html만 반환)

    Returns:
        return_driver=False: Optional[str] (HTML)
        return_driver=True: Tuple[Optional[str], Optional[WebDriver]] (HTML, driver)
    """
    if not SELENIUM_AVAILABLE:
        print(f"   ❌ Selenium 미설치. pip install selenium 실행 후 다시 시도해주세요.")
        if return_driver:
            return None, None
        return None

    driver = None
    try:
        print(f"   🌐 Selenium으로 JavaScript 렌더링 중... (최대 {wait_time}초)")

        # Chrome 옵션 설정
        chrome_options = Options()
        chrome_options.add_argument("--headless")  # 브라우저 창 표시 안함
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        chrome_options.add_argument("--disable-blink-features=AutomationControlled")
        chrome_options.add_argument('user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36')

        driver = webdriver.Chrome(options=chrome_options)
        driver.get(url)

        # 페이지 로딩 대기 (최대 wait_time초)
        time.sleep(3)  # 기본 대기

        # 특정 요소 대기 (최대 wait_time초)
        try:
            WebDriverWait(driver, wait_time).until(
                EC.presence_of_any_elements_located((By.CSS_SELECTOR, "body *"))
            )
        except:
            pass  # 타임아웃 무시하고 진행

        html = driver.page_source
        print(f"   ✅ Selenium 렌더링 완료 (크기: {len(html)/1024:.1f}KB)")

        if return_driver:
            return html, driver
        else:
            driver.quit()
            return html

    except Exception as e:
        print(f"   ❌ Selenium 렌더링 실패: {str(e)}")
        if return_driver:
            return None, None
        return None
    finally:
        if driver and not return_driver:
            driver.quit()


def extract_data_from_html(html: str, selectors: Dict[str, str]) -> Dict[str, Any]:
    """CSS 선택자를 사용하여 HTML에서 데이터 추출"""
    soup = BeautifulSoup(html, 'html.parser')
    data = {}

    for field, selector in selectors.items():
        try:
            if selector is None:
                data[field] = None
                continue

            element = soup.select_one(selector)
            if element:
                text = element.get_text(strip=True)
                data[field] = text[:500] if len(text) > 500 else text
            else:
                data[field] = None
        except Exception as e:
            data[field] = None

    return data


def extract_naver_job_data(html: str, driver=None) -> Optional[Dict[str, Any]]:
    """Naver 채용공고에서 데이터 추출 (AI 기반 유연한 추출)"""
    try:
        soup = BeautifulSoup(html, 'html.parser')

        # 1단계: JSON-LD 데이터 추출 (기본 정보)
        json_ld_script = soup.find('script', {'type': 'application/ld+json'})
        json_data = {}

        if json_ld_script:
            try:
                data = json.loads(json_ld_script.string)
                if isinstance(data, list):
                    job_data = next((item for item in data if item.get('@type') == 'JobPosting'), None)
                else:
                    job_data = data if data.get('@type') == 'JobPosting' else None

                if job_data:
                    json_data = {
                        'title': job_data.get('title'),
                        'company': job_data.get('hiringOrganization', {}).get('name') if isinstance(job_data.get('hiringOrganization'), dict) else job_data.get('hiringOrganization'),
                        'location': job_data.get('jobLocation', {}).get('address', {}).get('addressLocality') if isinstance(job_data.get('jobLocation'), dict) else job_data.get('jobLocation'),
                        'work_condition': job_data.get('employmentType'),
                    }
            except:
                pass

        # 2단계: 페이지 전체 텍스트 추출
        page_text = soup.get_text()

        # 3단계: 기본 정보 준비
        basic_info = {
            'title': json_data.get('title'),
            'company': json_data.get('company') or 'NAVER',
            'location': json_data.get('location'),
            'work_condition': json_data.get('work_condition'),
            'skills': extract_skills_from_text(page_text)
        }

        # 4단계: AI를 사용하여 모든 섹션 데이터 추출 (형식 불일관성 대응)
        # 정규식 제거 → AI 기반으로 변경 (한글/영문 모두 지원)
        extracted = extract_all_fields_with_ai(page_text, basic_info)

        return extracted

    except Exception as e:
        print(f"   ❌ Naver 데이터 추출 실패: {str(e)}")
        return None


def extract_by_regex(text: str, pattern: str, multiline: bool = False) -> Optional[str]:
    """정규식으로 텍스트에서 정보 추출"""
    try:
        flags = re.MULTILINE | re.DOTALL if multiline else 0
        match = re.search(pattern, text, flags)
        if match:
            result = match.group(1) if match.lastindex else match.group(0)
            # 정제: 공백 제거, 너무 긴 텍스트 자르기
            result = result.strip()
            if len(result) > 1000:
                result = result[:1000] + "..."
            return result if result else None
        return None
    except:
        return None


def extract_skills_from_text(text: str) -> List[str]:
    """텍스트에서 기술 스택 추출"""
    skills_keywords = {
        'Python', 'Java', 'JavaScript', 'TypeScript', 'Go', 'Rust', 'C++', 'C#', 'PHP',
        'Kubernetes', 'Docker', 'AWS', 'GCP', 'Azure', 'Linux', 'Windows',
        'MySQL', 'PostgreSQL', 'MongoDB', 'Redis', 'Elasticsearch',
        'React', 'Vue', 'Angular', 'Node.js', 'Django', 'Flask',
        'Git', 'CI/CD', 'Jenkins', 'Terraform', 'Ansible',
        'REST API', 'gRPC', 'GraphQL', 'Microservices',
        'DevOps', 'SRE', 'Cloud', 'Infrastructure', 'Monitoring'
    }

    found_skills = []
    for skill in skills_keywords:
        if skill.lower() in text.lower():
            found_skills.append(skill)

    return found_skills if found_skills else []


def extract_all_fields_with_ai(page_text: str, basic_info: Dict[str, Any]) -> Dict[str, Any]:
    """
    AI를 사용하여 모든 필드를 원문에서 직접 추출 (형식 불일관성 대응)

    원칙:
    - 정규식 대신 AI로 유연하게 처리
    - 절대 거짓 정보를 생성하지 않음 (temperature=0)
    - 원문에서만 추출 (hallucination 방지)
    - 없는 정보는 None으로 반환

    Args:
        page_text: 전체 페이지 텍스트
        basic_info: 기본 정보 (title, company, work_condition, skills)

    Returns:
        완전히 추출된 데이터
    """

    try:
        print(f"   🤖 AI로 모든 필드 추출 중 (형식 불일관성 대응)...")

        # OpenAI API 호출
        prompt = f"""다음은 채용공고 페이지의 전체 텍스트입니다. 원문에서만 정보를 추출해줘.

중요:
- 원문에 없는 정보는 절대 만들지 말고, null로 반환해줘
- 한글과 영문 섹션 모두 지원해줘 (예: "Who We Are"도, "자격요건"도)
- 각 필드마다 원문의 관련 내용을 모두 포함해줘

## 전체 페이지 텍스트:
```
{page_text}
```

## 다음 필드들을 원문에서만 추출해줘:

1. **introduction** (회사/부서 소개)
   - "Who We Are", "회사 소개", "우리는", "About Us" 등의 섹션에서 추출
   - 회사나 부서의 철학, 비전, 역할 설명

2. **work_content** (주요 업무/담당 업무)
   - "What You'll Do", "주요 업무", "업무 내용", "담당 업무", "Job Responsibilities" 등에서 추출
   - 실제 수행할 업무 목록

3. **qualification** (필수 자격요건)
   - "Required Skills", "자격요건", "필수", "Requirements" 등에서 추출
   - 필수 경험, 기술, 자격

4. **recruitment_process** (채용 절차)
   - "면접 절차", "채용 절차", "Interview Process", "[전형절차]" 등에서 추출
   - 서류→면접→최종합격 같은 절차와 일정

## 응답 형식 (JSON):
{{
  "introduction": "회사 소개 텍스트 (없으면 null)",
  "work_content": "업무 내용 (없으면 null)",
  "qualification": "자격요건 (없으면 null)",
  "recruitment_process": "채용 절차 (없으면 null)"
}}

절대 거짓 정보를 만들지 말고, 원문에서만 추출해줘."""

        response = client.chat.completions.create(
            model="gpt-4-turbo",
            messages=[{"role": "user", "content": prompt}],
            temperature=0,  # 거짓 생성 완전 방지
            max_tokens=2000
        )

        result_text = response.choices[0].message.content

        # JSON 파싱
        result_json = {}
        try:
            # JSON 블록 추출
            json_match = re.search(r'\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\}', result_text, re.DOTALL)
            if json_match:
                result_json = json.loads(json_match.group(0))
            else:
                result_json = json.loads(result_text)
        except json.JSONDecodeError:
            print(f"   ⚠️  AI 응답 파싱 실패, 원문 분석 시도")
            # 파싱 실패 시 텍스트에서 직접 추출 시도
            pass

        # 기본 정보 + AI 추출 정보 통합
        extracted = {
            'title': basic_info.get('title'),
            'company': basic_info.get('company'),
            'location': basic_info.get('location'),
            'work_condition': basic_info.get('work_condition'),
            'skills': basic_info.get('skills'),
            'introduction': None,
            'work_content': None,
            'qualification': None,
            'recruitment_process': None
        }

        # AI 추출 결과 병합
        for field in ['introduction', 'work_content', 'qualification', 'recruitment_process']:
            if field in result_json and result_json[field]:
                value = str(result_json[field]).strip()
                if value.lower() != 'null' and len(value) > 20:  # 의미 있는 내용만
                    extracted[field] = value[:500]
                    print(f"      ✓ {field} 추출 ({len(value)} 자)")

        return extracted

    except Exception as e:
        print(f"   ⚠️  AI 추출 실패: {str(e)[:50]}")
        # 실패 시 기본 정보만 반환
        return {
            'title': basic_info.get('title'),
            'company': basic_info.get('company'),
            'location': basic_info.get('location'),
            'work_condition': basic_info.get('work_condition'),
            'skills': basic_info.get('skills'),
            'introduction': None,
            'work_content': None,
            'qualification': None,
            'recruitment_process': None
        }


def complete_missing_fields_with_ai(page_text: str, extracted_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    AI를 사용하여 정규식으로 추출 못한 필드를 원문에서만 추출 (보조 함수)
    """

    try:
        # 보완이 필요한 필드 확인
        missing_fields = [
            field for field in ['introduction', 'work_content', 'qualification', 'recruitment_process']
            if not extracted_data.get(field)
        ]

        if not missing_fields:
            return extracted_data  # 모든 필드가 있으면 그대로 반환

        print(f"   🤖 AI로 누락된 필드 보완 중: {', '.join(missing_fields)}")

        # extract_all_fields_with_ai 활용
        ai_extracted = extract_all_fields_with_ai(page_text, extracted_data)

        # 누락된 필드만 채우기
        for field in missing_fields:
            if ai_extracted.get(field):
                extracted_data[field] = ai_extracted[field]

        return extracted_data

    except Exception as e:
        print(f"   ⚠️  AI 보완 실패: {str(e)[:50]}")
        return extracted_data


def fetch_from_api(api_endpoint: str, params: Dict = None) -> Optional[List[Dict]]:
    """API에서 데이터 가져오기"""
    try:
        print(f"   📡 API 호출: {api_endpoint}")
        response = httpx.get(api_endpoint, params=params, timeout=30)
        response.raise_for_status()
        data = response.json()

        # 공고 리스트 추출 (다양한 구조 지원)
        if isinstance(data, list):
            print(f"   ✅ {len(data)}개 공고 조회 완료")
            return data
        elif 'data' in data:
            jobs = data['data'] if isinstance(data['data'], list) else [data['data']]
            print(f"   ✅ {len(jobs)}개 공고 조회 완료 (data 필드)")
            return jobs
        elif 'jobList' in data:
            print(f"   ✅ {len(data['jobList'])}개 공고 조회 완료 (jobList 필드)")
            return data['jobList']
        elif 'jobs' in data:
            print(f"   ✅ {len(data['jobs'])}개 공고 조회 완료 (jobs 필드)")
            return data['jobs']
        else:
            # 첫 번째 배열 필드 찾기
            for key, value in data.items():
                if isinstance(value, list) and len(value) > 0:
                    print(f"   ✅ {len(value)}개 공고 조회 완료 ({key} 필드)")
                    return value

        print(f"   ⚠️  API 응답에서 공고 리스트를 찾을 수 없음")
        return None
    except Exception as e:
        print(f"   ❌ API 호출 실패: {str(e)}")
        return None


# ============================================================================
# DB 함수
# ============================================================================

def init_db(db_path: str):
    """데이터베이스 초기화"""
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS job_postings (
            id TEXT PRIMARY KEY,
            domain VARCHAR(255) NOT NULL,
            job_id VARCHAR(500),
            title VARCHAR(1000),
            company VARCHAR(500),
            location VARCHAR(200),
            source_url TEXT,

            -- 정제된 상세 내용
            introduction TEXT,
            work_content TEXT,
            qualification TEXT,
            work_condition TEXT,
            recruitment_process TEXT,

            -- 기술 스택
            skills TEXT,

            -- 메타데이터
            raw_json TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    cursor.execute('CREATE INDEX IF NOT EXISTS idx_domain ON job_postings(domain)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_source_url ON job_postings(source_url)')

    conn.commit()
    cursor.close()
    conn.close()


def save_job(db_path: str, posting: Dict[str, Any]) -> bool:
    """공고 저장"""
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        cursor.execute('''
            INSERT OR REPLACE INTO job_postings (
                id, domain, job_id, title, company, location, source_url,
                introduction, work_content, qualification, work_condition,
                recruitment_process, skills, raw_json
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            posting.get('id'),
            posting.get('domain'),
            posting.get('job_id'),
            posting.get('title'),
            posting.get('company'),
            posting.get('location'),
            posting.get('source_url'),
            posting.get('introduction'),
            posting.get('work_content'),
            posting.get('qualification'),
            posting.get('work_condition'),
            posting.get('recruitment_process'),
            posting.get('skills'),
            posting.get('raw_json')
        ))

        conn.commit()
        cursor.close()
        conn.close()
        return True
    except sqlite3.IntegrityError as e:
        if 'UNIQUE constraint failed' in str(e):
            # job_id가 이미 존재하는 경우 - 이미 크롤링된 공고
            return False
        print(f"   ❌ DB 제약 조건 오류: {str(e)}")
        return False
    except Exception as e:
        print(f"   ❌ DB 저장 오류: {str(e)}")
        return False


# ============================================================================
# 메인 크롤러
# ============================================================================

def crawl_job_url(url: str, db_path: str = r'C:\Users\SKAX\Desktop\kr-job-crawler\kr-job-crawler\jobs.db'):
    """주어진 URL에서 채용공고 크롤링"""

    print("=" * 100)
    print(f"🚀 스마트 크롤러 시작: {url}")
    print("=" * 100)

    # 1. 페이지 다운로드 (httpx 먼저 시도)
    print(f"\n📥 페이지 다운로드 중...")
    html = fetch_page(url, use_selenium=False)

    use_selenium_fallback = False

    if not html:
        return

    # 2. 사이트 특수 처리
    if 'careers.kakao.com' in url:
        print(f"\n🔍 Kakao careers 페이지 감지 - Kakao API 사용")
        analysis = {
            'api_endpoint': 'https://careers.kakao.com/public/api/job-list',
            'fields': {
                'title': 'jobOfferTitle',
                'company': 'companyName',
                'location': 'locationName',
                'introduction': 'introduction',
                'work_content': 'workContentDesc',
                'qualification': 'qualification',
                'work_condition': 'workTypeDesc',
                'recruitment_process': 'jobOfferProcessDesc',
                'skills': 'skillSetList'
            }
        }
    elif 'recruit.navercorp.com' in url:
        print(f"\n🔍 Naver recruit 페이지 감지 - Selenium 렌더링 + 하이브리드 추출")
        use_selenium_fallback = True

        # Selenium으로 페이지 다시 다운로드 (driver 반환하도록 요청)
        print(f"\n📥 Selenium으로 JavaScript 렌더링된 페이지 다운로드...")
        html, driver = fetch_page_with_selenium(url, return_driver=True)

        if not html:
            print(f"❌ Naver 페이지 로드 실패")
            return

        # 하이브리드 방식으로 상세 데이터 추출 (JSON-LD + JavaScript + 정규식)
        print(f"\n📋 하이브리드 방식으로 데이터 추출 중 (JSON-LD + JavaScript + 정규식)...")
        naver_data = extract_naver_job_data(html, driver=driver)

        # driver 정리 (더 이상 필요 없음)
        if driver:
            driver.quit()
            driver = None

        if naver_data and naver_data.get('title'):
            print(f"✅ 하이브리드 추출 성공")
            # 직접 데이터 사용 (OpenAI 분석 스킵)
            analysis = None
        else:
            # 하이브리드 실패 시 OpenAI 분석
            print(f"⚠️  하이브리드 추출 실패. OpenAI로 분석 시도...")
            analysis = analyze_page_structure(url, html)
    else:
        # 3. OpenAI 분석 (일반 사이트)
        print(f"\n🤖 OpenAI로 페이지 구조 분석 중...")
        analysis = analyze_page_structure(url, html)

    # 분석 결과 정보
    if analysis is None:
        # Naver 하이브리드 직접 추출 경우
        print(f"\n📋 데이터 추출 방식: 하이브리드 (JSON-LD + JavaScript + 정규식)")
    elif "error" in analysis:
        print(f"❌ OpenAI 분석 실패")

        # OpenAI 분석 실패 시 Selenium 폴백
        if not use_selenium_fallback and SELENIUM_AVAILABLE:
            print(f"\n⚠️  OpenAI 분석 실패. Selenium으로 재시도 중...")
            html, driver = fetch_page_with_selenium(url, return_driver=True)
            if html:
                # Naver인 경우 하이브리드 방식으로 다시 시도
                if 'recruit.navercorp.com' in url:
                    naver_data = extract_naver_job_data(html, driver=driver)
                    if driver:
                        driver.quit()
                    if naver_data and naver_data.get('title'):
                        analysis = None
                    else:
                        analysis = analyze_page_structure(url, html)
                else:
                    if driver:
                        driver.quit()
                    analysis = analyze_page_structure(url, html)

                if analysis is None or "error" not in analysis:
                    use_selenium_fallback = True
                    print(f"✅ Selenium 재시도 성공")
                else:
                    print(f"❌ 재시도 실패")
                    return
            else:
                return
        else:
            return
    else:
        print(f"\n📋 분석 결과:")
        result_preview = json.dumps(analysis, ensure_ascii=False, indent=2)
        print(result_preview[:500] if len(result_preview) > 500 else result_preview)

    # 3. DB 초기화
    init_db(db_path)

    # 4. 데이터 추출
    saved_count = 0

    # Naver 하이브리드 직접 추출 경우 처리
    if analysis is None and 'recruit.navercorp.com' in url:
        print(f"\n🔄 하이브리드 방식에서 데이터 추출 중...")
        # JavaScript 실행을 위해 새로운 Selenium 드라이버 생성
        # (이전 드라이버는 이미 정리됨)
        print(f"   🔧 JavaScript 실행 재설정 중...")
        html_for_js, driver_for_js = fetch_page_with_selenium(url, return_driver=True)
        if html_for_js and driver_for_js:
            data = extract_naver_job_data(html_for_js, driver=driver_for_js)
            driver_for_js.quit()
        else:
            data = extract_naver_job_data(html)

        if data and data.get('title'):
            # job_id 생성 (URL 기반 해시)
            job_id = hashlib.md5(url.encode()).hexdigest()[:20]

            # skills 처리 (리스트 또는 문자열 → JSON 배열 문자열)
            skills = data.get('skills', [])
            if isinstance(skills, str):
                skills = [skills] if skills else []
            elif isinstance(skills, list):
                # 리스트의 각 항목이 딕셔너리인 경우 처리
                skills = [s.get('name', str(s)) if isinstance(s, dict) else str(s) for s in skills if s]
            else:
                skills = []

            # 데이터 정제 (모든 값을 문자열 또는 None으로 변환)
            def safe_str(val):
                if val is None:
                    return None
                if isinstance(val, (list, dict)):
                    return json.dumps(val, ensure_ascii=False)
                return str(val) if val else None

            posting = {
                'id': str(uuid.uuid4()),
                'domain': url.split('/')[2],
                'job_id': job_id,
                'source_url': url,
                'title': safe_str(data.get('title')) or 'Unknown',
                'company': safe_str(data.get('company')),
                'location': safe_str(data.get('location')),
                'introduction': safe_str(data.get('introduction')),
                'work_content': safe_str(data.get('work_content')),
                'qualification': safe_str(data.get('qualification')),
                'work_condition': safe_str(data.get('work_condition')),
                'recruitment_process': safe_str(data.get('recruitment_process')),
                'skills': json.dumps(skills, ensure_ascii=False),
                'raw_json': json.dumps(data, ensure_ascii=False)
            }

            # 필수 필드 확인
            if not posting['title'] or posting['title'] == 'Unknown':
                print(f"❌ 제목을 찾을 수 없습니다.")
                return

            if save_job(db_path, posting):
                saved_count += 1
                print(f"   ✓ {posting.get('title', 'Unknown')[:50]}")
            else:
                print(f"⚠️  공고 저장 실패 (이미 존재할 수 있음)")
        else:
            print(f"❌ JSON-LD 데이터를 찾을 수 없습니다.")
            print(f"   수집된 데이터: {data}")

    elif analysis and analysis.get('api_endpoint'):
        print(f"\n🔄 API에서 데이터 추출 중...")
        jobs = fetch_from_api(analysis['api_endpoint'])

        if jobs:
            for job in jobs:
                # OpenAI가 제시한 필드명 매핑
                # job_id 생성 (API 응답의 id 필드 또는 URL 기반)
                job_id = job.get('id') or job.get('jobId') or job.get('job_id') or \
                         hashlib.md5(str(job).encode()).hexdigest()[:20]

                fields = analysis.get('fields', {})
                title = job.get(fields.get('title')) if fields.get('title') else None

                # title이 없으면 건너뛰기
                if not title:
                    continue

                posting = {
                    'id': str(uuid.uuid4()),
                    'domain': url.split('/')[2],
                    'job_id': str(job_id),
                    'source_url': url,
                    'title': title,
                    'company': job.get(fields.get('company')),
                    'location': job.get(fields.get('location')),
                    'introduction': job.get(fields.get('introduction')),
                    'work_content': job.get(fields.get('work_content')),
                    'qualification': job.get(fields.get('qualification')),
                    'work_condition': job.get(fields.get('work_condition')),
                    'recruitment_process': job.get(fields.get('recruitment_process')),
                    'skills': json.dumps(job.get(fields.get('skills'), [])),
                    'raw_json': json.dumps(job, ensure_ascii=False)
                }

                if save_job(db_path, posting):
                    saved_count += 1
                    print(f"   ✓ {posting.get('title', 'Unknown')[:50]}")

    else:
        # HTML 파싱으로 추출
        print(f"\n🔄 HTML에서 데이터 추출 중...")
        selectors = analysis.get('selectors', {})
        data = extract_data_from_html(html, selectors)

        # 필수 필드 확인
        if not data.get('title'):
            print(f"⚠️  제목을 찾을 수 없습니다. CSS 선택자를 확인해주세요.")
            print(f"📍 분석된 선택자: {selectors}")
            return

        # job_id 생성 (URL 기반 해시)
        job_id = hashlib.md5(url.encode()).hexdigest()[:20]

        posting = {
            'id': str(uuid.uuid4()),
            'domain': url.split('/')[2],
            'job_id': job_id,
            'source_url': url,
            'title': data.get('title'),
            'company': data.get('company'),
            'location': data.get('location'),
            'introduction': data.get('introduction'),
            'work_content': data.get('work_content'),
            'qualification': data.get('qualification'),
            'work_condition': data.get('work_condition'),
            'recruitment_process': data.get('recruitment_process'),
            'skills': json.dumps(data.get('skills', [])),
            'raw_json': json.dumps(data, ensure_ascii=False)
        }

        if save_job(db_path, posting):
            saved_count += 1
            print(f"   ✓ {posting.get('title', 'Unknown')[:50]}")

    print(f"\n✅ {saved_count}개 공고 저장 완료")
    print(f"💾 DB: {db_path}")


# ============================================================================
# 배치 크롤링 (여러 URL)
# ============================================================================

def crawl_batch_urls(urls: List[str], db_path: str = r'C:\Users\SKAX\Desktop\kr-job-crawler\kr-job-crawler\jobs.db'):
    """여러 URL을 배치로 크롤링"""

    print("=" * 100)
    print(f"🚀 배치 크롤링 시작: {len(urls)}개 URL")
    print("=" * 100)

    total_saved = 0
    failed_urls = []

    for i, url in enumerate(urls, 1):
        try:
            print(f"\n[{i}/{len(urls)}] {url}")
            print("─" * 100)
            crawl_job_url(url, db_path)

        except Exception as e:
            print(f"❌ 크롤링 실패: {str(e)}")
            failed_urls.append((url, str(e)))

    # 최종 통계
    print("\n" + "=" * 100)
    print("📊 배치 크롤링 완료 통계")
    print("=" * 100)
    print(f"\n✓ 성공한 URL: {len(urls) - len(failed_urls)}/{len(urls)}")

    if failed_urls:
        print(f"\n❌ 실패한 URL: {len(failed_urls)}개")
        for url, error in failed_urls:
            print(f"   • {url}")
            print(f"     오류: {error[:80]}")


def read_urls_from_file(filename: str) -> List[str]:
    """파일에서 URL 읽기 (한 줄에 하나씩)"""
    try:
        with open(filename, 'r', encoding='utf-8') as f:
            urls = [line.strip() for line in f if line.strip() and line.strip().startswith('http')]
        return urls
    except FileNotFoundError:
        print(f"❌ 파일을 찾을 수 없습니다: {filename}")
        return []


# ============================================================================
# Naver 공채 리스트에서 annoId 추출
# ============================================================================

def extract_naver_job_ids(list_url: str = "https://recruit.navercorp.com/rcrt/list.do", max_pages: int = None) -> List[Dict[str, str]]:
    """
    네이버 공채 리스트 페이지에서 개별 공고의 annoId와 URL 추출 (페이지네이션 지원)

    Args:
        list_url: 네이버 공채 리스트 페이지 URL
        max_pages: 최대 크롤링 페이지 수 (None이면 모든 페이지)

    Returns:
        [{'title': '공고제목', 'annoId': '12345', 'url': '...'}, ...]
    """

    if not SELENIUM_AVAILABLE:
        print("❌ Selenium이 필요합니다: pip install selenium")
        return []

    options = Options()
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-dev-shm-usage')
    options.add_argument('--disable-gpu')
    options.add_argument('user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/120.0.0.0 Safari/537.36')

    driver = webdriver.Chrome(options=options)
    extracted_jobs = []
    page_num = 1

    try:
        print(f"📍 Naver 공채 리스트 크롤링 시작 (페이지네이션 지원)")
        print(f"   기본 URL: {list_url}")
        if max_pages:
            print(f"   최대 페이지: {max_pages}\n")
        else:
            print(f"   최대 페이지: 무제한\n")

        while True:
            # 페이지 URL 구성
            separator = '&' if '?' in list_url else '?'
            current_page_url = f"{list_url}{separator}page={page_num}" if page_num > 1 else list_url

            print(f"{'='*80}")
            print(f"📄 페이지 {page_num} 로드 중...")
            print(f"{'='*80}")

            driver.get(current_page_url)
            time.sleep(4)

            # 페이지에서 공고 제목 추출
            body_text = driver.find_element("tag name", "body").text
            lines = [line for line in body_text.split('\n') if line.strip()]
            job_titles = [line for line in lines if '[NAVER' in line]

            if not job_titles:
                print(f"⚠️  페이지 {page_num}에서 공고를 찾을 수 없습니다. 크롤링 종료.")
                break

            print(f"\n📋 페이지 {page_num} 공고: {len(job_titles)}개\n")

            for i, title in enumerate(job_titles, 1):
                print(f"   [{page_num}-{i}] {title}")

                try:
                    # 링크 찾기
                    element = driver.find_element(By.XPATH, f"//a[contains(., '{title.split('(')[0].strip()}')]")

                    # JavaScript로 클릭
                    driver.execute_script("arguments[0].click();", element)
                    time.sleep(3)

                    # 새 URL에서 annoId 추출
                    new_url = driver.current_url
                    match = re.search(r'annoId=(\d+)', new_url)

                    if match:
                        anno_id = match.group(1)
                        extracted_jobs.append({
                            'title': title,
                            'annoId': anno_id,
                            'url': new_url
                        })
                        print(f"         ✓ annoId: {anno_id}")

                    # 리스트로 돌아가기
                    driver.execute_script("window.history.back();")
                    time.sleep(2)

                except Exception as e:
                    print(f"         ❌ 오류: {str(e)[:50]}")

            # 페이지 수 제한 확인
            if max_pages and page_num >= max_pages:
                print(f"\n⚠️  최대 페이지({max_pages})에 도달했습니다.")
                break

            page_num += 1

        print(f"\n✅ {len(extracted_jobs)}/{len(job_titles)}개 추출 완료\n")

    finally:
        driver.quit()

    return extracted_jobs


def crawl_naver_list(db_path: str = r'C:\Users\SKAX\Desktop\kr-job-crawler\kr-job-crawler\jobs.db',
                     max_pages: int = None):
    """
    Naver 공채 리스트 페이지에서 모든 공고를 자동으로 크롤링 (페이지네이션 지원)

    Args:
        db_path: 데이터베이스 경로
        max_pages: 최대 크롤링 페이지 수 (None이면 모든 페이지)
    """

    print("=" * 100)
    print("🔗 Naver 공채 리스트 크롤링 시작 (페이지네이션 지원)")
    print("=" * 100)

    # 리스트에서 annoId 추출 (페이지네이션 포함)
    jobs = extract_naver_job_ids(max_pages=max_pages)

    if not jobs:
        print("❌ 추출할 공고가 없습니다")
        return

    # 각 공고의 상세 페이지 크롤링
    print("\n" + "=" * 100)
    print(f"📄 {len(jobs)}개 공고의 상세 페이지 크롤링 시작")
    print("=" * 100)

    saved_count = 0
    failed_count = 0

    for i, job in enumerate(jobs, 1):
        try:
            print(f"\n[{i}/{len(jobs)}] {job['title']}")
            print(f"   annoId: {job['annoId']}")
            crawl_job_url(job['url'], db_path)
            saved_count += 1

        except Exception as e:
            print(f"   ❌ 크롤링 실패: {str(e)[:60]}")
            failed_count += 1

    # 최종 통계
    print("\n" + "=" * 100)
    print("📊 Naver 공채 크롤링 완료")
    print("=" * 100)
    print(f"\n✓ 성공: {saved_count}개")
    if failed_count > 0:
        print(f"✗ 실패: {failed_count}개")
    print(f"💾 DB: {db_path}")


if __name__ == "__main__":
    # 사용 예시
    # python smart_crawler.py "https://careers.kakao.com/jobs/P-14207"
    # python smart_crawler.py --batch urls.txt
    # python smart_crawler.py --naver-list
    # python smart_crawler.py --naver-list --max-pages 3

    if len(sys.argv) > 1:
        if sys.argv[1] == "--batch" and len(sys.argv) > 2:
            # 배치 모드: URL 파일 읽기
            filename = sys.argv[2]
            urls = read_urls_from_file(filename)
            if urls:
                crawl_batch_urls(urls)
            else:
                print("사용법: python smart_crawler.py --batch <파일명>")
                print("파일 형식: 한 줄에 하나씩 URL 입력")
        elif sys.argv[1] == "--naver-list":
            # Naver 공채 리스트 크롤링 (페이지네이션 지원)
            max_pages = None

            # --max-pages 옵션 확인
            if len(sys.argv) > 2 and sys.argv[2] == "--max-pages" and len(sys.argv) > 3:
                try:
                    max_pages = int(sys.argv[3])
                except ValueError:
                    print("⚠️  --max-pages 값이 올바른 숫자가 아닙니다.")

            crawl_naver_list(max_pages=max_pages)
        else:
            # 단일 URL 모드
            url = sys.argv[1]
            crawl_job_url(url)
    else:
        print("=" * 100)
        print("🚀 스마트 크롤러 - 사용법")
        print("=" * 100)
        print("\n1️⃣  단일 URL 크롤링:")
        print("   python smart_crawler.py <URL>")
        print("   예: python smart_crawler.py https://careers.kakao.com/jobs/P-14207")
        print("\n2️⃣  배치 크롤링 (여러 URL):")
        print("   python smart_crawler.py --batch <파일명>")
        print("   예: python smart_crawler.py --batch urls.txt")
        print("\n3️⃣  Naver 공채 전체 크롤링 (페이지네이션 지원):")
        print("   python smart_crawler.py --naver-list")
        print("   (리스트 페이지에서 모든 공고를 자동으로 추출하여 크롤링)")
        print("\n   페이지 수 제한:")
        print("   python smart_crawler.py --naver-list --max-pages 3")
        print("   (처음 3페이지만 크롤링)")
        print("\n   urls.txt 형식:")
        print("   https://careers.kakao.com/jobs/P-14207")
        print("   https://recruit.navercorp.com/rcrt/view.do?annoId=30004125&lang=ko")
        print("   https://recruit.navercorp.com/rcrt/view.do?annoId=30004126&lang=ko")
        print("=" * 100)
