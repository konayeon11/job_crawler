import asyncio
import logging
import re
from typing import List, Dict, Optional, Any
from .base_crawler import BaseCrawler

logger = logging.getLogger(__name__)


class NaverCrawler(BaseCrawler):
    """
    네이버 채용 공고 크롤러 (Playwright 기반)

    네이버 채용 공고를 크롤링합니다.
    """

    def get_company_name(self) -> str:
        """회사명 반환"""
        return "Naver"

    def get_job_list_urls(self) -> List[str]:
        """
        채용 목록 페이지 URL 리스트 반환

        Returns:
            네이버 채용공고 URL 리스트
        """
        return [
            "https://recruit.naver.com/rcrt/list.do",
        ]

    async def extract_job_urls(self, page: Any) -> List[Dict[str, str]]:
        """
        채용공고 목록 페이지에서 개별 공고 URL 추출 (비동기)

        Args:
            page: Playwright page 객체

        Returns:
            [{'url': '...', 'job_id': '...', 'title': '...'}] 형식의 리스트
        """
        try:
            logger.info("네이버 메인 페이지 로딩 중...")
            await page.goto(
                self.get_job_list_urls()[0],
                wait_until='domcontentloaded',
                timeout=self.get_timeout()
            )

            # JavaScript 실행 대기
            logger.info("JavaScript 실행 대기 중...")
            await asyncio.sleep(2)

            # 채용공고 링크 추출
            logger.info("채용공고 링크 추출 중...")
            job_links = []

            try:
                # 네이버 채용공고 URL 패턴 찾기
                result = await page.evaluate("""
                    () => {
                        const links = [];
                        // 네이버 채용 링크: /rcrt/view.do 또는 /rcrt/detail.do
                        document.querySelectorAll('a[href]').forEach(a => {
                            const href = a.getAttribute('href');
                            if (href && (href.includes('/rcrt/view.do') || href.includes('/rcrt/detail.do'))) {
                                links.push(href);
                            }
                        });
                        // 중복 제거
                        return [...new Set(links)];
                    }
                """)

                for href in result:
                    try:
                        full_url = self._normalize_url(href)
                        if full_url not in job_links:
                            job_links.append(full_url)
                    except Exception:
                        continue

                logger.info(f"총 {len(job_links)}개의 채용공고 링크 추출")

            except Exception as e:
                logger.warning(f"JavaScript 실행 실패: {e}")
                # Fallback: CSS 선택자로 링크 추출
                try:
                    job_elements = await page.query_selector_all('a[href*="/rcrt/view.do"], a[href*="/rcrt/detail.do"]')
                    for elem in job_elements:
                        href = await elem.get_attribute('href')
                        if href:
                            try:
                                full_url = self._normalize_url(href)
                                if full_url not in job_links:
                                    job_links.append(full_url)
                            except Exception:
                                continue
                except Exception as fallback_error:
                    logger.error(f"CSS 선택자 방식도 실패: {fallback_error}")

            return [
                {
                    "url": link,
                    "job_id": self._extract_job_id(link),
                    "title": ""
                }
                for link in job_links
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

            job_data = {
                "url": url,
                "job_id": self._extract_job_id(url),
                "company": self.get_company_name(),
                "title": "",
                "posting_date": "",
                "closing_date": "",
                "location": "",
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

                        // 제목 추출
                        const titleEl = document.querySelector('h1, [class*="title"]');
                        if (titleEl) {
                            data.title = titleEl.textContent.trim().substring(0, 200);
                        }

                        // 본문 추출
                        const contentEl = document.querySelector('[class*="content"], [class*="description"], .section_bottom, main');
                        if (contentEl) {
                            data.jobDescription = contentEl.textContent.trim().substring(0, 5000);
                        }

                        // 필수 자격 추출
                        const qualEl = document.querySelector('[class*="qual"], [class*="requirement"]');
                        if (qualEl) {
                            data.requiredQualifications = qualEl.textContent.trim().substring(0, 2000);
                        }

                        return data;
                    }
                """)

                job_data.update({k: v for k, v in result.items() if v})

            except Exception as e:
                logger.warning(f"JavaScript 파싱 실패 ({url}): {e}")

            # HTML 원본 저장
            job_data["html"] = await page.content()

            logger.info(f"[{idx}] 공고 파싱 완료: {job_data.get('title', 'Unknown')}")
            return job_data

        except Exception as e:
            logger.error(f"공고 상세 파싱 실패 ({url}): {e}")
            return None

    def get_wait_time(self) -> int:
        """
        PDF 캡처 대기 시간(초)

        네이버는 비교적 빠르게 로드됨
        """
        return 3

    def requires_selenium(self) -> bool:
        """
        동적 페이지 여부

        네이버는 Playwright로 처리됨
        """
        return False

    def requires_playwright(self) -> bool:
        """
        Playwright 사용 여부

        네이버는 Playwright 필요
        """
        return True

    def get_max_concurrent_jobs(self) -> int:
        """동시 처리 공고 수"""
        return 3

    def get_timeout(self) -> int:
        """타임아웃 시간(밀리초)"""
        return 30000

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
            return "https://recruit.naver.com" + href
        else:
            return "https://recruit.naver.com/" + href

    def _extract_job_id(self, url: str) -> str:
        """
        URL에서 job_id 추출

        Args:
            url: 공고 URL

        Returns:
            job_id 문자열
        """
        # recruitSeq 파라미터 추출
        match = re.search(r'recruitSeq=(\d+)', url)
        if match:
            return f"naver_{match.group(1)}"

        # URL 경로에서 마지막 부분 사용
        job_id = url.rstrip('/').split('/')[-1]
        return f"naver_{job_id}" if job_id else "naver_unknown"
