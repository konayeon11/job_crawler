"""
크롤링 방식 및 결과 비교 분석 도구

사용 방법:
    python crawling_comparison.py [--output html|json|csv]

기능:
    1. 데이터베이스에서 모든 공고 조회
    2. 도메인별 크롤링 방식 분석
    3. 추출 결과 비교
    4. 성능 지표 계산
    5. 결과 리포트 생성
"""

import os
import sys
import json
import sqlite3
from datetime import datetime
from typing import Dict, List, Tuple, Any
from collections import defaultdict

os.environ['PYTHONIOENCODING'] = 'utf-8'
sys.stdout.reconfigure(encoding='utf-8')

# ============================================================================
# 데이터 모델
# ============================================================================

class CrawlingMethod:
    """크롤링 방식 정의"""

    METHODS = {
        'careers.kakao.com': {
            'name': 'REST API 직접 호출',
            'type': 'API',
            'estimated_time': 6,  # 초
            'estimated_speed': '매우 빠름',
            'reliability': '100%',
            'description': 'Kakao 공식 REST API 사용',
            'pros': ['빠름', '신뢰도 높음', '공식 API'],
            'cons': ['API 변경 가능성'],
        },
        'recruit.navercorp.com': {
            'name': '하이브리드 (Selenium + JSON-LD + 정규식)',
            'type': 'Hybrid',
            'estimated_time': 30,  # 초
            'estimated_speed': '느림',
            'reliability': '89%',
            'description': 'Selenium 렌더링 + JSON-LD + 정규식 패턴',
            'pros': ['동적 콘텐츠 지원', '상세 정보 추출', 'API 불필요'],
            'cons': ['느림', 'Selenium 의존성', '메모리 사용 많음'],
        },
        'general': {
            'name': 'OpenAI 기반 분석',
            'type': 'AI',
            'estimated_time': 15,  # 초
            'estimated_speed': '보통',
            'reliability': '95%',
            'description': 'OpenAI로 페이지 분석 후 CSS 선택자 추출',
            'pros': ['범용성', '자동 분석', '대부분 사이트 지원'],
            'cons': ['비용 발생', '부정확할 수 있음'],
        },
    }

    @classmethod
    def get_method(cls, domain: str) -> Dict[str, Any]:
        """도메인에 맞는 크롤링 방식 반환"""
        for key, method in cls.METHODS.items():
            if key in domain:
                return method
        return cls.METHODS['general']


class ExtractionAnalysis:
    """추출 결과 분석"""

    FIELDS = [
        'title', 'company', 'location', 'introduction',
        'work_content', 'qualification', 'work_condition',
        'recruitment_process', 'skills'
    ]

    @staticmethod
    def check_field(value: Any) -> bool:
        """필드 추출 여부 확인"""
        if value is None:
            return False
        if isinstance(value, str) and len(value.strip()) == 0:
            return False
        if isinstance(value, list) and len(value) == 0:
            return False
        return True

    @staticmethod
    def get_field_value(cursor, job_id: str, field: str) -> Any:
        """특정 필드 값 조회"""
        cursor.execute(f'SELECT {field} FROM job_postings WHERE id = ?', (job_id,))
        result = cursor.fetchone()
        return result[0] if result else None

    @staticmethod
    def calculate_extraction_rate(job_data: Dict[str, Any]) -> Tuple[int, int, float]:
        """추출률 계산 (추출된 필드수, 전체필드수, 추출률%)"""
        extracted = sum(1 for field in ExtractionAnalysis.FIELDS
                       if ExtractionAnalysis.check_field(job_data.get(field)))
        total = len(ExtractionAnalysis.FIELDS)
        rate = (extracted / total * 100) if total > 0 else 0
        return extracted, total, rate


# ============================================================================
# 데이터베이스 쿼리
# ============================================================================

class DatabaseQuery:
    """데이터베이스 쿼리 클래스"""

    def __init__(self, db_path: str = r'C:\Users\SKAX\Desktop\kr-job-crawler\kr-job-crawler\jobs.db'):
        self.db_path = db_path
        self.conn = None

    def connect(self):
        """데이터베이스 연결"""
        try:
            self.conn = sqlite3.connect(self.db_path)
            self.conn.row_factory = sqlite3.Row
            return True
        except Exception as e:
            print(f"DB 연결 실패: {str(e)}")
            return False

    def close(self):
        """데이터베이스 연결 종료"""
        if self.conn:
            self.conn.close()

    def get_all_jobs(self) -> List[Dict[str, Any]]:
        """모든 공고 조회"""
        cursor = self.conn.cursor()
        cursor.execute("""
            SELECT id, domain, title, company, location, introduction,
                   work_content, qualification, work_condition,
                   recruitment_process, skills, created_at
            FROM job_postings
            ORDER BY domain, created_at DESC
        """)

        jobs = []
        for row in cursor.fetchall():
            jobs.append(dict(row))
        return jobs

    def get_jobs_by_domain(self, domain: str) -> List[Dict[str, Any]]:
        """도메인별 공고 조회"""
        cursor = self.conn.cursor()
        cursor.execute("""
            SELECT id, domain, title, company, location, introduction,
                   work_content, qualification, work_condition,
                   recruitment_process, skills, created_at
            FROM job_postings
            WHERE domain = ?
            ORDER BY created_at DESC
        """, (domain,))

        jobs = []
        for row in cursor.fetchall():
            jobs.append(dict(row))
        return jobs

    def get_domain_stats(self) -> Dict[str, int]:
        """도메인별 공고 수 통계"""
        cursor = self.conn.cursor()
        cursor.execute("""
            SELECT domain, COUNT(*) as count
            FROM job_postings
            GROUP BY domain
            ORDER BY count DESC
        """)

        stats = {}
        for row in cursor.fetchall():
            stats[row[0]] = row[1]
        return stats


