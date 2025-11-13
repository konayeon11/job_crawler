import asyncio
import re
import logging
from typing import List, Dict, Optional
from .base_crawler import BaseCrawler

logger = logging.getLogger(__name__)


class WoowahanCrawler(BaseCrawler):
    """
    우아한형제들 채용 공고 크롤러 (Playwright 기반)
    """

    def get_company_name(self) -> str:
        """회사명 반환"""
        return "Woowahan"

    def get_job_list_urls(self) -> List[str]:
        """
        채용 목록 페이지 URL 리스트 반환

        Returns:
            우아한형제들 채용공고 URL 리스트
        """
        return [
            "https://career.woowahan.com/?keyword=&category=all%3Aall&employmentTypeCodes=BA002001#recruit-list",
        ]

    def extract_job_urls(self, html: str) -> List[Dict[str, str]]:
        """
        HTML에서 개별 공고 URL 추출

        Args:
            html: 파싱할 HTML 문자열

        Returns:
            [{'url': '...', 'job_id': '...', 'title': '...'}] 형식의 리스트
        """
        # Playwright 기반 크롤러는 async 함수로 처리되므로
        # 여기서는 기본 구현만 제공
        # 실제 파싱은 async 메서드에서 처리
        return []

    def get_wait_time(self) -> int:
        """
        PDF 캡처 대기 시간(초)

        우아한형제들은 동적 로드가 있으므로 충분한 대기 필요
        """
        return 5

    def requires_selenium(self) -> bool:
        """
        동적 페이지 여부

        우아한형제들은 Playwright로 처리됨
        """
        return False

    def requires_playwright(self) -> bool:
        """
        Playwright 사용 여부

        우아한형제들은 Playwright 필요
        """
        return True

    async def extract_job_links(self, page) -> List[str]:
        """
        채용공고 목록 페이지에서 개별 공고 링크 추출

        Args:
            page: Playwright page 객체

        Returns:
            공고 링크 리스트
        """
        try:
            logger.info("채용공고 목록 페이지 로딩...")

            # 페이지 로드
            await page.goto(self.get_job_list_urls()[0], wait_until="networkidle", timeout=60000)
            await asyncio.sleep(3)  # 동적 콘텐츠 로드 대기

            # 목록에서 공고 링크 추출
            links = []
            job_items = await page.query_selector_all(
                "a[href*='career.woowahan.com'], a[href*='/job/'], .recruit-item a"
            )

            for item in job_items:
                href = await item.get_attribute("href")
                if href and "/job/" in href:
                    full_url = self._normalize_url(href)
                    if full_url not in links:
                        links.append(full_url)

            logger.info(f"추출된 공고 링크: {len(links)}개")
            return links

        except Exception as e:
            logger.error(f"채용공고 링크 추출 실패: {e}")
            return []

    async def parse_job_detail_async(self, page, url: str, idx: int) -> Optional[Dict]:
        """
        공고 상세 페이지 파싱 (Async)

        Args:
            page: Playwright page 객체
            url: 공고 URL
            idx: 인덱스

        Returns:
            파싱된 공고 데이터 또는 None
        """
        try:
            logger.info(f"[{idx}] 상세 페이지 로딩: {url}")
            await page.goto(url, wait_until="networkidle", timeout=60000)
            await asyncio.sleep(2)

            # 기본 정보 추출
            job_data = {
                "url": url,
                "job_id": self._extract_job_id(url),
                "company": self.get_company_name(),
                "title": "",
                "job_description": "",
                "posting_date": "",
                "closing_date": "",
                "location": "",
                "company_description": "",
                "team_description": "",
                "required_qualifications": "",
                "preferred_qualifications": "",
                "recruitment_schedule": "",
                "selection_process": "",
                "notes": "",
                "key_technologies": ""
            }

            # 제목 추출
            try:
                title = await page.text_content("h1, h2, .job-title, .detail-title")
                job_data["title"] = title.strip() if title else ""
            except Exception as e:
                logger.debug(f"제목 추출 실패: {e}")

            # 본문 추출
            try:
                description = await page.text_content(".detail-view, .job-description, .recruit-detail")
                job_data["job_description"] = description.strip()[:5000] if description else ""
            except Exception as e:
                logger.debug(f"본문 추출 실패: {e}")

            # 메타데이터 추출
            job_data["posting_date"] = await self._extract_meta_async(page, "게시일", "공고일")
            job_data["closing_date"] = await self._extract_meta_async(page, "마감일", "마감")
            job_data["location"] = await self._extract_meta_async(page, "근무지", "위치")

            # 섹션별 내용 추출
            sections = await self._extract_sections_async(page)

            # 섹션 매핑
            section_mapping = {
                "회사소개": "company_description",
                "조직소개": "team_description",
                "팀소개": "team_description",
                "지원자격": "required_qualifications",
                "자격요건": "required_qualifications",
                "우대사항": "preferred_qualifications",
                "채용일정": "recruitment_schedule",
                "전형절차": "selection_process",
                "참고사항": "notes",
                "개발환경": "key_technologies",
                "주요기술": "key_technologies",
                "기술스택": "key_technologies"
            }

            for section_title, content in sections.items():
                for kr_title, field_name in section_mapping.items():
                    if kr_title in section_title or section_title in kr_title:
                        job_data[field_name] = content[:2000]
                        logger.debug(f"섹션 매핑: '{section_title}' → '{field_name}'")
                        break

            logger.info(f"상세 정보 추출 완료: {job_data['title']}")
            return job_data

        except Exception as e:
            logger.error(f"상세 페이지 파싱 실패 ({url}): {e}")
            return None

    async def _extract_meta_async(self, page, *keywords: str) -> str:
        """메타데이터 추출 (Async)"""
        try:
            text = await page.text_content("body")
            if not text:
                return ""

            for keyword in keywords:
                pattern = rf"{keyword}\s*[:：]\s*([^\n\r]+)"
                match = re.search(pattern, text)
                if match:
                    value = match.group(1).strip()
                    if re.search(r"\d{4}[-/\.]\d{1,2}[-/\.]\d{1,2}", value):
                        return value
                    if keyword == "근무지" or keyword == "위치":
                        return value.split("\n")[0].strip()

            return ""
        except Exception as e:
            logger.debug(f"메타데이터 추출 실패: {e}")
            return ""

    async def _extract_sections_async(self, page) -> Dict[str, str]:
        """섹션별 내용 추출 (Async)"""
        sections = {}

        try:
            result = await page.evaluate("""
                () => {
                    const sections = {};
                    const detailView = document.querySelector('.detail-view, .recruit-detail');
                    if (!detailView) return sections;

                    const fullText = detailView.innerText;
                    const sectionPattern = /\\[([^\\[\\]]+)\\]/g;
                    const matches = Array.from(fullText.matchAll(sectionPattern));

                    matches.forEach((match, idx) => {
                        const title = match[1].trim();
                        const startIndex = match.index + match[0].length;

                        let endIndex = fullText.length;
                        if (idx < matches.length - 1) {
                            endIndex = matches[idx + 1].index;
                        }

                        let content = fullText.substring(startIndex, endIndex)
                            .trim()
                            .split('\\n')
                            .filter(line => line.trim().length > 0)
                            .slice(0, 100)
                            .join('\\n');

                        if (content.length > 0) {
                            sections[title] = content.substring(0, 3000);
                        }
                    });

                    return sections;
                }
            """)

            sections = result
            logger.debug(f"섹션 {len(sections)}개 추출: {list(sections.keys())}")

            return sections

        except Exception as e:
            logger.debug(f"섹션 추출 실패: {e}")
            return sections

    def _extract_job_id(self, url: str) -> str:
        """URL에서 공고 ID 추출"""
        try:
            match = re.search(r"/job/(\d+)", url)
            if match:
                return match.group(1)
            return url.split("/")[-1]
        except Exception:
            return "woowahan_unknown"

    def _normalize_url(self, url: str) -> str:
        """URL 정규화"""
        if url.startswith("http"):
            return url
        elif url.startswith("/"):
            return f"https://career.woowahan.com{url}"
        else:
            return f"https://career.woowahan.com/{url}"
