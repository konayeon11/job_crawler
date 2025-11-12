import asyncio
import json
import logging
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Optional
from playwright.async_api import async_playwright, Page
import re

# 설정 파일 임포트
try:
    from config import (
        CRAWLING_CONFIG, BROWSER_CONFIG, OUTPUT_CONFIG,
        CSS_SELECTORS, SECTION_MAPPING, META_KEYWORDS,
        DATA_CLEANING, DEBUG_CONFIG
    )
except ImportError:
    # 기본 설정값
    CRAWLING_CONFIG = {'max_jobs': None, 'request_delay': 1.5}
    BROWSER_CONFIG = {'headless': True}
    OUTPUT_CONFIG = {'log_filename': 'woowahan_crawler.log', 'log_level': 'INFO'}
    CSS_SELECTORS = {}
    SECTION_MAPPING = {}
    META_KEYWORDS = {}
    DATA_CLEANING = {}
    DEBUG_CONFIG = {'enabled': False}

# 로깅 설정
log_level = getattr(logging, OUTPUT_CONFIG.get('log_level', 'INFO'))
logging.basicConfig(
    level=log_level,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(OUTPUT_CONFIG.get('log_filename', 'woowahan_crawler.log')),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


class WoowahanCrawler:
    def __init__(self):
        self.base_url = "https://career.woowahan.com/?keyword=&category=all%3Aall&employmentTypeCodes=BA002001#recruit-list"
        self.job_links = []
        self.jobs = []
        self.output_file = None
        self.screenshot_dir = None
        self.timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    def _setup_screenshot_dir(self):
        """스크린샷 디렉토리 설정"""
        self.screenshot_dir = Path(f"screenshots_{self.timestamp}")
        self.screenshot_dir.mkdir(exist_ok=True)
        logger.info(f"스크린샷 디렉토리 생성: {self.screenshot_dir}")

    async def init_browser(self, p):
        """브라우저 초기화"""
        browser = await p.chromium.launch(
            headless=BROWSER_CONFIG.get('headless', True)
        )
        context = await browser.new_context(
            user_agent=BROWSER_CONFIG.get('user_agent', 'Mozilla/5.0'),
            viewport=BROWSER_CONFIG.get('viewport', {'width': 1280, 'height': 1024})
        )
        return browser, context

    async def extract_job_links(self, page: Page) -> List[str]:
        """메인 페이지에서 채용공고 링크 추출 (무한 스크롤 지원)"""
        try:
            logger.info("메인 페이지 로딩 중...")
            await page.goto(
                CRAWLING_CONFIG.get('base_url', self.base_url),
                wait_until='domcontentloaded',
                timeout=60000
            )

            # JavaScript 실행 대기
            logger.info("JavaScript 실행 대기 중...")
            await asyncio.sleep(2)

            # 무한 스크롤로 모든 공고 로드하기
            logger.info("무한 스크롤로 모든 공고 로드 중...")
            job_links = []
            previous_count = 0
            scroll_attempts = 0
            max_scroll_attempts = 20  # 최대 20번 스크롤

            while scroll_attempts < max_scroll_attempts:
                # 현재 페이지의 모든 공고 링크 추출
                try:
                    result = await page.evaluate("""
                        () => {
                            const links = [];
                            document.querySelectorAll('a[href]').forEach(a => {
                                const href = a.getAttribute('href');
                                // /recruitment/R*****/detail 형태의 URL 찾기
                                if (href && href.match(/\\/recruitment\\/R\\d+\\/detail/)) {
                                    links.push(href);
                                }
                            });
                            return [...new Set(links)];  // 중복 제거
                        }
                    """)

                    # 링크 업데이트
                    for href in result:
                        try:
                            full_url = self._normalize_url(href)
                            if full_url not in job_links:
                                job_links.append(full_url)
                        except:
                            continue

                    logger.debug(f"스크롤 {scroll_attempts}: {len(job_links)}개 공고 발견")

                    # 새로운 공고가 로드되지 않으면 종료
                    if len(job_links) == previous_count:
                        logger.info("더 이상 새로운 공고가 로드되지 않음. 스크롤 종료")
                        break

                    previous_count = len(job_links)

                    # 페이지 끝까지 스크롤
                    await page.evaluate("() => window.scrollTo(0, document.documentElement.scrollHeight)")
                    await asyncio.sleep(1.5)  # 새 콘텐츠 로드 대기

                except Exception as e:
                    logger.warning(f"스크롤 중 오류: {e}")
                    break

                scroll_attempts += 1

            logger.info(f"총 {len(job_links)}개의 채용공고 링크 추출 (스크롤 {scroll_attempts}회)")

            return job_links

        except Exception as e:
            logger.error(f"채용공고 링크 추출 실패: {e}", exc_info=True)
            return []

    async def parse_job_detail(self, page: Page, url: str, idx: int = 0) -> Optional[Dict]:
        """채용공고 상세 페이지 파싱"""
        try:
            logger.info(f"공고 파싱 중: {url}")
            await page.goto(url, wait_until='domcontentloaded', timeout=60000)

            # JavaScript 로드 대기 (더 충분한 시간)
            await asyncio.sleep(4)  # 4초 대기

            job_data = {
                "url": url,
                "title": "",
                "posting_date": "",
                "closing_date": "",
                "location": "",
                "employment_type": "정규직",
                "company_description": "",
                "team_description": "",
                "job_description": "",
                "required_qualifications": "",
                "preferred_qualifications": "",
                "recruitment_schedule": "",
                "selection_process": "",
                "notes": "",
                "privacy_policy": "",
                "document_return_policy": "",
                "development_environment": "",
                "key_technologies": "",
                "screenshot_path": "",
                "crawled_at": datetime.now().isoformat()
            }

            # JavaScript로 제목과 본문 함께 추출 (우아한형제들 특화)
            try:
                result = await page.evaluate("""
                    () => {
                        const data = {};

                        // 제목 추출
                        const titleEl = document.querySelector('.recruit-detail-title-inner');
                        if (titleEl) {
                            let text = titleEl.textContent.trim();
                            // [직군] 형식에서 실제 직종명 추출
                            const match = text.match(/\\[(.*?)\\]\\s*([^\\[]+)/);
                            if (match && match[2]) {
                                data.title = match[2].trim().substring(0, 150);
                            } else {
                                data.title = text.substring(0, 150);
                            }
                        } else {
                            // h1 태그 시도
                            const h1 = document.querySelector('h1');
                            if (h1) {
                                let text = h1.textContent.trim();
                                const match = text.match(/\\[(.*?)\\]\\s*(.+?)(?=\\[|$)/);
                                data.title = match && match[2] ? match[2].trim() : text.substring(0, 150);
                            }
                        }

                        // 본문 추출 (detail-view.editor-viewer)
                        const detailView = document.querySelector('.detail-view.editor-viewer');
                        if (detailView) {
                            const fullText = detailView.textContent.trim();
                            if (fullText && fullText.length > 10) {
                                data.jobDescription = fullText.substring(0, 10000);
                            }
                        }

                        // 만약 detail-view.editor-viewer가 없으면 .detail-view만 시도
                        if (!data.jobDescription) {
                            const detailViewOnly = document.querySelector('.detail-view');
                            if (detailViewOnly) {
                                const fullText = detailViewOnly.textContent.trim();
                                if (fullText && fullText.length > 10) {
                                    data.jobDescription = fullText.substring(0, 10000);
                                }
                            }
                        }

                        return data;
                    }
                """)
                job_data["title"] = result.get("title", "")
                job_data["job_description"] = result.get("jobDescription", "")

                logger.debug(f"추출된 제목: {job_data['title'][:50] if job_data['title'] else '(비어있음)'}")
                logger.debug(f"추출된 본문 길이: {len(job_data['job_description'])} 문자")

            except Exception as e:
                logger.warning(f"JavaScript 제목/본문 추출 실패: {e}")
                job_data["title"] = ""
                job_data["job_description"] = ""

            # 메타데이터 추출
            job_data["posting_date"] = await self._extract_meta(
                page,
                '게시일',
                '공고일'
            )
            job_data["closing_date"] = await self._extract_meta(
                page,
                '마감일',
                '마감'
            )
            job_data["location"] = await self._extract_meta(
                page,
                '근무지',
                '위치'
            )

            # 섹션별 내용 추출
            sections = await self._extract_sections(page)

            logger.debug(f"추출된 섹션: {list(sections.keys())}")

            # 우아한형제들 섹션 매핑
            section_mapping = {
                '회사소개': 'company_description',
                '조직소개': 'team_description',
                '팀소개': 'team_description',
                '지원자격': 'required_qualifications',
                '자격요건': 'required_qualifications',
                '우대사항': 'preferred_qualifications',
                '채용일정': 'recruitment_schedule',
                '채용 일정': 'recruitment_schedule',
                '전형절차': 'selection_process',
                '전형 절차': 'selection_process',
                '참고사항': 'notes',
                '필독사항': 'notes',
                '개인정보처리방침': 'privacy_policy',
                '개인정보 처리방침': 'privacy_policy',
                '서류반환정책': 'document_return_policy',
                '서류 반환 정책': 'document_return_policy',
                '개발환경': 'development_environment',
                '주요기술': 'key_technologies',
                '기술스택': 'key_technologies'
            }

            # 섹션 매핑 적용
            if sections:
                logger.info(f"추출된 섹션: {list(sections.keys())}")

            for section_title, content in sections.items():
                matched = False
                for kr_title, field_name in section_mapping.items():
                    # 정확한 매칭 또는 포함 관계 확인
                    if kr_title == section_title or kr_title in section_title:
                        # job_description은 이미 전체 본문으로 채워졌으므로 스킵
                        if field_name != 'job_description':
                            job_data[field_name] = content[:2000]  # 최대 2000자
                            logger.info(f"섹션 매핑: '{section_title}' → '{field_name}' ({len(content)} 문자)")
                            matched = True
                        break

                if not matched:
                    logger.debug(f"매핑 안 됨: '{section_title}'")

            # 스크린샷 저장
            screenshot_path = await self._save_screenshot(page, idx, job_data["title"])
            if screenshot_path:
                job_data["screenshot_path"] = screenshot_path

            logger.info(f"파싱 완료: {job_data['title']}")
            return job_data

        except Exception as e:
            logger.error(f"공고 파싱 실패 ({url}): {e}")
            return None

    async def _extract_text(self, page: Page, selector: str) -> str:
        """텍스트 추출"""
        try:
            elements = await page.locator(selector).all()
            if elements:
                text = await elements[0].text_content()
                return text.strip() if text else ""
        except Exception as e:
            logger.debug(f"텍스트 추출 실패 ({selector}): {e}")
        return ""

    async def _extract_meta(self, page: Page, *keywords) -> str:
        """메타데이터 추출"""
        try:
            # 페이지의 모든 텍스트 내용 가져오기
            text = await page.locator('body').text_content()

            for keyword in keywords:
                pattern = rf'{keyword}\s*[:：]\s*([^\n\r]+)'
                match = re.search(pattern, text)
                if match:
                    value = match.group(1).strip()
                    # 날짜 형식 확인
                    if re.search(r'\d{4}[-/\.]\d{1,2}[-/\.]\d{1,2}', value):
                        return value
                    # 지역 정보의 경우
                    if keyword == '근무지' or keyword == '위치':
                        return value.split('\n')[0].strip()

            return ""
        except Exception as e:
            logger.debug(f"메타데이터 추출 실패: {e}")
            return ""

    async def _extract_sections(self, page: Page) -> Dict[str, str]:
        """섹션별 내용 추출 (강화된 파싱)"""
        sections = {}

        try:
            # 상세한 섹션 추출
            logger.debug("섹션별 데이터 추출 중...")
            result = await page.evaluate("""
                () => {
                    const sections = {};
                    const detailView = document.querySelector('.detail-view, .recruit-detail');
                    if (!detailView) return sections;

                    // 전체 텍스트 콘텐츠 가져오기
                    const fullText = detailView.innerText;

                    // 정규식을 사용하여 섹션 분리
                    // [섹션명] 패턴으로 섹션 찾기
                    const sectionPattern = /\\[([^\\[\\]]+)\\]/g;
                    const matches = Array.from(fullText.matchAll(sectionPattern));

                    matches.forEach((match, idx) => {
                        const title = match[1].trim();
                        const startIndex = match.index + match[0].length;

                        // 다음 섹션의 시작점 또는 텍스트의 끝
                        let endIndex = fullText.length;
                        if (idx < matches.length - 1) {
                            endIndex = matches[idx + 1].index;
                        }

                        // 섹션 내용 추출
                        let content = fullText.substring(startIndex, endIndex)
                            .trim()
                            .split('\\n')
                            .filter(line => line.trim().length > 0)
                            .slice(0, 100) // 최대 100줄
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

    async def _save_screenshot(self, page: Page, idx: int, title: str) -> Optional[str]:
        """페이지 스크린샷 저장"""
        try:
            if not self.screenshot_dir:
                return None

            # 파일명 생성 (제목에서 특수문자 제거)
            safe_title = re.sub(r'[<>:"/\\|?*]', '', title)[:50]
            filename = f"{idx:03d}_{safe_title}.png"
            filepath = self.screenshot_dir / filename

            # 전체 페이지 스크린샷 저장
            await page.screenshot(path=str(filepath), full_page=True)

            logger.info(f"스크린샷 저장: {filepath}")
            return str(filepath)

        except Exception as e:
            logger.warning(f"스크린샷 저장 실패: {e}")
            return None

    def _normalize_url(self, url: str) -> str:
        """URL 정규화"""
        if url.startswith('http'):
            return url
        elif url.startswith('/'):
            return f"https://career.woowahan.com{url}"
        else:
            return f"https://career.woowahan.com/{url}"

    async def crawl(self, max_jobs: Optional[int] = None):
        """크롤링 시작"""
        # 스크린샷 디렉토리 설정
        self._setup_screenshot_dir()

        async with async_playwright() as p:
            browser, context = await self.init_browser(p)

            try:
                page = await context.new_page()

                # 1. 채용공고 링크 추출
                self.job_links = await self.extract_job_links(page)

                if max_jobs:
                    self.job_links = self.job_links[:max_jobs]

                # 2. 각 공고 상세 파싱
                total = len(self.job_links)
                for idx, link in enumerate(self.job_links, 1):
                    logger.info(f"진행률: {idx}/{total}")

                    job_data = await self.parse_job_detail(page, link, idx)
                    if job_data:
                        self.jobs.append(job_data)
                        await self._write_jsonl(job_data)

                    # 크롤링 속도 제한
                    await asyncio.sleep(1.5)

                logger.info(f"크롤링 완료: {len(self.jobs)}개 공고")

            finally:
                await context.close()
                await browser.close()

    async def _write_jsonl(self, job_data: Dict):
        """JSONL 형식으로 저장"""
        if not self.output_file:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            self.output_file = Path(f"woowahan_jobs_{timestamp}.jsonl")

        with open(self.output_file, 'a', encoding='utf-8') as f:
            f.write(json.dumps(job_data, ensure_ascii=False) + '\n')

    async def save_summary(self):
        """요약 정보 저장"""
        if not self.output_file:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            self.output_file = Path(f"woowahan_jobs_{timestamp}.jsonl")

        summary_file = self.output_file.with_suffix('.summary.json')
        summary = {
            "total_jobs": len(self.jobs),
            "crawled_at": datetime.now().isoformat(),
            "output_file": str(self.output_file),
            "screenshot_directory": str(self.screenshot_dir) if self.screenshot_dir else None,
            "jobs": self.jobs
        }

        with open(summary_file, 'w', encoding='utf-8') as f:
            json.dump(summary, f, ensure_ascii=False, indent=2)

        logger.info(f"요약 파일 저장: {summary_file}")
        logger.info(f"스크린샷 폴더: {self.screenshot_dir}")


async def main():
    crawler = WoowahanCrawler()

    try:
        # 테스트를 위해 처음 5개만 크롤링
        await crawler.crawl(max_jobs=None)
        await crawler.save_summary()

        logger.info("크롤링 완료!")

    except Exception as e:
        logger.error(f"크롤링 중 오류 발생: {e}")
        raise


if __name__ == "__main__":
    asyncio.run(main())
