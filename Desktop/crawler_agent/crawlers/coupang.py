import asyncio
import logging
import re
from typing import List, Dict, Optional, Any
from bs4 import BeautifulSoup
from .base_crawler import BaseCrawler

logger = logging.getLogger(__name__)


class CoupangCrawler(BaseCrawler):
    """
    쿠팡 채용 공고 크롤러 (Playwright 기반)

    쿠팡의 모든 채용공고를 크롤링합니다.
    https://www.coupang.jobs/kr/jobs/
    """

    def get_company_name(self) -> str:
        """회사명 반환"""
        return "Coupang"

    def get_job_list_urls(self) -> List[str]:
        """
        채용 목록 페이지 URL 리스트 반환

        Returns:
            쿠팡 채용공고 URL 리스트
        """
        return [
            "https://www.coupang.jobs/kr/jobs/",
        ]

    async def extract_job_urls(self, page: Any) -> List[Dict[str, str]]:
        """
        채용공고 목록 페이지에서 개별 공고 URL 추출 (비동기)

        페이지네이션을 통해 모든 공고를 수집

        Args:
            page: Playwright page 객체

        Returns:
            [{'url': '...', 'job_id': '...', 'title': '...'}] 형식의 리스트
        """
        try:
            logger.info("쿠팡 채용공고 링크 추출 중 (페이지네이션)...")

            # Playwright로 페이지 로드
            await page.goto(
                self.get_job_list_urls()[0],
                wait_until='domcontentloaded',
                timeout=self.get_timeout()
            )

            # 페이지 렌더링 대기
            await asyncio.sleep(2)

            # 페이지에서 총 공고 수 추출 및 페이지 수 계산
            page_info = await page.evaluate("""
                () => {
                    const text = document.body.innerText;
                    // "20 건 확인 중, 총 776건의 결과" 형식에서 추출
                    const match = text.match(/총\\s*(\\d+)건/);
                    const totalJobs = match ? parseInt(match[1]) : 0;

                    // 페이지당 20개씩
                    const pageSize = 20;
                    const totalPages = Math.ceil(totalJobs / pageSize);

                    return {
                        totalJobs: totalJobs,
                        pageSize: pageSize,
                        totalPages: totalPages
                    };
                }
            """)

            total_jobs = page_info.get('totalJobs', 0)
            total_pages = page_info.get('totalPages', 1)

            logger.info(f"총 공고 수: {total_jobs}개 (예상 페이지: {total_pages}개)")

            # 모든 공고 링크 수집 (페이지네이션)
            job_links = set()
            current_page = 1

            logger.info(f"페이지네이션 수집 시작 (총 {total_pages}페이지, {total_jobs}개 공고)...")

            while current_page <= total_pages:
                # 현재 페이지의 모든 gh_jid 링크 추출
                current_links = await page.evaluate("""
                    () => {
                        const links = new Set();
                        document.querySelectorAll('a[href*="/jobs/"][href*="gh_jid="]').forEach(a => {
                            const href = a.getAttribute('href');
                            if (href && href.includes('gh_jid=')) {
                                links.add(href);
                            }
                        });
                        return Array.from(links);
                    }
                """)

                job_links.update(current_links)
                current_count = len(job_links)

                logger.info(f"[페이지 {current_page}/{total_pages}] 수집된 링크: {current_count}개")

                # 마지막 페이지이면 종료
                if current_page >= total_pages:
                    logger.info("모든 페이지 수집 완료.")
                    break

                # 다음 페이지로 이동
                try:
                    # 페이지 번호 이동 - URL을 직접 변경하는 방식
                    next_page_url = f"{self.get_job_list_urls()[0]}?page={current_page + 1}"
                    await page.goto(next_page_url, wait_until='domcontentloaded', timeout=self.get_timeout())
                    await asyncio.sleep(1)  # 페이지 로드 대기 (1초로 단축)

                except Exception as e:
                    logger.warning(f"다음 페이지로 이동 실패: {e}. 수집 종료.")
                    break

                current_page += 1

            logger.info(f"총 {len(job_links)}개의 채용공고 링크 추출 완료")

            # URL 정규화
            normalized_links = []
            for link in job_links:
                try:
                    full_url = self._normalize_url(link)
                    normalized_links.append(full_url)
                except Exception:
                    continue

            return [
                {
                    "url": link,
                    "job_id": self._extract_job_id(link),
                    "title": ""
                }
                for link in normalized_links
            ]

        except Exception as e:
            logger.error(f"채용공고 링크 추출 실패: {e}")
            return []

    async def parse_job_detail(self, page: Any, url: str, idx: int) -> Optional[Dict[str, Any]]:
        """
        공고 상세 페이지 파싱 (비동기)

        Args:
            page: Playwright page 객체
            url: 공고 URL
            idx: 인덱스

        Returns:
            파싱된 공고 데이터 또는 None
        """
        try:
            logger.info(f"[{idx}] 공고 파싱 중: {url}")
            await page.goto(url, wait_until='domcontentloaded', timeout=self.get_timeout())

            # JavaScript 로드 대기
            await asyncio.sleep(self.get_wait_time())

            # 페이지 스크롤 (lazy-loading 콘텐츠 로드)
            await page.evaluate("() => window.scrollTo(0, document.documentElement.scrollHeight)")
            await asyncio.sleep(1)

            job_data = {
                "url": url,
                "job_id": self._extract_job_id(url),
                "company": self.get_company_name(),
                "title": "",
                "posting_date": "",
                "closing_date": "",
                "location": "",
                "employment_type": "",
                "job_description": "",
                "required_qualifications": "",
                "preferred_qualifications": "",
                "company_description": "",
                "team_description": "",
                "selection_process": "",
                "notes": "",
                "metadata": {
                    "crawled_at": asyncio.get_event_loop().time(),
                    "wait_time": self.get_wait_time(),
                }
            }

            # JavaScript로 페이지 데이터 추출
            try:
                result = await page.evaluate("""
                    () => {
                        const data = {};

                        // 제목 추출 (보통 h1 또는 page title)
                        const titleEl = document.querySelector('h1, [class*="title"]');
                        if (titleEl) {
                            data.title = titleEl.textContent.trim().substring(0, 200);
                        } else {
                            const pageTitle = document.querySelector('title');
                            if (pageTitle) {
                                data.title = pageTitle.textContent.split('|')[0].trim().substring(0, 200);
                            }
                        }

                        // article.cms-content에서 본문 추출 (쿠팡 특화)
                        const cmsContent = document.querySelector('article.cms-content');
                        if (cmsContent) {
                            data.jobDescription = cmsContent.textContent.trim().substring(0, 5000);
                        } else {
                            // Fallback: main 또는 article 태그
                            const mainEl = document.querySelector('main, article, [class*="content"]');
                            if (mainEl) {
                                data.jobDescription = mainEl.textContent.trim().substring(0, 5000);
                            }
                        }

                        // 위치/지역 정보
                        const locationEl = document.querySelector('[class*="location"], [class*="address"], [class*="area"]');
                        if (locationEl) {
                            data.location = locationEl.textContent.trim().substring(0, 200);
                        }

                        // 고용형태
                        const employmentEl = document.querySelector('[class*="employment"], [class*="type"]');
                        if (employmentEl) {
                            data.employmentType = employmentEl.textContent.trim().substring(0, 100);
                        }

                        return data;
                    }
                """)

                # camelCase를 snake_case로 변환하여 저장
                for key, value in result.items():
                    snake_key = self._camel_to_snake(key)
                    if snake_key in job_data and value:
                        job_data[snake_key] = value

            except Exception as e:
                logger.warning(f"JavaScript 파싱 실패 ({url}): {e}")

            # HTML 원본 저장
            job_data["html"] = await page.content()

            # 섹션별 파싱 (content에서 구조화된 정보 추출)
            await self._parse_sections(page, job_data)

            logger.info(f"[{idx}] 공고 파싱 완료: {job_data.get('title', 'Unknown')}")
            return job_data

        except Exception as e:
            logger.error(f"공고 상세 파싱 실패 ({url}): {e}")
            return None

    async def _parse_sections(self, page: Any, job_data: Dict):
        """
        페이지에서 섹션별 정보 추출

        Args:
            page: Playwright page 객체
            job_data: 공고 데이터 딕셔너리
        """
        try:
            # HTML 컨텐츠 가져오기
            html_content = await page.content()

            # 섹션별 키워드 정의
            sections = {
                'company_description': [
                    '회사소개', '쿠팡 소개', '기업소개', 'About', 'Company'
                ],
                'team_description': [
                    '팀소개', '팀 정보', '조직소개', 'Team', 'Organization'
                ],
                'job_description': [
                    '직무소개', '주요업무', '담당업무', '직무', 'Job Description', 'Responsibilities'
                ],
                'required_qualifications': [
                    '필수요건', '필수자격', '필수조건', 'Required', 'Must Have'
                ],
                'preferred_qualifications': [
                    '우대사항', '우대조건', '우대요건', 'Preferred', 'Nice to Have'
                ],
            }

            # BeautifulSoup을 사용하여 섹션 추출
            soup = BeautifulSoup(html_content, 'html.parser')
            content_text = soup.get_text('\n', strip=True)

            # 각 섹션별로 텍스트 추출
            for field, keywords in sections.items():
                if job_data[field]:  # 이미 채워진 경우 스킵
                    continue

                for keyword in keywords:
                    pattern = rf'{keyword}.*?(?=\n\n|$)'
                    match = re.search(pattern, content_text, re.IGNORECASE | re.DOTALL)
                    if match:
                        section_text = match.group(0).strip()
                        if len(section_text) > 50:  # 최소 길이 확인
                            job_data[field] = section_text[:2000]
                            break

        except Exception as e:
            logger.debug(f"섹션 파싱 실패: {e}")

    def get_wait_time(self) -> int:
        """
        PDF 캡처 대기 시간(초)

        쿠팡은 일부 콘텐츠가 lazy-loading되므로 적당한 대기 필요
        """
        return 5

    def requires_selenium(self) -> bool:
        """
        동적 페이지 여부

        쿠팡은 Playwright로 처리됨
        """
        return False

    def requires_playwright(self) -> bool:
        """
        Playwright 사용 여부

        쿠팡은 Playwright 필요 (동적 페이지)
        """
        return True

    def get_max_concurrent_jobs(self) -> int:
        """동시 처리 공고 수"""
        return 5  # 전체 공고 크롤링을 위해 동시 처리 증가

    def get_timeout(self) -> int:
        """타임아웃 시간(밀리초)"""
        return 30000  # 페이지 로드 타임아웃 (30초)

    def _normalize_url(self, href: str) -> str:
        """
        상대 URL을 절대 URL로 변환

        Args:
            href: 상대 또는 절대 URL

        Returns:
            절대 URL
        """
        if href.startswith("http"):
            return href
        elif href.startswith("/"):
            return "https://www.coupang.jobs" + href
        else:
            return "https://www.coupang.jobs/" + href

    def _extract_job_id(self, url: str) -> str:
        """
        URL에서 job_id 추출 (gh_jid 파라미터)

        Args:
            url: 공고 URL

        Returns:
            job_id 문자열
        """
        # gh_jid 파라미터 추출 (Greenhouse 시스템)
        match = re.search(r'gh_jid=(\d+)', url)
        if match:
            return f"coupang_{match.group(1)}"

        # URL 경로에서 추출
        match = re.search(r'/jobs/([^/?]+)', url)
        if match:
            return f"coupang_{match.group(1)}"

        # URL의 마지막 부분 사용
        job_id = url.rstrip('/').split('/')[-1]
        return f"coupang_{job_id}" if job_id else "coupang_unknown"

    def _camel_to_snake(self, name: str) -> str:
        """
        camelCase를 snake_case로 변환

        Args:
            name: camelCase 문자열

        Returns:
            snake_case 문자열
        """
        s1 = re.sub('(.)([A-Z][a-z]+)', r'\1_\2', name)
        return re.sub('([a-z0-9])([A-Z])', r'\1_\2', s1).lower()
