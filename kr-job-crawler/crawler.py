"""
채용공고 크롤러: API → 정제 → DB 저장
목표: 공고별 상세 내용을 저장하여 유사도 측정 및 트렌드 분석 가능
"""

import sys
import os
import re
import json
import html as html_lib
from datetime import datetime
from typing import Optional, List, Dict, Any
import uuid

# UTF-8 인코딩 설정
os.environ['PYTHONIOENCODING'] = 'utf-8'
sys.stdout.reconfigure(encoding='utf-8')

sys.path.insert(0, r'C:\Users\SKAX\Desktop\kr-job-crawler\kr-job-crawler')

from dotenv import load_dotenv
load_dotenv(override=True)

import httpx
import sqlite3


# ============================================================================
# 정제 함수
# ============================================================================

def clean_html_text(text: Optional[str]) -> Optional[str]:
    """HTML 엔티티 및 태그 정제"""
    if not text or text == '-' or text == '':
        return None

    try:
        text = html_lib.unescape(text)
        text = re.sub(r'<br\s*/?>', '\n', text)
        text = re.sub(r'</?p>', '\n', text)
        text = re.sub(r'</?div>', '\n', text)
        text = re.sub(r'<[^>]+>', '', text)
        text = re.sub(r'\n\s*\n+', '\n\n', text)
        text = re.sub(r'[ \t]+', ' ', text)
        text = text.strip()
        return text if text else None
    except:
        return text


def extract_skills(skill_list: Optional[List[Dict]]) -> Optional[List[str]]:
    """기술 스택 추출"""
    if not skill_list:
        return None

    skills = []
    for skill in skill_list:
        if isinstance(skill, dict):
            name = skill.get('skillSetName') or skill.get('name')
            if name and name not in ['Unknown', '기타', '-', '']:
                skills.append(name)

    return skills if skills else None


# ============================================================================
# DB 관련 함수
# ============================================================================

