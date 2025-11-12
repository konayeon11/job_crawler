#!/usr/bin/env python3
"""
쿠팡 채용사이트 크롤러
https://www.coupang.jobs/kr/jobs/ 의 채용공고를 수집하고 정보를 추출합니다.
"""

import argparse
import json
import os
import time
import re
import sys
from pathlib import Path
from typing import List, Dict, Optional
from datetime import datetime
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup

# Windows 환경에서 UTF-8 출력 지원
if sys.platform == 'win32':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

# CloudFlare 우회를 위한 라이브러리 선택적 임포트
try:
    import cloudscraper
    HAS_CLOUDSCRAPER = True
except ImportError:
    HAS_CLOUDSCRAPER = False


class CoupangJobCrawler:
    """쿠팡 채용공고 크롤러"""

    def __init__(self, delay: float = 2.0, max_retries: int = 3, location: Optional[str] = None):
        """
        Args:
            delay: 페이지 요청 간 대기 시간 (초)
            max_retries: 최대 재시도 횟수
            location: 위치 필터 (예: "South Korea", "Seoul")
        """
        self.delay = delay
        self.max_retries = max_retries
        self.location = location

        # CloudScraper 또는 일반 requests 세션 사용
        if HAS_CLOUDSCRAPER:
            try:
                self.session = cloudscraper.create_scraper()
                print("  ℹ️  CloudScraper를 사용하여 CloudFlare 우회 중...")
            except Exception as e:
                print(f"  ⚠️  CloudScraper 초기화 실패: {e}")
                self.session = requests.Session()
        else:
            self.session = requests.Session()

        # 한국어 헤더 설정
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept-Language': 'ko-KR,ko;q=0.9,en-US;q=0.8,en;q=0.7',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Encoding': 'gzip, deflate, br',
            'DNT': '1',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
            'Sec-Fetch-Dest': 'document',
            'Sec-Fetch-Mode': 'navigate',
            'Sec-Fetch-Site': 'none',
            'Cache-Control': 'max-age=0',
        })

        # 위치 필터를 포함한 base URL 설정
        if location:
            # URL 인코딩 처리 (공백을 %20으로 변환, +로 표현된 공백도 처리)
            location_encoded = location.replace(' ', '%20').replace('+', '%2B')
            # search 파라미터도 포함하여 쿠팡 형식에 맞추기
            self.base_url = f"https://www.coupang.jobs/kr/jobs/?search=&location={location_encoded}&pagesize=20"
        else:
            self.base_url = "https://www.coupang.jobs/kr/jobs/"

    def _make_request(self, url: str, timeout: int = 15) -> Optional[requests.Response]:
        """
        재시도 로직과 함께 HTTP 요청 수행

        Args:
            url: 요청할 URL
            timeout: 타임아웃 (초)

        Returns:
            Response 객체 또는 None
        """
        headers = self.session.headers.copy()
        headers['Referer'] = self.base_url

        for attempt in range(self.max_retries):
            try:
                response = self.session.get(
                    url,
                    timeout=timeout,
                    headers=headers,
                    allow_redirects=True
                )

                if response.status_code == 200:
                    response.encoding = 'utf-8'
                    return response
                elif response.status_code == 429:  # Too Many Requests
                    wait_time = min(2 ** attempt, 10)
                    print(f"    ⏸  Rate limit - {wait_time}초 대기")
                    time.sleep(wait_time)
                elif response.status_code in [403, 404]:
                    return None
                else:
                    if attempt < self.max_retries - 1:
                        wait_time = 2 ** attempt
                        print(f"    ⏸  HTTP {response.status_code} - {wait_time}초 후 재시도")
                        time.sleep(wait_time)

            except requests.exceptions.Timeout:
                if attempt < self.max_retries - 1:
                    wait_time = 2 ** attempt
                    print(f"    ⏸  타임아웃 - {wait_time}초 후 재시도")
                    time.sleep(wait_time)
            except requests.exceptions.RequestException as e:
                if attempt < self.max_retries - 1:
                    wait_time = 2 ** attempt
                    print(f"    ⏸  요청 실패 - {wait_time}초 후 재시도")
                    time.sleep(wait_time)

        return None

    def is_korea_job(self, title: str, content: str) -> bool:
        """
        채용공고가 한국 채용인지 판단

        Args:
            title: 공고 제목
            content: 공고 본문

        Returns:
            한국 채용 여부
        """
        # 한국 채용 키워드
        korea_keywords = ['Seoul', '서울', 'Korea', '한국', '대한민국', 'KR']

        # 해외 채용 키워드 (제외)
        overseas_keywords = [
            'USA', 'US ', 'United States', 'Mountain View', 'New York', 'California',
            'Canada', 'Japan', '일본', 'Singapore', '싱가포르', 'India', '인도',
            'Bengaluru', 'UK', 'London', 'Germany', 'Europe', 'Taiwan', '대만',
            'Vietnam', '베트남', 'Thailand', '태국'
        ]

        combined_text = (title + ' ' + content).lower()

        # 해외 키워드가 있으면 False
        for keyword in overseas_keywords:
            if keyword.lower() in combined_text:
                return False

        # 한국 키워드가 있으면 True
        for keyword in korea_keywords:
            if keyword.lower() in combined_text:
                return True

        return False

    def _is_contract_position(self, title: str, employment_type: str) -> bool:
        """
        채용공고가 계약직인지 판단

        Args:
            title: 공고 제목
            employment_type: 고용형태

        Returns:
            계약직 여부
        """
        contract_keywords = ['계약직', 'contract', '계약', '임시직', 'temporary']

        combined_text = (title + ' ' + employment_type).lower()

        for keyword in contract_keywords:
            if keyword.lower() in combined_text:
                return True

        return False

    def _find_max_page(self) -> int:
        """
        마지막 페이지 번호를 이진 탐색으로 찾음

        Returns:
            마지막 페이지 번호
        """
        low, high = 1, 100
        last_valid = 1

        while low <= high:
            mid = (low + high) // 2

            # mid 페이지 확인
            if self.location:
                test_url = f"{self.base_url}&page={mid}"
            else:
                test_url = f"{self.base_url}?page={mid}"

            response = self._make_request(test_url)
            if response:
                soup = BeautifulSoup(response.content, 'html.parser')
                jobs = len(soup.find_all('a', href=lambda x: x and 'gh_jid=' in str(x)))

                if jobs > 0:
                    last_valid = mid
                    low = mid + 1
                else:
                    high = mid - 1
            else:
                high = mid - 1

        return last_valid

    def get_job_links(self, korea_only: bool = False) -> List[str]:
        """
        채용공고 링크 수집 (모든 페이지에서)

        Args:
            korea_only: 한국 채용만 수집 여부 (location 필터 사용 시 무시됨)

        Returns:
            채용공고 링크 리스트
        """
        print(f"📄 채용공고 목록 페이지 접속: {self.base_url}")

        try:
            job_links = []
            seen_urls = set()

            # location 필터가 설정된 경우 모든 페이지 크롤링
            if self.location:
                print(f"📍 위치 필터: {self.location}")

                # 최대 페이지 찾기
                max_page = self._find_max_page()
                print(f"✅ 최대 페이지: {max_page}개 발견")

                # 모든 페이지 크롤링
                for page_num in range(1, max_page + 1):
                    page_url = f"{self.base_url}&page={page_num}" if page_num > 1 else self.base_url
                    response = self._make_request(page_url)

                    if not response:
                        print(f"  ⚠️  페이지 {page_num} 접속 실패")
                        continue

                    soup = BeautifulSoup(response.content, 'html.parser')
                    elements = soup.select('a[href*="/jobs/"]')

                    page_jobs = 0
                    for element in elements:
                        href = element.get('href', '').strip()

                        if not href:
                            continue

                        # 절대 URL로 변환
                        if href.startswith('/'):
                            href = urljoin(self.base_url, href)
                        elif not href.startswith('http'):
                            href = urljoin(self.base_url, href)

                        # URL 필터링
                        has_job_id = 'gh_jid=' in href or re.search(r'/jobs/\d+', href)

                        if (href and '/jobs/' in href
                            and href not in seen_urls
                            and has_job_id
                            and 'saved' not in href.lower()):

                            job_links.append(href)
                            seen_urls.add(href)
                            page_jobs += 1

                    print(f"  📄 페이지 {page_num}: {page_jobs}개 공고 수집")
                    time.sleep(self.delay)

            else:
                # location 필터가 없는 경우 (원래 방식)
                response = self._make_request(self.base_url)
                if not response:
                    print(f"  ❌ 페이지 접속 실패")
                    return []

                soup = BeautifulSoup(response.content, 'html.parser')
                elements = soup.select('a[href*="/jobs/"]')
                print(f"  🔍 선택자에서 {len(elements)}개 요소 발견")

                for element in elements:
                    href = element.get('href', '').strip()

                    if not href:
                        continue

                    # 절대 URL로 변환
                    if href.startswith('/'):
                        href = urljoin(self.base_url, href)
                    elif not href.startswith('http'):
                        href = urljoin(self.base_url, href)

                    # URL 필터링
                    has_job_id = 'gh_jid=' in href or re.search(r'/jobs/\d+', href)

                    if (href and '/jobs/' in href
                        and href not in seen_urls
                        and href != self.base_url
                        and not href.endswith('/jobs/')
                        and not href.endswith('/jobs')
                        and '저장된' not in href
                        and 'saved' not in href.lower()
                        and has_job_id):

                        job_links.append(href)
                        seen_urls.add(href)

            # 중복 제거
            job_links = list(dict.fromkeys(job_links))

            print(f"✅ 총 {len(job_links)}개의 채용공고 링크 수집")
            if job_links:
                print(f"   예시: {job_links[0]}")

            return job_links

        except Exception as e:
            print(f"❌ 링크 수집 실패: {str(e)}")
            return []

    def extract_job_details(self, url: str) -> Dict:
        """
        채용공고 상세 정보 추출

        Args:
            url: 채용공고 URL

        Returns:
            채용공고 정보 딕셔너리
        """
        job_data = {
            'url': url,
            'title': '',
            'posting_date': '',
            'closing_date': '',
            'location': '',
            'employment_type': '',
            'company_description': '',
            'team_description': '',
            'job_description': '',
            'required_qualifications': '',
            'preferred_qualifications': '',
            'recruitment_schedule': '',
            'selection_process': '',
            'notes': '',
            'privacy_policy': '',
            'document_return_policy': '',
            'content': '',
            'crawled_at': datetime.now().isoformat(),
        }

        response = self._make_request(url)
        if not response:
            print(f"  ❌ 페이지 접속 실패")
            return job_data

        try:
            soup = BeautifulSoup(response.content, 'html.parser')

            # 페이지 제목
            title_tag = soup.find('title')
            if title_tag:
                job_data['title'] = title_tag.get_text().strip()

            # article.cms-content에서 본문 크롤링
            content_element = soup.find('article', class_='cms-content')
            if content_element:
                job_data['content'] = content_element.get_text(separator='\n', strip=True)
                print(f"  ✅ article.cms-content에서 본문 크롤링 ({len(job_data['content'])} 글자)")
            else:
                # 대안: main 또는 body 전체 텍스트 수집
                main_element = soup.find('main')
                if main_element:
                    job_data['content'] = main_element.get_text(separator='\n', strip=True)
                    print(f"  ✅ main 요소에서 본문 크롤링 ({len(job_data['content'])} 글자)")
                else:
                    body = soup.find('body')
                    if body:
                        job_data['content'] = body.get_text(separator='\n', strip=True)
                        print(f"  ✅ body 요소에서 본문 크롤링 ({len(job_data['content'])} 글자)")

            # HTML에서 직접 날짜 정보 크롤링
            self._extract_dates_from_html(soup, job_data)

            # 메타 정보 추출
            self._extract_metadata(soup, job_data)

            # 섹션별 파싱
            self._parse_job_sections(job_data)

            if job_data['title']:
                print(f"  ✅ 공고 제목: {job_data['title'][:60]}...")
            else:
                print(f"  ⚠️  공고 제목을 찾을 수 없습니다")

        except Exception as e:
            print(f"  ❌ 크롤링 실패: {str(e)}")

        return job_data

    def _extract_dates_from_html(self, soup: BeautifulSoup, job_data: Dict):
        """
        HTML과 content에서 공고 시작일과 마감일을 크롤링
        content 내용에서 날짜 정보 추출
        """
        try:
            # HTML 메타데이터 확인
            all_text = soup.get_text()

            # 패턴 정의
            date_patterns = {
                'posting_date': [
                    r'공고게시일[:\s]+(\d{4}[.\-]\d{1,2}[.\-]\d{1,2})',
                    r'공고게시일[:\s]+(\d{4}년\s*\d{1,2}월\s*\d{1,2}일)',
                    r'Posted[:\s]+([A-Za-z]+\s+\d{1,2},\s*\d{4})',
                ],
                'closing_date': [
                    r'마감일[:\s]+(\d{4}[.\-]\d{1,2}[.\-]\d{1,2})',
                    r'마감일[:\s]+(\d{4}년\s*\d{1,2}월\s*\d{1,2}일)',
                    r'접수마감[:\s]+(\d{4}[.\-]\d{1,2}[.\-]\d{1,2})',
                    r'접수마감[:\s]+(\d{4}년\s*\d{1,2}월\s*\d{1,2}일)',
                    r'Deadline[:\s]+([A-Za-z]+\s+\d{1,2},\s*\d{4})',
                    r'마감[:\s]+(\d{4}[.\-]\d{1,2}[.\-]\d{1,2})',
                    r'~\s*(\d{4}[.\-]\d{1,2}[.\-]\d{1,2})',  # ~로 표시된 마감일
                ],
            }

            for date_field, patterns in date_patterns.items():
                if not job_data[date_field]:
                    for pattern in patterns:
                        match = re.search(pattern, all_text)
                        if match:
                            date_value = match.group(1).strip()
                            date_value = self._normalize_date_format(date_value)
                            if date_value:
                                job_data[date_field] = date_value
                            break

            # content에서도 날짜 찾기 (2번 호출되는 것 방지하기 위해 content 확인)
            if job_data['content']:
                self._extract_dates_from_content(job_data)

        except Exception as e:
            # 날짜 추출 실패는 무시
            pass

    def _extract_dates_from_content(self, job_data: Dict):
        """
        content 텍스트에서 채용 일정과 마감일 추출
        """
        if not job_data['content']:
            return

        content = job_data['content']

        # 공고게시일/마감일 추출
        posting_patterns = [
            r'공고게시일[:\s]*\n*([^\n]+)',
            r'공고게시[:\s]*\n*([^\n]+)',
        ]

        closing_patterns = [
            r'마감일[:\s]*\n*([^\n]+)',
            r'접수마감[:\s]*\n*([^\n]+)',
            r'채용\s*일정.*?(\d{4}[.\-]\d{1,2}[.\-]\d{1,2})',
        ]

        # 공고게시일 추출
        if not job_data['posting_date']:
            for pattern in posting_patterns:
                match = re.search(pattern, content)
                if match:
                    text = match.group(1).strip()
                    # 텍스트에서 날짜 추출
                    date_match = re.search(r'\d{4}[.\-]\d{1,2}[.\-]\d{1,2}|\d{4}년\s*\d{1,2}월\s*\d{1,2}일', text)
                    if date_match:
                        date_value = self._normalize_date_format(date_match.group(0))
                        if date_value:
                            job_data['posting_date'] = date_value
                        break

        # 마감일 추출
        if not job_data['closing_date']:
            for pattern in closing_patterns:
                match = re.search(pattern, content, re.DOTALL)
                if match:
                    text = match.group(1).strip() if match.lastindex >= 1 else match.group(0)
                    date_match = re.search(r'\d{4}[.\-]\d{1,2}[.\-]\d{1,2}|\d{4}년\s*\d{1,2}월\s*\d{1,2}일', text)
                    if date_match:
                        date_value = self._normalize_date_format(date_match.group(0))
                        if date_value:
                            job_data['closing_date'] = date_value
                        break

    def _normalize_date_format(self, date_str: str) -> str:
        """
        다양한 날짜 형식을 YYYY-MM-DD로 통일
        """
        # 도트 형식: 2024.11.30 → 2024-11-30
        date_str = date_str.replace('.', '-')

        # 한글 년월일 형식: 2024년 11월 30일 → 2024-11-30
        if '년' in date_str and '월' in date_str and '일' in date_str:
            date_str = re.sub(r'(\d{4})년\s*(\d{1,2})월\s*(\d{1,2})일', r'\1-\2-\3', date_str)

        # 패딩 추가: 2024-1-5 → 2024-01-05
        parts = date_str.split('-')
        if len(parts) == 3:
            try:
                year = parts[0]
                month = parts[1].zfill(2)
                day = parts[2].zfill(2)
                return f"{year}-{month}-{day}"
            except:
                return date_str

        return date_str

    def _extract_metadata(self, soup: BeautifulSoup, job_data: Dict):
        """
        메타데이터 추출 (정보 카드/표에서)
        """
        try:
            content = job_data['content']

            if not content:
                return

            # 정규식으로 날짜, 위치, 고용형태 추출 시도
            patterns = {
                'posting_date': [
                    r'공고게시일[:\s]+(\d{4}-\d{2}-\d{2})',
                    r'공고게시일[:\s]+(\d{4}\.\d{2}\.\d{2})',
                    r'업데이트일[:\s]+(\d{4}-\d{2}-\d{2})',
                    r'업데이트일[:\s]+(\d{4}\.\d{2}\.\d{2})',
                    r'posted[:\s]+(\d{4}-\d{2}-\d{2})',
                    r'Posted[:\s]+([A-Za-z]+\s+\d{1,2},\s+\d{4})',
                ],
                'closing_date': [
                    r'마감일[:\s]+(\d{4}-\d{2}-\d{2})',
                    r'마감일[:\s]+(\d{4}\.\d{2}\.\d{2})',
                    r'마감[:\s]+(\d{4}-\d{2}-\d{2})',
                    r'마감[:\s]+(\d{4}\.\d{2}\.\d{2})',
                    r'closing[:\s]+(\d{4}-\d{2}-\d{2})',
                    r'Closing[:\s]+([A-Za-z]+\s+\d{1,2},\s+\d{4})',
                    r'Deadline[:\s]+([A-Za-z]+\s+\d{1,2},\s+\d{4})',
                ],
                'location': [
                    r'근무지역[:\s]*([가-힣\w\s,/]+?)(?:\n|$)',
                    r'근무지[:\s]*([가-힣\w\s,/]+?)(?:\n|$)',
                    r'지역[:\s]*([가-힣\w\s,/]+?)(?:\n|$)',
                    r'위치[:\s]*([가-힣\w\s,/]+?)(?:\n|$)',
                    r'(Seoul|서울|Incheon|인천|Busan|부산|Daegu|대구|Daejeon|대전|Gwangju|광주|Ulsan|울산)',
                ],
                'employment_type': [
                    r'고용형태[:\s]*([가-힣\w\s,]+?)(?:\n|$)',
                    r'근무형태[:\s]*([가-힣\w\s,]+?)(?:\n|$)',
                    r'근무형태[:\s]*([가-힣\w\s,]+?)(?:\n|$)',
                    r'(정규직|계약직|파트타임|상용직|인턴)',
                ],
            }

            for key, pattern_list in patterns.items():
                if not job_data[key]:
                    for pattern in pattern_list:
                        match = re.search(pattern, content, re.IGNORECASE)
                        if match:
                            value = match.group(1).strip()
                            if value:
                                job_data[key] = value
                                break

            # HTML 구조에서 테이블/리스트 추출
            tables = soup.find_all(['table', 'dl', 'div'])

            for table in tables:
                text = table.get_text()

                # 필수조건 추출
                if '필수' in text and not job_data['required_qualifications']:
                    lines = [line.strip() for line in text.split('\n') if line.strip()]
                    for i, line in enumerate(lines):
                        if '필수' in line or 'requirement' in line.lower():
                            end_idx = min(i + 6, len(lines))
                            job_data['required_qualifications'] = '\n'.join(lines[i:end_idx]).strip()
                            break

                # 우대조건 추출
                if '우대' in text and not job_data['preferred_qualifications']:
                    lines = [line.strip() for line in text.split('\n') if line.strip()]
                    for i, line in enumerate(lines):
                        if '우대' in line or 'preferred' in line.lower():
                            end_idx = min(i + 6, len(lines))
                            job_data['preferred_qualifications'] = '\n'.join(lines[i:end_idx]).strip()
                            break

            # 내용에서 섹션별 추출
            sections = {
                'job_description': ['직무소개', '주요 업무', '담당 업무', 'Job Description'],
                'company_description': ['회사소개', '기업소개', '쿠팡 소개', 'Company Info'],
            }

            for key, keywords in sections.items():
                if not job_data[key]:
                    for keyword in keywords:
                        if keyword in content:
                            start_idx = content.find(keyword)
                            # 다음 섹션까지의 텍스트 추출 (최대 800자)
                            next_section_idx = len(content)
                            for other_keywords in sections.values():
                                for word in other_keywords:
                                    if word != keyword:
                                        idx = content.find(word, start_idx + len(keyword))
                                        if idx > start_idx and idx < next_section_idx:
                                            next_section_idx = idx

                            section_text = content[start_idx:next_section_idx][:800].strip()
                            if section_text:
                                job_data[key] = section_text
                                break

        except Exception as e:
            # 메타데이터 추출 실패는 무시
            pass

    def _parse_job_sections(self, job_data: Dict):
        """
        content에서 각 섹션별로 텍스트를 파싱하여 해당 필드에 저장
        """
        if not job_data['content']:
            return

        content = job_data['content']

        # 섹션 정의 (키워드와 대응하는 필드)
        # \s*를 사용하여 공백 유무에 관계없이 매칭
        section_patterns = {
            'company_description': [
                r'회사\s*소개',
                r'기업\s*소개',
                r'쿠팡\s*소개',
                r'Company\s+(?:Info|Description|Overview|Introduction)',
            ],
            'team_description': [
                r'조직\s*소개',
                r'팀\s*소개',
                r'팀\s*정보',
                r'조직\s*문화',
                r'Team\s+(?:Info|Description|Overview|Introduction)',
            ],
            'job_description': [
                r'직무\s*소개',
                r'업무\s*내용',
                r'주요\s*업무',
                r'담당\s*업무',
                r'Job\s+(?:Description|Overview)',
                r'Responsibilities',
            ],
            'required_qualifications': [
                r'필수\s*(?:조건|자격|요건)',
                r'Required\s+(?:Qualifications|Skills|Requirements)',
            ],
            'preferred_qualifications': [
                r'우대\s*(?:사항|조건|요건)',
                r'Preferred\s+(?:Qualifications|Skills|Requirements)',
            ],
            'recruitment_schedule': [
                r'채용\s*(?:일정|스케줄|기간)',
                r'Recruitment\s+Schedule',
            ],
            'selection_process': [
                r'전형\s*절차',
                r'선발\s*절차',
                r'Selection\s+Process',
                r'면접',
            ],
            'notes': [
                r'참고\s*사항',
                r'주의\s*사항',
                r'Important\s+Notes',
                r'안내\s*사항',
            ],
            'privacy_policy': [
                r'개인정보\s*처리방침',
                r'Privacy\s+Policy',
                r'개인정보\s*보호',
            ],
            'document_return_policy': [
                r'서류\s*반환',
                r'Document\s+Return',
            ],
        }

        # 각 섹션에 대해 텍스트 추출
        for field, patterns in section_patterns.items():
            if job_data[field]:  # 이미 추출된 경우 건너뛰기
                continue

            for pattern in patterns:
                # 섹션 시작 위치 찾기 (공백 무시)
                match = re.search(pattern, content, re.IGNORECASE)
                if not match:
                    continue

                start_pos = match.start()
                section_text = ""

                # 다음 섹션까지의 텍스트 추출
                remaining_text = content[start_pos:]
                lines = remaining_text.split('\n')

                # 첫 번째 줄은 헤더이므로 스킵
                for i, line in enumerate(lines[1:], 1):
                    line = line.strip()

                    # 빈 줄은 스킵
                    if not line:
                        continue

                    # 다른 섹션 키워드가 나오면 중단
                    is_next_section = False
                    for other_patterns in section_patterns.values():
                        for other_pattern in other_patterns:
                            if re.search(other_pattern, line, re.IGNORECASE):
                                is_next_section = True
                                break
                        if is_next_section:
                            break

                    if is_next_section:
                        break

                    section_text += line + '\n'

                    # 최대 2000자까지 추출
                    if len(section_text) > 2000:
                        section_text = section_text[:2000].rsplit('\n', 1)[0]
                        break

                if section_text.strip():
                    job_data[field] = section_text.strip()
                    break

    def parse_with_claude(self, job_data: Dict, api_key: str) -> Dict:
        """
        Claude API를 사용하여 텍스트에서 구조화된 정보 추출

        Args:
            job_data: 크롤링된 원본 데이터
            api_key: Claude API 키

        Returns:
            파싱된 채용공고 정보
        """
        if not job_data['content']:
            return job_data

        try:
            import anthropic

            client = anthropic.Anthropic(api_key=api_key)

            prompt = f"""다음 채용공고 텍스트에서 정보를 추출하여 JSON 형식으로 반환해주세요.

채용공고 URL: {job_data['url']}
채용공고 내용:
{job_data['content'][:2500]}

다음 정보를 추출해주세요:
1. 공고게시일 (posting_date) - YYYY-MM-DD 형식
2. 마감일 (closing_date) - YYYY-MM-DD 형식
3. 지역 (location)
4. 고용형태 (employment_type)
5. 필수조건 (required_qualifications) - 불릿 포인트로
6. 우대조건 (preferred_qualifications) - 불릿 포인트로
7. 직무소개 (job_description)
8. 회사소개 (company_description)

정보가 없으면 빈 문자열로 반환하세요.
응답은 유효한 JSON 형식만 반환하세요."""

            message = client.messages.create(
                model="claude-3-5-sonnet-20241022",
                max_tokens=1500,
                messages=[
                    {"role": "user", "content": prompt}
                ]
            )

            # 응답에서 JSON 추출
            response_text = message.content[0].text

            # JSON 파싱
            json_match = re.search(r'\{.*\}', response_text, re.DOTALL)
            if json_match:
                parsed_data = json.loads(json_match.group())

                # 기존 데이터에 병합 (빈 값만 채우기)
                for key, value in parsed_data.items():
                    if key in job_data and not job_data[key] and value:
                        job_data[key] = value

                print(f"  ✅ Claude API 파싱 완료")

        except Exception as e:
            print(f"  ⚠️  Claude API 파싱 실패: {str(e)}")

        return job_data

    def crawl(self,
              output_file: str = "coupang.json",
              use_ai: bool = False,
              api_key: Optional[str] = None,
              korea_only: bool = False) -> List[Dict]:
        """
        크롤링 실행

        Args:
            output_file: JSON 출력 파일
            use_ai: Claude API 사용 여부
            api_key: Claude API 키
            korea_only: 한국 채용만 수집 여부

        Returns:
            수집된 채용공고 리스트
        """
        start_time = time.time()

        try:
            # 채용공고 링크 수집
            job_links = self.get_job_links(korea_only)

            if not job_links:
                print("❌ 채용공고를 찾을 수 없습니다.")
                return []

            # 각 공고 크롤링
            jobs = []
            success_count = 0
            fail_count = 0
            korea_count = 0

            for idx, url in enumerate(job_links, 1):
                print(f"\n⏳ [{idx}/{len(job_links)}] 크롤링 중...")

                job_data = self.extract_job_details(url)

                # 계약직 필터링 (제외)
                if self._is_contract_position(job_data['title'], job_data['employment_type']):
                    print(f"  ⏭️  계약직 - 건너뜀")
                    fail_count += 1
                    time.sleep(self.delay * 0.5)  # 짧은 대기
                    continue

                # 한국 채용 필터링
                if korea_only:
                    if not self.is_korea_job(job_data['title'], job_data['content']):
                        print(f"  ⏭️  해외 채용 - 건너뜀")
                        fail_count += 1
                        time.sleep(self.delay * 0.5)  # 짧은 대기
                        continue

                # Claude API 파싱
                if use_ai and api_key and job_data['content']:
                    job_data = self.parse_with_claude(job_data, api_key)

                jobs.append(job_data)
                korea_count += 1

                if job_data['title']:
                    success_count += 1
                else:
                    fail_count += 1

                # 과부하 방지를 위한 대기
                time.sleep(self.delay)

            # 크롤링된 시간 순서로 정렬 (최신 먼저)
            # crawled_at 필드를 기준으로 역순 정렬 (최신이 먼저 오도록)
            jobs.sort(key=lambda x: x['crawled_at'], reverse=True)

            # JSON 파일 저장
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(jobs, f, ensure_ascii=False, indent=2)

            # 통계 출력
            elapsed_time = time.time() - start_time
            avg_time = elapsed_time / len(jobs) if jobs else 0

            print("\n" + "=" * 70)
            print("🎉 크롤링 완료!")
            print("=" * 70)
            print(f"✅ 수집 완료: {success_count}개 | ❌ 수집 실패: {fail_count}개")
            print(f"📁 저장 경로: {output_file}")
            print(f"⏱️  총 소요 시간: {elapsed_time:.2f}초")
            print(f"⚡ 평균 처리시간: {avg_time:.2f}초/개")
            print("=" * 70)

            return jobs

        finally:
            self.session.close()


