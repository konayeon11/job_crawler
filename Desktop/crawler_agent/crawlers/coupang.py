from typing import List, Dict
from bs4 import BeautifulSoup
from .base_crawler import BaseCrawler


class CoupangCrawler(BaseCrawler):
    """
    쿠팡 채용 공고 크롤러
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
            "https://www.coupang.com/np/pages/whatsnew/careers",
        ]

    def extract_job_urls(self, html: str) -> List[Dict[str, str]]:
        """
        HTML에서 개별 공고 URL 추출

        Args:
            html: BeautifulSoup으로 파싱할 HTML 문자열

        Returns:
            [{'url': '...', 'job_id': '...', 'title': '...'}] 형식의 리스트
        """
        soup = BeautifulSoup(html, "html.parser")
        job_list = []

        # 쿠팡 특화 선택자로 공고 컨테이너 찾기
        # 공고 항목들을 찾는 선택자 (실제 구조에 맞게 조정 필요)
        job_items = soup.select(".job-list-item, .job-posting, [data-job-id]")

        for idx, item in enumerate(job_items, 1):
            try:
                # 링크 찾기
                link = item.find("a", href=True)
                if not link:
                    continue

                url = link.get("href", "")
                # 상대경로인 경우 절대경로로 변환
                if url and not url.startswith("http"):
                    url = "https://www.coupang.com" + url

                # 제목 추출
                title_elem = item.find(["h2", "h3", "span"], class_=lambda x: x and "title" in x.lower())
                title = title_elem.get_text(strip=True) if title_elem else f"Job {idx}"

                # job_id 추출 (없으면 생성)
                job_id = item.get("data-job-id") or url.split("/")[-1] or f"coupang_{idx}"

                if url:
                    job_list.append({
                        "url": url,
                        "job_id": str(job_id),
                        "title": title
                    })

            except Exception as e:
                print(f"Error extracting job item {idx}: {e}")
                continue

        return job_list

    def get_wait_time(self) -> int:
        """
        PDF 캡처 대기 시간(초)

        쿠팡은 일부 콘텐츠가 lazy-loading되므로 적당한 대기 필요
        """
        return 5

    def requires_selenium(self) -> bool:
        """
        동적 페이지 여부

        쿠팡 채용공고 목록은 동적으로 로드되므로 Selenium 필요
        """
        return True
