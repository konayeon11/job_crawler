from typing import List, Dict
from bs4 import BeautifulSoup
from .base_crawler import BaseCrawler


class NaverCrawler(BaseCrawler):
    """
    네이버 채용 공고 크롤러
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

        # 네이버 채용 특화 선택자로 공고 컨테이너 찾기
        job_items = soup.select(".job_item, .job-list-item, [data-recruit-seq]")

        for idx, item in enumerate(job_items, 1):
            try:
                # 링크 찾기
                link = item.find("a", href=True)
                if not link:
                    continue

                url = link.get("href", "")
                # 상대경로인 경우 절대경로로 변환
                if url and not url.startswith("http"):
                    url = "https://recruit.naver.com" + url

                # 제목 추출
                title_elem = item.find(["h2", "h3", "span"], class_=lambda x: x and "title" in x.lower())
                title = title_elem.get_text(strip=True) if title_elem else f"Job {idx}"

                # job_id 추출
                job_id = item.get("data-recruit-seq")
                if not job_id:
                    # URL에서 id 추출 시도
                    if "?recruitSeq=" in url:
                        job_id = url.split("?recruitSeq=")[-1].split("&")[0]
                    else:
                        job_id = f"naver_{idx}"

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

        네이버는 비교적 빠르게 로드됨
        """
        return 3

    def requires_selenium(self) -> bool:
        """
        동적 페이지 여부

        네이버 채용공고는 정적 페이지인 경우가 많음
        """
        return False