def main():
    """CLI 메인 함수"""
    parser = argparse.ArgumentParser(
        description='쿠팡 채용사이트 크롤러',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
사용 예시:
  # 기본 크롤링 (모든 공고 전체 수집)
  python coupang_crawler.py

  # South Korea 위치의 모든 공고 수집
  python coupang_crawler.py --location "South Korea"

  # 한국 채용만 전체 수집 (클라이언트 필터링)
  python coupang_crawler.py --korea

  # Claude API 파싱 사용
  python coupang_crawler.py --ai --api-key your-api-key

  # 커스텀 출력 파일 및 대기시간
  python coupang_crawler.py -o results/jobs.json --delay 3

  # Seoul 위치로 필터링하여 모든 공고 수집
  python coupang_crawler.py --location "Seoul" --delay 1
        """
    )

    parser.add_argument(
        '-o', '--output',
        default='coupang.json',
        help='JSON 출력 파일 경로 (기본: coupang.json)'
    )

    parser.add_argument(
        '--delay',
        type=float,
        default=2.0,
        help='요청 간 대기시간 (초, 기본: 2.0)'
    )

    parser.add_argument(
        '--ai',
        action='store_true',
        help='Claude API를 사용한 텍스트 파싱 활성화'
    )

    parser.add_argument(
        '--api-key',
        default=None,
        help='Anthropic API 키 (--ai 사용시)'
    )

    parser.add_argument(
        '--korea',
        action='store_true',
        help='한국 채용만 수집 (location 필터 없이 클라이언트 필터링)'
    )

    parser.add_argument(
        '--location',
        default=None,
        help='위치 필터 (예: "South Korea", "Seoul") - 서버 필터링 사용'
    )

    args = parser.parse_args()

    # AI 파싱 사용 시 API 키 확인
    if args.ai and not args.api_key:
        api_key = os.environ.get('ANTHROPIC_API_KEY')
        if not api_key:
            parser.error('--ai 옵션 사용 시 --api-key 또는 ANTHROPIC_API_KEY 환경변수가 필요합니다')
        args.api_key = api_key

    # 크롤러 실행
    print("\n" + "=" * 70)
    print("🚀 쿠팡 채용사이트 크롤러")
    print("=" * 70)
    print(f"📝 출력 파일: {args.output}")
    print(f"⏱️  요청 대기시간: {args.delay}초")
    print(f"📊 수집 방식: 전체 크롤링 (제한 없음)")
    print(f"🤖 Claude API 파싱: {'활성화' if args.ai else '비활성화'}")
    if args.location:
        print(f"📍 위치 필터: {args.location}")
    print(f"🇰🇷 한국 채용만: {'활성화' if args.korea else '비활성화'}")
    print("=" * 70 + "\n")

    crawler = CoupangJobCrawler(delay=args.delay, location=args.location)

    crawler.crawl(
        output_file=args.output,
        use_ai=args.ai,
        api_key=args.api_key,
        korea_only=args.korea
    )


if __name__ == '__main__':
    main()
