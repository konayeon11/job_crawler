from abc import ABC, abstractmethod
from typing import List, Dict, Optional


class BaseCrawler(ABC):
    """
    모든 회사 크롤러가 구현해야 하는 추상 기본 클래스
    """

    @abstractmethod
    def get_company_name(self) -> str:
        """회사명 반환"""
        pass

    @abstractmethod
    def get_job_list_urls(self) -> List[str]:
        """채용 목록 페이지 URL 리스트 반환"""
        pass

    @abstractmethod
    def extract_job_urls(self, html: str) -> List[Dict[str, str]]:
        """
        HTML에서 개별 공고 URL 추출

        Returns:
            [{'url': '...', 'job_id': '...', 'title': '...'}]
        """
        pass

    @abstractmethod
    def get_wait_time(self) -> int:
        """PDF 캡처 대기 시간(초)"""
        pass

    @abstractmethod
    def requires_selenium(self) -> bool:
        """동적 페이지 여부 (True/False)"""
        pass

    def requires_playwright(self) -> bool:
        """Playwright 사용 여부 (기본값: False)"""
        return False

    def get_retry_count(self) -> int:
        """재시도 횟수 (기본값: 3)"""
        return 3

    def get_timeout(self) -> int:
        """타임아웃 시간(초) (기본값: 30)"""
        return 30