def init_db(db_path: str):
    """SQLite 데이터베이스 초기화"""
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS job_postings (
            id TEXT PRIMARY KEY,
            domain VARCHAR(255) NOT NULL,
            job_id VARCHAR(500) NOT NULL UNIQUE,
            title VARCHAR(1000) NOT NULL,
            company VARCHAR(500),
            location VARCHAR(200),
            source_url TEXT,

            -- 정제된 상세 내용 (핵심)
            introduction TEXT,
            work_content TEXT,
            qualification TEXT,
            work_condition TEXT,
            recruitment_process TEXT,

            -- 기술 스택
            skills TEXT,
            required_skills TEXT,

            -- 기타
            recruitment_count INT,
            employment_type VARCHAR(100),
            job_category VARCHAR(100),

            -- 메타데이터
            raw_json TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    cursor.execute('CREATE INDEX IF NOT EXISTS idx_domain ON job_postings(domain)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_job_id ON job_postings(job_id)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_company ON job_postings(company)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_created_at ON job_postings(created_at)')

    conn.commit()
    cursor.close()
    conn.close()


def save_job_posting(db_path: str, posting: Dict[str, Any]) -> bool:
    """공고를 DB에 저장"""
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        cursor.execute('''
            INSERT OR REPLACE INTO job_postings (
                id, domain, job_id, title, company, location, source_url,
                introduction, work_content, qualification, work_condition,
                recruitment_process, skills, required_skills, recruitment_count,
                employment_type, job_category, raw_json, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            posting['id'],
            posting['domain'],
            posting['job_id'],
            posting['title'],
            posting['company'],
            posting['location'],
            posting['source_url'],
            posting['introduction'],
            posting['work_content'],
            posting['qualification'],
            posting['work_condition'],
            posting['recruitment_process'],
            posting['skills'],
            posting['required_skills'],
            posting['recruitment_count'],
            posting['employment_type'],
            posting['job_category'],
            posting['raw_json'],
            datetime.now().isoformat()
        ))

        conn.commit()
        cursor.close()
        conn.close()
        return True
    except Exception as e:
        print(f"❌ 저장 오류: {str(e)}")
        return False


# ============================================================================
# 크롤러
# ============================================================================

def crawl_kakao_jobs(db_path: str, limit: int = 15):
    """카카오 채용공고 크롤링"""

    print("=" * 100)
    print("🚀 채용공고 크롤러 시작")
    print("=" * 100)

    api_url = "https://careers.kakao.com/public/api/job-list"
    params = {
        "skillSet": "",
        "part": "TECHNOLOGY",
        "company": "",
        "page": 1,
        "limit": limit,
    }

    # 1. API 호출
    print(f"\n📡 API 호출 중... {api_url}")

    try:
        client = httpx.Client(follow_redirects=True, timeout=30.0)
        response = client.get(api_url, params=params)
        response.raise_for_status()
        data = response.json()
        jobs = data.get('jobList', [])
        print(f"✅ {len(jobs)}개 공고 수집 완료\n")
    except Exception as e:
        print(f"❌ API 호출 실패: {str(e)}")
        return

    # 2. DB 초기화
    print("📝 데이터베이스 초기화 중...")
    init_db(db_path)
    print("✅ DB 준비 완료\n")

    # 3. 각 공고 처리
    print("🔄 공고 처리 중...")
    saved_count = 0

    for i, job in enumerate(jobs, 1):
        try:
            # 정제
            posting = {
                'id': str(uuid.uuid4()),
                'domain': 'careers.kakao.com',
                'job_id': str(job.get('jobOfferId')),
                'title': job.get('jobOfferTitle', ''),
                'company': job.get('companyName', ''),
                'location': job.get('locationName', ''),
                'source_url': f"https://careers.kakao.com/jobs/{job.get('realId', '')}",

                # 정제된 상세 내용
                'introduction': clean_html_text(job.get('introduction')),
                'work_content': clean_html_text(job.get('workContentDesc')),
                'qualification': clean_html_text(job.get('qualification')),
                'work_condition': clean_html_text(job.get('workTypeDesc')),
                'recruitment_process': clean_html_text(job.get('jobOfferProcessDesc')),

                # 기술
                'skills': json.dumps(extract_skills(job.get('skillSetList')) or []),
                'required_skills': None,

                # 기타
                'recruitment_count': job.get('recruitCount'),
                'employment_type': job.get('workTypeName'),
                'job_category': job.get('jobTypeName'),

                # 원본 JSON
                'raw_json': json.dumps(job, ensure_ascii=False),
            }

            # 저장
            if save_job_posting(db_path, posting):
                saved_count += 1
                print(f"   ✓ [{i}] {posting['title'][:50]}")

        except Exception as e:
            print(f"   ✗ [{i}] 처리 실패: {str(e)}")

    print(f"\n✅ {saved_count}/{len(jobs)}개 공고 저장 완료")

    # 4. 저장된 데이터 요약
    print("\n" + "=" * 100)
    print("📊 저장된 데이터 요약")
    print("=" * 100)

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    cursor.execute('SELECT COUNT(*) FROM job_postings')
    total = cursor.fetchone()[0]

    cursor.execute('SELECT COUNT(*) FROM job_postings WHERE introduction IS NOT NULL')
    intro_count = cursor.fetchone()[0]

    cursor.execute('SELECT COUNT(*) FROM job_postings WHERE work_content IS NOT NULL')
    work_count = cursor.fetchone()[0]

    cursor.execute('SELECT COUNT(*) FROM job_postings WHERE qualification IS NOT NULL')
    qual_count = cursor.fetchone()[0]

    print(f"\n총 공고 수: {total}개")
    print(f"상세 내용 저장률:")
    print(f"  - 소개: {intro_count}/{total} ({intro_count/total*100:.1f}%)")
    print(f"  - 직무: {work_count}/{total} ({work_count/total*100:.1f}%)")
    print(f"  - 자격: {qual_count}/{total} ({qual_count/total*100:.1f}%)")

    cursor.close()
    conn.close()

    print(f"\n✅ 크롤링 완료!")
    print(f"💾 DB 위치: {db_path}")


if __name__ == "__main__":
    db_path = r'C:\Users\SKAX\Desktop\kr-job-crawler\kr-job-crawler\jobs.db'
    crawl_kakao_jobs(db_path)
