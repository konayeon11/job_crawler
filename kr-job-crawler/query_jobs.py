"""
크롤링된 채용공고 데이터 조회 및 분석

사용법:
  python query_jobs.py               # 모든 공고 조회
  python query_jobs.py --company 카카오    # 특정 회사 공고만
  python query_jobs.py --keyword 파이썬    # 키워드로 검색
"""

import sys
import os
import sqlite3
import json
import argparse
from datetime import datetime

# UTF-8 인코딩 설정
os.environ['PYTHONIOENCODING'] = 'utf-8'
sys.stdout.reconfigure(encoding='utf-8')

DB_PATH = r'C:\Users\SKAX\Desktop\kr-job-crawler\kr-job-crawler\jobs.db'

def print_job(job_row):
    """공고 정보를 포맷팅하여 출력"""
    job_id, domain, title, company, location, source_url, intro, skills_json = job_row

    print(f"\n{'=' * 100}")
    print(f"📌 {title}")
    print(f"{'=' * 100}")
    print(f"회사: {company}")
    print(f"위치: {location}")
    print(f"도메인: {domain}")
    print(f"URL: {source_url}")

    if intro:
        intro_short = intro[:200] + "..." if len(intro) > 200 else intro
        print(f"소개: {intro_short}")

    if skills_json and skills_json != '[]':
        try:
            skills = json.loads(skills_json)
            if skills:
                print(f"기술: {', '.join(skills[:10])}")  # 최대 10개만
        except:
            pass

def query_all_jobs():
    """모든 공고 조회"""
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()

        cursor.execute('''
            SELECT id, domain, title, company, location, source_url,
                   introduction, skills
            FROM job_postings
            ORDER BY created_at DESC
        ''')

        rows = cursor.fetchall()

        if not rows:
            print("❌ 저장된 공고가 없습니다.")
            print("먼저 smart_crawler.py로 데이터를 크롤링하세요.")
            return

        print(f"\n✅ 총 {len(rows)}개 공고 조회됨\n")

        for row in rows[:20]:  # 최대 20개만 표시
            print_job(row)

        if len(rows) > 20:
            print(f"\n... (외 {len(rows) - 20}개 생략)")

        conn.close()

        # 통계
        print_statistics()

    except Exception as e:
        print(f"❌ 조회 오류: {str(e)}")

def query_by_company(company_name):
    """특정 회사의 공고 조회"""
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()

        cursor.execute('''
            SELECT id, domain, title, company, location, source_url,
                   introduction, skills
            FROM job_postings
            WHERE company LIKE ?
            ORDER BY created_at DESC
        ''', (f'%{company_name}%',))

        rows = cursor.fetchall()

        if not rows:
            print(f"❌ '{company_name}'에 관련된 공고가 없습니다.")
            return

        print(f"\n✅ '{company_name}'의 {len(rows)}개 공고 조회됨\n")

        for row in rows:
            print_job(row)

        conn.close()

    except Exception as e:
        print(f"❌ 조회 오류: {str(e)}")

def search_keyword(keyword):
    """키워드로 검색"""
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()

        search_term = f'%{keyword}%'
        cursor.execute('''
            SELECT id, domain, title, company, location, source_url,
                   introduction, skills
            FROM job_postings
            WHERE title LIKE ?
               OR introduction LIKE ?
               OR work_content LIKE ?
               OR qualification LIKE ?
            ORDER BY created_at DESC
        ''', (search_term, search_term, search_term, search_term))

        rows = cursor.fetchall()

        if not rows:
            print(f"❌ '{keyword}' 관련 공고가 없습니다.")
            return

        print(f"\n✅ '{keyword}' 키워드로 {len(rows)}개 공고 찾음\n")

        for row in rows:
            print_job(row)

        conn.close()

    except Exception as e:
        print(f"❌ 검색 오류: {str(e)}")

def print_statistics():
    """저장된 데이터 통계"""
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()

        print(f"\n{'=' * 100}")
        print("📊 통계")
        print(f"{'=' * 100}")

        # 총 공고 수
        cursor.execute('SELECT COUNT(*) FROM job_postings')
        total = cursor.fetchone()[0]
        print(f"총 공고 수: {total}개")

        # 회사별 공고 수
        cursor.execute('''
            SELECT company, COUNT(*) as cnt
            FROM job_postings
            GROUP BY company
            ORDER BY cnt DESC
        ''')

        companies = cursor.fetchall()
        print(f"\n회사별 공고 수:")
        for company, count in companies[:5]:
            print(f"  - {company}: {count}개")

        if len(companies) > 5:
            print(f"  ... (외 {len(companies) - 5}개 회사)")

        # 도메인별 공고 수
        cursor.execute('''
            SELECT domain, COUNT(*) as cnt
            FROM job_postings
            GROUP BY domain
        ''')
        domains = cursor.fetchall()
        print(f"\n도메인별 공고 수:")
        for domain, count in domains:
            print(f"  - {domain}: {count}개")

        # 상세 정보 채움율
        cursor.execute('SELECT COUNT(*) FROM job_postings WHERE introduction IS NOT NULL')
        intro_count = cursor.fetchone()[0]

        cursor.execute('SELECT COUNT(*) FROM job_postings WHERE work_content IS NOT NULL')
        content_count = cursor.fetchone()[0]

        cursor.execute('SELECT COUNT(*) FROM job_postings WHERE qualification IS NOT NULL')
        qual_count = cursor.fetchone()[0]

        print(f"\n상세 정보 저장율:")
        print(f"  - 소개: {intro_count}/{total} ({intro_count/total*100:.1f}%)")
        print(f"  - 직무: {content_count}/{total} ({content_count/total*100:.1f}%)")
        print(f"  - 자격: {qual_count}/{total} ({qual_count/total*100:.1f}%)")

        conn.close()

    except Exception as e:
        print(f"❌ 통계 오류: {str(e)}")

def main():
    parser = argparse.ArgumentParser(
        description='크롤링된 채용공고 데이터 조회 및 분석'
    )
    parser.add_argument('--company', type=str, help='회사명으로 검색')
    parser.add_argument('--keyword', type=str, help='키워드로 검색')

    args = parser.parse_args()

    if args.company:
        query_by_company(args.company)
    elif args.keyword:
        search_keyword(args.keyword)
    else:
        query_all_jobs()

if __name__ == "__main__":
    main()
