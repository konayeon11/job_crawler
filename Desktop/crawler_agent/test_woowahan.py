#!/usr/bin/env python3
"""
우아한형제들 크롤러 테스트 스크립트
"""

import asyncio
import json
import logging
from datetime import datetime
from pathlib import Path
from crawlers import WoowahanCrawler

# 로깅 설정
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler("woowahan_test.log"),
        logging.StreamHandler(),
    ],
)
logger = logging.getLogger(__name__)


async def test_woowahan_crawler():
    """우아한형제들 크롤러 테스트"""
    try:
        from playwright.async_api import async_playwright

        crawler = WoowahanCrawler()

        logger.info(f"크롤러: {crawler.get_company_name()}")
        logger.info(f"대기 시간: {crawler.get_wait_time()}초")
        logger.info(f"Playwright 필요: {crawler.requires_playwright()}")
        logger.info(f"Selenium 필요: {crawler.requires_selenium()}")

        logger.info("\n=== 채용 목록 페이지 URL ===")
        urls = crawler.get_job_list_urls()
        for url in urls:
            logger.info(f"  - {url}")

        # Playwright 브라우저 초기화
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            context = await browser.new_context()
            page = await context.new_page()

            # 채용공고 링크 추출
            logger.info("\n=== 채용공고 링크 추출 ===")
            job_links = await crawler.extract_job_links(page)
            logger.info(f"추출된 공고 링크: {len(job_links)}개")

            if job_links:
                logger.info("첫 5개 링크:")
                for link in job_links[:5]:
                    logger.info(f"  - {link}")

                # 첫 번째 공고 상세 정보 추출 테스트
                logger.info("\n=== 첫 번째 공고 상세 정보 추출 ===")
                if job_links:
                    job_data = await crawler.parse_job_detail_async(
                        page, job_links[0], 1
                    )
                    if job_data:
                        logger.info(f"제목: {job_data.get('title', 'N/A')}")
                        logger.info(f"URL: {job_data.get('url', 'N/A')}")
                        logger.info(f"공고 ID: {job_data.get('job_id', 'N/A')}")
                        logger.info(f"근무지: {job_data.get('location', 'N/A')}")
                        logger.info(f"게시일: {job_data.get('posting_date', 'N/A')}")
                        logger.info(f"마감일: {job_data.get('closing_date', 'N/A')}")

                        # 결과 저장
                        results_file = Path("woowahan_test_result.json")
                        with open(results_file, "w", encoding="utf-8") as f:
                            json.dump(job_data, f, ensure_ascii=False, indent=2)
                        logger.info(f"\n결과 저장: {results_file}")

            await context.close()
            await browser.close()

        logger.info("\n✅ 테스트 완료!")

    except ImportError as e:
        logger.error(f"Playwright가 설치되지 않았습니다: {e}")
        logger.info("설치 방법: pip install playwright")
    except Exception as e:
        logger.error(f"테스트 중 오류 발생: {e}", exc_info=True)


if __name__ == "__main__":
    asyncio.run(test_woowahan_crawler())
