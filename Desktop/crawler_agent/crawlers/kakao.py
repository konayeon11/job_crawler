import asyncio
import logging
import re
from typing import List, Dict, Optional, Any
from .base_crawler import BaseCrawler

logger = logging.getLogger(__name__)


class KakaoCrawler(BaseCrawler):
    """
    카카오 채용 공고 크롤러 (Playwright 기반)

    카카오 채용 공고를 크롤링합니다.
    """

    def get_company_name(self) -> str:
        """회사명 반환"""
        return "Kakao"

    def get_job_list_urls(self) -> List[str]:
        """
        채용 목록 페이지 URL 리스트 반환

        Returns:
            카카오 채용공고 URL 리스트
        """
        return [
            "https://careers.kakao.com/jobs",
        ]

    async def extract_job_urls(self, page: Any) -> List[Dict[str, str]]:
        """
        채용공고 목록 페이지에서 개별 공고 URL 추출 (비동기, 페이지네이션 + 다중 카테고리 지원)

        카카오는 4가지 카테고리(기술, 서비스비즈, 디자인, 스태프)로 구성되어 있습니다.
        Playwright를 사용해 버튼 클릭으로 카테고리를 선택합니다.

        Args:
            page: Playwright page 객체

        Returns:
            [{'url': '...', 'job_id': '...', 'title': '...'}] 형식의 리스트
        """
        try:
            base_url = self.get_job_list_urls()[0]
            job_links = []
            max_pages = 50  # 카테고리당 최대 페이지 수

            # 카카오 채용 카테고리 정의 (버튼 텍스트, 표시명)
            categories = [
                ("기술", "기술"),
                ("서비스비즈", "서비스비즈"),
                ("디자인", "디자인"),
                ("스태프", "스태프"),
            ]

            # 먼저 기본 페이지 로드
            logger.info(f"카카오 채용 목록 페이지 로드 중: {base_url}")
            await page.goto(base_url, wait_until='networkidle', timeout=self.get_timeout())
            await asyncio.sleep(2)

            # 각 카테고리별로 크롤링
            for button_text, part_name in categories:
                logger.info(f"\n{'='*60}")
                logger.info(f"[{part_name}] 카테고리 크롤링 시작")
                logger.info(f"{'='*60}")

                try:
                    # 카테고리 버튼 클릭하여 선택
                    logger.info(f"[{part_name}] 카테고리 버튼 클릭 중...")

                    # 버튼을 찾고 클릭
                    category_button = None
                    try:
                        # txt_tab 클래스를 사용하여 버튼 찾기
                        category_button = page.locator(f"button.txt_tab:has-text('{button_text}')")
                        if await category_button.count() > 0:
                            await category_button.first.click()
                            logger.info(f"[{part_name}] 카테고리 버튼 클릭 완료")
                            await asyncio.sleep(3)  # 카테고리 전환 대기
                        else:
                            # txt_tab 클래스 없이 다시 시도
                            logger.info(f"[{part_name}] txt_tab 클래스로 찾기 실패, 다른 선택자 시도 중...")
                            category_button = page.locator(f"[class*='txt_tab']:has-text('{button_text}')")
                            if await category_button.count() > 0:
                                await category_button.first.click()
                                logger.info(f"[{part_name}] 대체 선택자로 버튼 클릭 완료")
                                await asyncio.sleep(3)
                            else:
                                logger.warning(f"[{part_name}] 카테고리 버튼을 찾을 수 없습니다: {button_text}")
                                continue
                    except Exception as e:
                        logger.warning(f"[{part_name}] 버튼 클릭 실패: {e}")
                        continue

                    # 페이지네이션 처리
                    page_num = 1
                    has_more = True
                    category_job_count = 0

                    while has_more and page_num <= max_pages:
                        logger.info(f"[{part_name}] 페이지 {page_num} 스크래핑 중...")

                        try:
                            # JavaScript 실행 대기
                            await asyncio.sleep(2)

                            # 추가 네트워크 요청 대기
                            try:
                                await page.wait_for_load_state('networkidle', timeout=5000)
                            except:
                                pass

                            # 현재 페이지에서 공고 링크 추출
                            result = await page.evaluate("""
                                () => {
                                    const links = [];
                                    document.querySelectorAll('a[href*="/jobs/P-"]').forEach(a => {
                                        const href = a.getAttribute('href');
                                        if (href && href.includes('/jobs/P-')) {
                                            const cleanUrl = href.split('?')[0];
                                            links.push(cleanUrl);
                                        }
                                    });
                                    return [...new Set(links)];
                                }
                            """)

                            page_job_count = 0
                            for href in result:
                                try:
                                    # 쿼리파라미터 없이 정규화
                                    full_url = self._normalize_url(href)
                                    if full_url not in job_links:
                                        job_links.append(full_url)
                                        page_job_count += 1
                                except Exception:
                                    continue

                            logger.info(f"[{part_name}] 페이지 {page_num}: {page_job_count}개 공고 추출 (누적: {len(job_links)}개)")
                            category_job_count += page_job_count

                            # 더 이상 공고가 없으면 종료
                            if page_job_count == 0:
                                has_more = False
                                logger.info(f"[{part_name}] 더 이상 공고가 없습니다.")
                            else:
                                # 다음 페이지로 이동
                                page_num += 1
                                next_page_url = f"{base_url}?page={page_num}"
                                await page.goto(next_page_url, wait_until='networkidle', timeout=self.get_timeout())

                        except Exception as e:
                            logger.warning(f"[{part_name}] 페이지 {page_num} 파싱 실패: {e}")
                            has_more = False

                    logger.info(f"[{part_name}] 크롤링 완료: {category_job_count}개 공고")

                except Exception as e:
                    logger.error(f"[{part_name}] 카테고리 처리 실패: {e}")
                    continue

            logger.info(f"\n{'='*60}")
            logger.info(f"전체 크롤링 완료: {len(job_links)}개의 채용공고 링크 추출")
            logger.info(f"{'='*60}\n")

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
                        const contentEl = document.querySelector('[class*="content"], [class*="description"], main, article');
                        if (contentEl) {
                            data.jobDescription = contentEl.textContent.trim().substring(0, 5000);
                        }

                        // 근무지 추출
                        const locationEl = document.querySelector('[class*="location"], [class*="area"]');
                        if (locationEl) {
                            data.location = locationEl.textContent.trim().substring(0, 200);
                        }

                        // 자격요건 추출
                        const qualEl = document.querySelector('[class*="requirement"], [class*="qualification"]');
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

        카카오는 동적 콘텐츠가 있을 수 있음
        """
        return 4

    def requires_selenium(self) -> bool:
        """
        동적 페이지 여부

        카카오는 Playwright로 처리됨
        """
        return False

    def requires_playwright(self) -> bool:
        """
        Playwright 사용 여부

        카카오는 Playwright 필요 (동적 페이지)
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
            return "https://careers.kakao.com" + href
        else:
            return "https://careers.kakao.com/" + href

    def _extract_job_id(self, url: str) -> str:
        """
        URL에서 job_id 추출

        Args:
            url: 공고 URL

        Returns:
            job_id 문자열
        """
        # /jobs/{id} 패턴 추출
        match = re.search(r'/jobs/([^/?]+)', url)
        if match:
            job_id = match.group(1)
            # 쿼리 파라미터 제거
            job_id = job_id.split('?')[0]
            return f"kakao_{job_id}"

        # /job/{id} 패턴 추출
        match = re.search(r'/job/([^/?]+)', url)
        if match:
            job_id = match.group(1)
            # 쿼리 파라미터 제거
            job_id = job_id.split('?')[0]
            return f"kakao_{job_id}"

        # URL의 마지막 부분 사용 (쿼리 파라미터 제거)
        job_id = url.rstrip('/').split('/')[-1]
        job_id = job_id.split('?')[0]
        return f"kakao_{job_id}" if job_id else "kakao_unknown"
