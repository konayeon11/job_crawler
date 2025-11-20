import asyncio
import logging
from typing import Optional
from pathlib import Path

logger = logging.getLogger(__name__)


class PlaywrightCaptureAgent:
    """
    Playwright를 사용하여 웹페이지를 이미지로 캡처하는 Agent
    동적 콘텐츠 로드에 최적화되어 있음
    """

    def __init__(self, headless: bool = True):
        """
        PlaywrightCaptureAgent 초기화

        Args:
            headless: 헤드리스 모드 사용 여부
        """
        self.headless = headless

    async def capture_as_image(
        self,
        url: str,
        wait_time: int = 5,
        timeout: int = 60000,
        scroll: bool = True,
        image_format: str = "png"
    ) -> Optional[bytes]:
        """
        Playwright로 웹페이지를 이미지로 캡처

        Args:
            url: 캡처할 URL
            wait_time: 페이지 로드 후 대기 시간(초)
            timeout: 페이지 로드 타임아웃(밀리초)
            scroll: 전체 페이지 스크롤 여부
            image_format: 이미지 포맷 ('png' 또는 'jpeg')

        Returns:
            이미지 바이너리 데이터 또는 None (실패 시)
        """
        try:
            from playwright.async_api import async_playwright

            async with async_playwright() as p:
                browser = await p.chromium.launch(headless=self.headless)
                context = await browser.new_context(
                    viewport={"width": 1920, "height": 1080}
                )
                page = await context.new_page()

                try:
                    logger.info(f"Navigating to: {url}")

                    # 페이지 로드
                    await page.goto(url, wait_until="networkidle", timeout=timeout)
                    await asyncio.sleep(wait_time)

                    # 전체 페이지 스크롤 (lazy-loading 콘텐츠 로드)
                    if scroll:
                        await self._scroll_page(page)

                    logger.info(f"Capturing page as {image_format.upper()} image...")

                    # 이미지로 캡처 (현재 viewport 크기만 캡처 - 길이 제한)
                    image_bytes = await page.screenshot(
                        path=None,
                        full_page=False,
                        type=image_format,
                        quality=95 if image_format == "jpeg" else None
                    )

                    logger.info(f"Image captured successfully from {url}")
                    return image_bytes

                finally:
                    await context.close()
                    await browser.close()

        except Exception as e:
            logger.error(f"Error capturing image from {url}: {e}")
            return None

    async def capture_as_pdf(
        self,
        url: str,
        wait_time: int = 5,
        timeout: int = 60000,
        scroll: bool = True
    ) -> Optional[bytes]:
        """
        (호환성 유지) Playwright로 웹페이지를 이미지로 캡처

        주의: 이전 PDF 캡처 대신 이미지 캡처를 수행합니다.

        Args:
            url: 캡처할 URL
            wait_time: 페이지 로드 후 대기 시간(초)
            timeout: 페이지 로드 타임아웃(밀리초)
            scroll: 전체 페이지 스크롤 여부

        Returns:
            이미지 바이너리 데이터 또는 None (실패 시)
        """
        logger.warning("capture_as_pdf() is deprecated, using capture_as_image() instead")
        return await self.capture_as_image(
            url=url,
            wait_time=wait_time,
            timeout=timeout,
            scroll=scroll,
            image_format="png"
        )

    async def _scroll_page(self, page) -> None:
        """
        전체 페이지를 스크롤하여 lazy-loading 콘텐츠 로드

        Args:
            page: Playwright page 객체
        """
        try:
            last_height = await page.evaluate("document.body.scrollHeight")

            while True:
                # 아래로 스크롤
                await page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
                await asyncio.sleep(1)

                # 새로운 스크롤 높이
                new_height = await page.evaluate("document.body.scrollHeight")

                if new_height == last_height:
                    break

                last_height = new_height

            # 페이지 상단으로 스크롤
            await page.evaluate("window.scrollTo(0, 0)")
            await asyncio.sleep(1)

        except Exception as e:
            logger.warning(f"Error during page scrolling: {e}")

    async def capture_as_image_bulk(
        self,
        urls: list,
        wait_time: int = 5,
        timeout: int = 60000,
        scroll: bool = True,
        image_format: str = "png"
    ) -> dict:
        """
        여러 URL을 이미지로 캡처

        Args:
            urls: 캡처할 URL 리스트
            wait_time: 페이지 로드 후 대기 시간(초)
            timeout: 페이지 로드 타임아웃(밀리초)
            scroll: 전체 페이지 스크롤 여부
            image_format: 이미지 포맷 ('png' 또는 'jpeg')

        Returns:
            {url: image_bytes} 또는 {url: None} (실패 시)
        """
        results = {}

        for url in urls:
            try:
                image_bytes = await self.capture_as_image(
                    url=url,
                    wait_time=wait_time,
                    timeout=timeout,
                    scroll=scroll,
                    image_format=image_format
                )
                results[url] = image_bytes
            except Exception as e:
                logger.error(f"Failed to capture {url}: {e}")
                results[url] = None

        return results

    async def capture_as_pdf_bulk(
        self,
        urls: list,
        wait_time: int = 5,
        timeout: int = 60000,
        scroll: bool = True
    ) -> dict:
        """
        (호환성 유지) 여러 URL을 이미지로 캡처

        주의: PDF 대신 이미지로 캡처합니다.

        Args:
            urls: 캡처할 URL 리스트
            wait_time: 페이지 로드 후 대기 시간(초)
            timeout: 페이지 로드 타임아웃(밀리초)
            scroll: 전체 페이지 스크롤 여부

        Returns:
            {url: image_bytes} 또는 {url: None} (실패 시)
        """
        logger.warning("capture_as_pdf_bulk() is deprecated, using capture_as_image_bulk() instead")
        return await self.capture_as_image_bulk(
            urls=urls,
            wait_time=wait_time,
            timeout=timeout,
            scroll=scroll,
            image_format="png"
        )
