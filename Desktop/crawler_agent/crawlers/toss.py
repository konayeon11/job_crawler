"""
토스 채용 공고 크롤러 (Playwright 기반)

토스의 채용공고를 크롤링합니다.
"""

import asyncio
import logging
import re
from typing import List, Dict, Optional, Any
from .base_crawler import BaseCrawler

logger = logging.getLogger(__name__)


class TossCrawler(BaseCrawler):
    """
    토스 채용 공고 크롤러 (Playwright 기반)

    토스의 채용공고를 크롤링합니다.
    """

    def get_company_name(self) -> str:
        """회사명 반환"""
        return "Toss"

    def get_job_list_urls(self) -> List[str]:
        """
        채용 목록 페이지 URL 리스트 반환

        Returns:
            토스 채용공고 URL 리스트
        """
        return [
            "https://toss.im/career/jobs",  # 토스 전체 포지션 및 공고
        ]

    async def extract_job_urls(self, page: Any) -> List[Dict[str, str]]:
        """
        채용공고 목록 페이지에서 개별 공고 URL 추출 (비동기)

        272개 포지션을 모두 스크롤해서 각 포지션의 모든 회사 공고를 추출합니다.

        Args:
            page: Playwright page 객체

        Returns:
            [{'url': '...', 'job_id': '...', 'title': '...'}] 형식의 리스트
        """
        try:
            logger.info("토스 전체 포지션 및 공고 링크 추출 중...")

            # 포지션 목록 페이지 로드
            list_url = self.get_job_list_urls()[0]
            logger.info(f"포지션 페이지 로드 중: {list_url}")
            try:
                await page.goto(list_url, wait_until="networkidle", timeout=self.get_timeout())
            except:
                logger.warning("networkidle 로드 실패, load로 재시도...")
                await page.goto(list_url, wait_until="load", timeout=self.get_timeout())
            logger.info("포지션 페이지 로드 완료")

            # 페이지 렌더링 대기
            await asyncio.sleep(3)

            # Step 1: 모든 포지션 로드 (전체 페이지 스크롤)
            logger.info("모든 포지션 로드를 위해 페이지 스크롤 중...")
            try:
                last_height = await page.evaluate("document.body.scrollHeight")
                scroll_count = 0
                max_scrolls = 100  # 무한 루프 방지

                while scroll_count < max_scrolls:
                    # 아래로 스크롤
                    await page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
                    await asyncio.sleep(1)

                    # 새로운 높이 확인
                    new_height = await page.evaluate("document.body.scrollHeight")
                    if new_height == last_height:
                        logger.info(f"모든 포지션 로드 완료 (총 {scroll_count}회 스크롤)")
                        break

                    last_height = new_height
                    scroll_count += 1

                # 페이지 상단으로 스크롤
                await page.evaluate("window.scrollTo(0, 0)")
                await asyncio.sleep(1)

            except Exception as e:
                logger.warning(f"페이지 스크롤 중 오류: {e}")

            # Step 2: 모든 job-detail 링크 추출
            logger.info("모든 세부 공고 링크 추출 중...")
            job_links = []
            try:
                # JavaScript로 모든 job-detail 링크 수집 (중복 제거)
                job_data = await page.evaluate("""() => {
                    const jobs = [];
                    const seen = new Set();
                    const links = document.querySelectorAll('a[href*="job-detail"]');

                    for (let link of links) {
                        const href = link.href;
                        if (!href.includes('job-detail')) continue;

                        // job_id 추출
                        const match = href.match(/job_id=([^&]+)/);
                        if (match && !seen.has(match[1])) {
                            const job_id = match[1];
                            const title = link.textContent.trim() || `Job ${job_id}`;

                            seen.add(job_id);
                            jobs.push({
                                url: href,
                                job_id: job_id,
                                title: title
                            });
                        }
                    }

                    return jobs;
                }""")

                job_links = job_data
                logger.info(f"발견된 세부 공고 URL: {len(job_links)}개")

                for idx, job in enumerate(job_links[:20], 1):  # 처음 20개만 로그
                    logger.info(f"  [{idx}] {job['title'][:40]} -> {job['url'][:60]}")
                if len(job_links) > 20:
                    logger.info(f"  ... 외 {len(job_links) - 20}개")

            except Exception as e:
                logger.error(f"공고 링크 추출 실패: {e}", exc_info=True)

            logger.info(f"총 {len(job_links)}개 세부 공고 링크 추출됨")
            return job_links

        except Exception as e:
            logger.error(f"공고 추출 중 오류: {e}", exc_info=True)
            return []

    async def parse_job_detail(self, page: Any, url: str, idx: int) -> Optional[Dict[str, str]]:
        """
        공고 상세 페이지 파싱 (비동기)

        Args:
            page: Playwright page 객체
            url: 공고 URL
            idx: 공고 인덱스

        Returns:
            공고 상세 정보 딕셔너리
        """
        try:
            logger.info(f"[{idx}] 토스 공고 상세 페이지 파싱: {url}")

            # URL이 상대 경로인 경우 절대 URL로 변환
            if url.startswith('/'):
                url = "https://toss.im" + url
                logger.info(f"[{idx}] URL 변환: {url}")

            # 페이지 로드
            try:
                await page.goto(url, wait_until="networkidle", timeout=self.get_timeout())
            except:
                logger.warning(f"[{idx}] networkidle 로드 실패, load로 재시도...")
                await page.goto(url, wait_until="load", timeout=self.get_timeout())

            logger.info(f"[{idx}] 페이지 로드 완료: {url}")

            # 페이지 렌더링 대기
            await asyncio.sleep(2)

            # 아코디언 펼치기 (모든 섹션 펼침)
            logger.info(f"[{idx}] 아코디언 섹션 펼치기 시도...")
            try:
                # 모든 버튼 찾기 (아코디언 토글 버튼은 보통 button 태그)
                buttons = await page.locator('button').all()
                for btn in buttons:
                    try:
                        # 버튼이 보이는지 확인
                        is_visible = await btn.is_visible()
                        if is_visible:
                            # 다양한 텍스트로 펼치기 버튼 확인 (한글, 영문 모두)
                            text = await btn.inner_text()
                            # 아코디언 펼치기 버튼 특징: 작은 텍스트나 아이콘 버튼
                            # 모든 보이는 버튼을 클릭해서 펼치기 시도
                            try:
                                await btn.click(timeout=3000)
                                await asyncio.sleep(0.3)  # 펼치는 애니메이션 대기
                                logger.info(f"[{idx}] 버튼 클릭: {text[:30]}")
                            except:
                                pass
                    except:
                        pass

                logger.info(f"[{idx}] 아코디언 펼치기 완료")
            except Exception as e:
                logger.warning(f"[{idx}] 아코디언 펼치기 실패: {e}")

            # 모든 섹션이 펼쳐진 후 추가 대기
            await asyncio.sleep(1)

            # URL에서 job_id 추출
            match = re.search(r'job_id=([^&]+)', url)
            job_id = match.group(1) if match else "unknown"

            # 원본 HTML 수집
            html_content = await page.content()
            logger.info(f"[{idx}] HTML 수집 완료 ({len(html_content)} bytes)")

            # 공고 제목
            title = ""
            try:
                title_elem = await page.query_selector('h1, .job-title, [class*="title"]')
                if title_elem:
                    title = await title_elem.inner_text()
            except:
                pass

            # 회사명
            company = "Toss"

            # 공고 설명 텍스트
            job_description = ""
            try:
                content_elem = await page.query_selector('[class*="content"], [class*="description"], main, article')
                if content_elem:
                    job_description = await content_elem.inner_text()
            except:
                pass

            # 세부 공고 페이지 여부 확인 (실제 내용이 있는 페이지인지 확인)
            # 공고 설명, job 키워드, 자격요건 등이 있으면 세부 페이지로 판단
            is_detail_page = (
                len(job_description) > 200 or
                'job' in html_content.lower() or
                'position' in html_content.lower() or
                '직무' in html_content or
                '요구' in html_content
            )

            logger.info(f"[{idx}] 세부 페이지 판정: {is_detail_page}")

            # 스크린샷 캡처 (세부 페이지에서만 - viewport 크기만 캡처)
            screenshot_bytes = None
            if is_detail_page:
                try:
                    await asyncio.sleep(1)  # 페이지 렌더링 대기
                    # full_page=False로 설정하여 현재 viewport 크기만 캡처 (길이 제한)
                    screenshot_bytes = await page.screenshot(full_page=False, timeout=60000)
                    logger.info(f"[{idx}] 스크린샷 캡처 완료 ({len(screenshot_bytes)} bytes)")
                except Exception as e:
                    logger.warning(f"[{idx}] 스크린샷 캡처 실패: {e}")
            else:
                logger.info(f"[{idx}] 세부 공고가 아닌 페이지로 판단 - 스크린샷 캡처 건너뜀")

            result = {
                'url': url,
                'job_id': job_id,
                'title': title.strip() if title else f'Toss Job {job_id}',
                'company': company,
                'html': html_content,
                'posting_date': '',
                'closing_date': '',
                'location': '',
                'job_description': job_description[:5000] if job_description else '',
                'required_qualifications': '',
                'preferred_qualifications': '',
                'company_description': '',
                'team_description': '',
                'selection_process': '',
                'notes': '',
                'screenshot': screenshot_bytes,
                'metadata': {
                    'source': 'toss',
                    'crawled_index': idx,
                }
            }

            logger.info(f"[{idx}] 파싱 완료: {result['title'][:50]}")
            return result

        except Exception as e:
            logger.error(f"[{idx}] 공고 파싱 실패: {e}", exc_info=True)
            return None

    def get_wait_time(self) -> int:
        """스크린샷 캡처 대기 시간(초)"""
        return 2

    def requires_selenium(self) -> bool:
        """동적 페이지 여부 (True/False)"""
        return False

    def requires_playwright(self) -> bool:
        """Playwright 사용 여부"""
        return True

    def get_max_concurrent_jobs(self) -> int:
        """동시 처리 공고 수"""
        return 3
