"""
LG 그룹 채용 공고 크롤러 (Playwright 기반)

LG 그룹의 채용공고를 크롤링합니다 (LG전자, LG유플러스, LG CNS, LG화학 등)
"""

import asyncio
import logging
import re
from typing import List, Dict, Optional, Any
from .base_crawler import BaseCrawler

logger = logging.getLogger(__name__)


class LGCrawler(BaseCrawler):
    """
    LG 그룹 채용 공고 크롤러 (Playwright 기반)

    LG 그룹 계열사의 채용공고를 크롤링합니다.
    """

    def get_company_name(self) -> str:
        """회사명 반환"""
        return "LG"

    def get_job_list_urls(self) -> List[str]:
        """
        채용 목록 페이지 URL 리스트 반환

        Returns:
            LG 채용공고 URL 리스트
        """
        return [
            "https://careers.lg.com/",
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
            logger.info("LG 채용공고 링크 추출 중...")

            # 페이지가 이미 로드되었다고 가정
            await asyncio.sleep(1)

            # 공고 목록 컨테이너 확인
            job_links = []
            try:
                # 공고 링크 선택자: a[href*="/apply/detail"]
                elements = await page.query_selector_all('a[href*="/apply/detail"]')

                for idx, elem in enumerate(elements):
                    try:
                        href = await elem.get_attribute('href')
                        text = await elem.inner_text()

                        if href and '/apply/detail' in href:
                            # URL에서 ID 추출: /apply/detail?id=1001083
                            match = re.search(r'id=(\d+)', href)
                            if match:
                                job_id = match.group(1)
                                full_url = href if href.startswith('http') else f"https://careers.lg.com{href}"

                                job_links.append({
                                    'url': full_url,
                                    'job_id': job_id,
                                    'title': text.strip()[:100] if text else f'LG Job {job_id}'
                                })
                    except Exception as e:
                        logger.warning(f"링크 {idx} 처리 실패: {e}")
                        continue

            except Exception as e:
                logger.warning(f"공고 목록 추출 실패: {e}")

            logger.info(f"총 {len(job_links)}개 공고 링크 추출됨")
            return job_links

        except Exception as e:
            logger.error(f"공고 추출 중 오류: {e}")
            return []

    async def parse_job_detail(self, page: Any, url: str, idx: int) -> Optional[Dict[str, str]]:
        """
        공고 상세 페이지 파싱 (비동기) - 아코디언 펼침 방식

        LG CNS는 MUI 아코디언을 사용하므로 모든 Accordion을 펼친 후 content 추출

        Args:
            page: Playwright page 객체
            url: 공고 URL
            idx: 공고 인덱스

        Returns:
            {
                'url': str,
                'job_id': str,
                'title': str,
                'company': str,
                'html': str,  # 원본 HTML (아코디언 펼쳐진 상태)
                'posting_date': str,
                'closing_date': str,
                'location': str,
                'job_description': str,
                'required_qualifications': str,
                'preferred_qualifications': str,
                'company_description': str,
                'team_description': str,
                'selection_process': str,
                'notes': str,
                'metadata': Dict[str, Any]
            }
        """
        try:
            logger.info(f"[{idx}] LG CNS 공고 상세 페이지 파싱: {url}")

            # 페이지 로드 (networkidle까지 대기)
            await page.goto(url, wait_until="networkidle", timeout=self.get_timeout())
            await asyncio.sleep(2)

            # URL에서 job_id 추출
            match = re.search(r'id=(\d+)', url)
            job_id = match.group(1) if match else "unknown"

            # 모든 MUI Accordion Summary를 펼치기
            logger.info(f"[{idx}] 아코디언 펼치기 시작...")
            accordion_summaries = await page.locator(".MuiAccordion-root .MuiAccordionSummary-root").all()

            for i, accordion in enumerate(accordion_summaries):
                try:
                    # 각 아코디언 클릭
                    await accordion.click()
                    logger.info(f"[{idx}] 아코디언 {i+1}/{len(accordion_summaries)} 펼침")
                    await asyncio.sleep(0.3)  # 애니메이션 대기
                except Exception as e:
                    logger.warning(f"[{idx}] 아코디언 {i+1} 펼치기 실패: {e}")
                    continue

            # 애니메이션 완료 대기
            await asyncio.sleep(0.5)

            # 원본 HTML 수집 (펼쳐진 상태)
            html_content = await page.content()

            # 공고 제목
            title = ""
            try:
                title_elem = await page.query_selector('h1, .job-title, [class*="title"]')
                if title_elem:
                    title = await title_elem.inner_text()
            except:
                pass

            # 회사명 (LG CNS)
            company = "LG CNS"
            try:
                # 회사명이 표시되는 곳 찾기
                company_elem = await page.query_selector('[class*="company"], [class*="subsidiary"], [class*="companyName"]')
                if company_elem:
                    company_text = await company_elem.inner_text()
                    if company_text and company_text.strip():
                        company = company_text.strip()
            except:
                pass

            # 마감일
            closing_date = ""
            try:
                # 마감일 패턴: YYYY.MM.DD 또는 YYYY-MM-DD
                page_text = await page.inner_text('body')
                match = re.search(r'(\d{4}[.\-]\d{2}[.\-]\d{2})', page_text)
                if match:
                    closing_date = match.group(1)
            except:
                pass

            # 위치/근무지
            location = ""
            try:
                location_elem = await page.query_selector('[class*="location"], [class*="place"], [class*="workPlace"]')
                if location_elem:
                    location = await location_elem.inner_text()
            except:
                pass

            # 펼쳐진 아코디언에서 모든 텍스트 추출
            job_description = ""
            try:
                # 아코디언 내용 추출
                accordion_contents = await page.query_selector_all(".MuiAccordion-root .MuiCollapse-root")
                if accordion_contents:
                    descriptions = []
                    for content in accordion_contents:
                        try:
                            text = await content.inner_text()
                            if text.strip():
                                descriptions.append(text.strip())
                        except:
                            continue
                    job_description = "\n\n".join(descriptions)
                else:
                    # 아코디언 없으면 일반 description 추출
                    desc_elem = await page.query_selector('[class*="description"], [class*="content"], article')
                    if desc_elem:
                        job_description = await desc_elem.inner_text()
            except Exception as e:
                logger.warning(f"[{idx}] 아코디언 content 추출 실패: {e}")

            result = {
                'url': url,
                'job_id': job_id,
                'title': title.strip() if title else f'LG CNS Job {job_id}',
                'company': company,
                'html': html_content,
                'posting_date': '',
                'closing_date': closing_date,
                'location': location,
                'job_description': job_description[:5000] if job_description else '',
                'required_qualifications': '',
                'preferred_qualifications': '',
                'company_description': '',
                'team_description': '',
                'selection_process': '',
                'notes': '',
                'metadata': {
                    'source': 'lg_cns',
                    'crawled_index': idx,
                    'accordion_expanded': len(accordion_summaries) > 0
                }
            }

            logger.info(f"[{idx}] 파싱 완료: {result['title'][:50]}")
            return result

        except Exception as e:
            logger.error(f"[{idx}] 공고 파싱 실패: {e}", exc_info=True)
            return None

    def get_wait_time(self) -> int:
        """PDF 캡처 대기 시간(초)"""
        return 3

    def requires_selenium(self) -> bool:
        """동적 페이지 여부 (True/False)"""
        return False

    def requires_playwright(self) -> bool:
        """Playwright 사용 여부"""
        return True

    def get_max_concurrent_jobs(self) -> int:
        """동시 처리 공고 수"""
        return 3