# ============================================================================
# 분석 및 리포트 생성
# ============================================================================

class AnalysisReport:
    """분석 리포트 생성"""

    def __init__(self, jobs: List[Dict[str, Any]]):
        self.jobs = jobs
        self.analysis = self._analyze()

    def _analyze(self) -> Dict[str, Any]:
        """전체 분석 수행"""
        analysis = {
            'total_jobs': len(self.jobs),
            'by_domain': self._analyze_by_domain(),
            'extraction_stats': self._analyze_extraction(),
            'field_stats': self._analyze_fields(),
        }
        return analysis

    def _analyze_by_domain(self) -> Dict[str, Any]:
        """도메인별 분석"""
        by_domain = defaultdict(list)
        for job in self.jobs:
            by_domain[job['domain']].append(job)

        result = {}
        for domain, jobs in by_domain.items():
            method = CrawlingMethod.get_method(domain)

            # 추출률 계산
            extracted_counts = []
            for job in jobs:
                extracted, total, rate = ExtractionAnalysis.calculate_extraction_rate(job)
                extracted_counts.append((extracted, total))

            avg_extracted = sum(e[0] for e in extracted_counts) / len(extracted_counts) if extracted_counts else 0
            avg_rate = (avg_extracted / (extracted_counts[0][1] if extracted_counts else 9) * 100) if extracted_counts else 0

            result[domain] = {
                'count': len(jobs),
                'method': method['name'],
                'type': method['type'],
                'estimated_time': method['estimated_time'],
                'reliability': method['reliability'],
                'avg_extraction_rate': round(avg_rate, 1),
                'description': method['description'],
                'pros': method['pros'],
                'cons': method['cons'],
            }

        return result

    def _analyze_extraction(self) -> Dict[str, Any]:
        """추출률 분석"""
        extraction_rates = []
        for job in self.jobs:
            extracted, total, rate = ExtractionAnalysis.calculate_extraction_rate(job)
            extraction_rates.append({
                'domain': job['domain'],
                'title': job['title'],
                'extracted': extracted,
                'total': total,
                'rate': rate,
            })

        return {
            'total_analyzed': len(extraction_rates),
            'avg_rate': round(sum(r['rate'] for r in extraction_rates) / len(extraction_rates), 1) if extraction_rates else 0,
            'min_rate': round(min(r['rate'] for r in extraction_rates), 1) if extraction_rates else 0,
            'max_rate': round(max(r['rate'] for r in extraction_rates), 1) if extraction_rates else 0,
            'details': extraction_rates[:5],  # 최상위 5개만
        }

    def _analyze_fields(self) -> Dict[str, Any]:
        """필드별 추출률"""
        field_stats = {}

        for field in ExtractionAnalysis.FIELDS:
            extracted = sum(1 for job in self.jobs
                          if ExtractionAnalysis.check_field(job.get(field)))
            total = len(self.jobs)
            rate = (extracted / total * 100) if total > 0 else 0

            field_stats[field] = {
                'extracted': extracted,
                'total': total,
                'rate': round(rate, 1),
            }

        return field_stats

    def print_summary(self):
        """콘솔 요약 출력"""
        print("\n" + "=" * 120)
        print("📊 크롤링 결과 분석 요약")
        print("=" * 120)

        # 전체 통계
        print(f"\n총 공고 수: {self.analysis['total_jobs']}개")
        print(f"평균 추출률: {self.analysis['extraction_stats']['avg_rate']:.1f}%")

        # 도메인별 분석
        print("\n" + "-" * 120)
        print("도메인별 크롤링 방식")
        print("-" * 120)

        for domain, info in self.analysis['by_domain'].items():
            print(f"\n🔗 {domain}")
            print(f"   공고 수: {info['count']}개")
            print(f"   방식: {info['method']}")
            print(f"   유형: {info['type']}")
            print(f"   예상 시간: {info['estimated_time']}초")
            print(f"   신뢰도: {info['reliability']}")
            print(f"   평균 추출률: {info['avg_extraction_rate']:.1f}%")
            print(f"   설명: {info['description']}")
            print(f"   장점: {', '.join(info['pros'])}")
            print(f"   단점: {', '.join(info['cons'])}")

        # 필드별 추출률
        print("\n" + "-" * 120)
        print("필드별 추출률")
        print("-" * 120)

        for field, stats in self.analysis['field_stats'].items():
            rate_bar = "█" * int(stats['rate'] / 10) + "░" * (10 - int(stats['rate'] / 10))
            status = "✓" if stats['rate'] == 100 else "⚠" if stats['rate'] >= 80 else "✗"
            print(f"{status} {field:20s} [{rate_bar}] {stats['rate']:5.1f}% ({stats['extracted']}/{stats['total']})")

        # 상세 추출 현황
        print("\n" + "-" * 120)
        print("공고별 추출 현황 (상위 5개)")
        print("-" * 120)

        for detail in self.analysis['extraction_stats']['details']:
            print(f"\n{detail['title']}")
            print(f"   도메인: {detail['domain']}")
            print(f"   추출률: {detail['rate']:.1f}% ({detail['extracted']}/{detail['total']})")

    def export_json(self, filename: str = 'crawling_analysis.json'):
        """JSON으로 내보내기"""
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(self.analysis, f, ensure_ascii=False, indent=2)
        print(f"✓ JSON 파일 저장: {filename}")

    def export_html(self, filename: str = 'crawling_analysis.html'):
        """HTML로 내보내기"""
        # 데이터 준비
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        total_jobs = self.analysis['total_jobs']
        avg_rate = self.analysis['extraction_stats']['avg_rate']
        max_rate = self.analysis['extraction_stats']['max_rate']
        min_rate = self.analysis['extraction_stats']['min_rate']

        # HTML 헤더 (f-string 사용)
        html_header = f"""<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <title>크롤링 분석 리포트</title>
    <style>
        body {{font-family: Arial, sans-serif; margin: 20px;}}
        h1 {{color: #333;}}
        table {{border-collapse: collapse; width: 100%; margin: 20px 0;}}
        th, td {{border: 1px solid #ddd; padding: 12px; text-align: left;}}
        th {{background-color: #4CAF50; color: white;}}
        tr:nth-child(even) {{background-color: #f2f2f2;}}
        .high {{color: green; font-weight: bold;}}
        .medium {{color: orange;}}
        .low {{color: red;}}
    </style>
</head>
<body>
    <h1>크롤링 결과 분석 리포트</h1>
    <p>생성일: {timestamp}</p>

    <h2>전체 통계</h2>
    <ul>
        <li>총 공고: {total_jobs}개</li>
        <li>평균 추출률: {avg_rate:.1f}%</li>
        <li>최고 추출률: {max_rate:.1f}%</li>
        <li>최저 추출률: {min_rate:.1f}%</li>
    </ul>

    <h2>도메인별 분석</h2>
    <table>
        <tr>
            <th>도메인</th>
            <th>공고 수</th>
            <th>크롤링 방식</th>
            <th>예상 시간</th>
            <th>평균 추출률</th>
        </tr>
"""
        html = html_header

        for domain, info in self.analysis['by_domain'].items():
            rate_class = 'high' if info['avg_extraction_rate'] >= 90 else 'medium' if info['avg_extraction_rate'] >= 70 else 'low'
            html += f"""
        <tr>
            <td>{domain}</td>
            <td>{info['count']}</td>
            <td>{info['method']}</td>
            <td>{info['estimated_time']}초</td>
            <td class="{rate_class}">{info['avg_extraction_rate']:.1f}%</td>
        </tr>
"""

        html += """
    </table>

    <h2>필드별 추출률</h2>
    <table>
        <tr>
            <th>필드</th>
            <th>추출됨</th>
            <th>전체</th>
            <th>추출률</th>
        </tr>
"""

        for field, stats in self.analysis['field_stats'].items():
            rate_class = 'high' if stats['rate'] >= 90 else 'medium' if stats['rate'] >= 70 else 'low'
            html += f"""
        <tr>
            <td>{field}</td>
            <td>{stats['extracted']}</td>
            <td>{stats['total']}</td>
            <td class="{rate_class}">{stats['rate']:.1f}%</td>
        </tr>
"""

        html += """
    </table>
</body>
</html>
"""

        with open(filename, 'w', encoding='utf-8') as f:
            f.write(html)
        print(f"✓ HTML 파일 저장: {filename}")


# ============================================================================
# 메인 실행
# ============================================================================

def main():
    """메인 함수"""
    print("=" * 120)
    print("🔍 크롤링 방식 및 결과 비교 분석")
    print("=" * 120)

    # 데이터베이스 연결
    db = DatabaseQuery()
    if not db.connect():
        return

    # 데이터 조회
    print("\n📂 데이터베이스에서 공고 조회 중...")
    jobs = db.get_all_jobs()

    if not jobs:
        print("❌ 저장된 공고가 없습니다.")
        db.close()
        return

    print(f"✓ {len(jobs)}개 공고 조회 완료")

    # 분석 수행
    print("\n📊 분석 수행 중...")
    report = AnalysisReport(jobs)

    # 결과 출력
    report.print_summary()

    # 파일 내보내기
    print("\n📁 결과 저장 중...")
    report.export_json()
    report.export_html()

    db.close()

    print("\n" + "=" * 120)
    print("✅ 분석 완료!")
    print("=" * 120)


if __name__ == '__main__':
    main()
