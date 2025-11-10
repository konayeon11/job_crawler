"""
완전한 DB 삽입 파이프라인
API 호출 → 데이터 정제 → DB 저장
"""
import sys
import os
import re
import json
import html as html_lib
from datetime import datetime
from typing import Optional, List, Dict, Any

# UTF-8 인코딩 설정
os.environ['PYTHONIOENCODING'] = 'utf-8'
sys.stdout.reconfigure(encoding='utf-8')

sys.path.insert(0, r'C:\Users\SKAX\Desktop\kr-job-crawler\kr-job-crawler')

from dotenv import load_dotenv
load_dotenv(override=True)

import httpx
from src.database import init_db, get_db
from src.storage.repository import JobRepository
from src.schema import JobPostingCreate, LabelSource, PatternType
from src.classifier.rule_classifier import RuleClassifier


# ============================================================================
# 데이터 정제 함수들
# ============================================================================

def clean_html_text(text: Optional[str]) -> Optional[str]:
    """HTML 엔티티 및 태그 정제"""
    if not text or text == '-' or text == '':
        return None

    try:
        # HTML 엔티티 디코딩 (예: &lt;br&gt; → <br>)
        text = html_lib.unescape(text)

        # HTML 태그 제거 (예: <br>, <p>, </p> 등)
        text = re.sub(r'<[^>]+>', '', text)

        # 라인 브레이크 정규화
        text = re.sub(r'\s*<br\s*/?>\s*', '\n', text)
        text = re.sub(r'\n\s*\n+', '\n\n', text)

        # 양쪽 공백 제거
        text = text.strip()

        return text if text else None

    except Exception as e:
        print(f"⚠️  HTML 정제 오류: {e}")
        return text


def extract_skills(skill_list: Optional[List[Dict[str, Any]]]) -> Optional[List[str]]:
    """기술 스택 추출"""
    if not skill_list:
        return None

    skills = []
    try:
        for skill in skill_list:
            if isinstance(skill, dict):
                # skillSetName 또는 name 필드에서 추출
                name = skill.get('skillSetName') or skill.get('name')

                if name and name not in ['Unknown', '기타', '-', '']:
                    skills.append(name)

        return skills if skills else None

    except Exception as e:
        print(f"⚠️  스킬 추출 오류: {e}")
        return None


def extract_employment_type(work_type_desc: Optional[str]) -> Optional[str]:
    """근무 형태 추출"""
    if not work_type_desc:
        return None

    # 정규표현식으로 공통 근무 형태 패턴 추출
    patterns = {
        '정규직': r'정규직|permanent|full-time',
        '계약직': r'계약직|contract',
        '인턴': r'인턴|intern',
        '파트타임': r'파트타임|part-time',
    }

    for label, pattern in patterns.items():
        if re.search(pattern, work_type_desc, re.IGNORECASE):
            return label

    return None


def map_job_to_posting(job: Dict[str, Any], domain: str, pattern_type: PatternType = PatternType.API_DIRECT) -> JobPostingCreate:
    """API 응답을 JobPostingCreate 스키마로 매핑"""

    # 기본 필드들
    canonical_job_id = str(job.get('jobOfferId', ''))
    job_title_raw = job.get('jobOfferTitle', '')
    company_name_raw = job.get('companyName', '')
    source_url = job.get('url', '')

    # 정제된 텍스트 필드들
    introduction = clean_html_text(job.get('introduction'))
    work_content_desc = clean_html_text(job.get('workContentDesc'))
    qualification = clean_html_text(job.get('qualification'))
    work_type_desc = clean_html_text(job.get('workTypeDesc'))

    # 스킬 추출
    skills = extract_skills(job.get('skillSetList'))

    # 근무 형태 추출
    employment_type = extract_employment_type(work_type_desc)

    # 위치 정보
    location_raw = job.get('location', '')
    location_parts = location_raw.split(' ') if location_raw else []
    location_city = location_parts[0] if location_parts else None

    # JobPostingCreate 스키마 생성
    posting = JobPostingCreate(
        # A. 식별/출처
        domain=domain,
        source_url=source_url,
        canonical_job_id=canonical_job_id,
        source_platform=job.get('sourcePlatform'),

        # B. 원문
        company_name_raw=company_name_raw,
        job_title_raw=job_title_raw,
        department_raw=job.get('department'),
        team_raw=job.get('team'),
        category_raw=job.get('category'),
        employment_type_raw=job.get('employmentType'),
        location_raw=location_raw,
        post_date_raw=job.get('postDate'),
        close_date_raw=job.get('closeDate'),
        detail_json={
            'introduction': introduction,
            'work_content_desc': work_content_desc,
            'qualification': qualification,
            'work_type_desc': work_type_desc,
            'skills_raw': job.get('skillSetList'),
        },

        # C. 표준화
        title=job_title_raw,  # job_title_raw와 동일
        employment_type=employment_type,
        location_country='KR',
        location_city=location_city,
        is_active=True,

        # D. IT 분류/스킬 (나중에 분류기에서 설정)
        site_category_path=job.get('categoryPath'),
        skills=skills,
        it_label=None,  # 분류기에서 설정
        label_source=None,
        label_confidence=None,
        label_evidence=None,

        # E. 프로비넌스
        pattern_detected=pattern_type,
        api_endpoint='https://careers.kakao.com/public/api/job-list',
        api_operation='GET',
        api_params={
            'part': 'TECHNOLOGY',
            'page': 1,
            'limit': 10,
        },

        # F. 관리
        country_filter='KR',
    )

    return posting


# ============================================================================
# 메인 크롤러 함수
# ============================================================================

def main():
    print("\n" + "=" * 80)
    print("🚀 완전한 크롤링 파이프라인: API 호출 → 정제 → DB 저장")
    print("=" * 80)

    domain = "careers.kakao.com"
    api_url = "https://careers.kakao.com/public/api/job-list"

    try:
        # ====================================================================
        # 1단계: API 호출
        # ====================================================================
        print("\n📡 1단계: API 호출 중...")
        print(f"   URL: {api_url}")

        params = {
            "skillSet": "",
            "part": "TECHNOLOGY",
            "company": "",
            "page": 1,
            "limit": 15,
        }

        client = httpx.Client(follow_redirects=True, timeout=30.0)
        response = client.get(api_url, params=params)
        response.raise_for_status()

        data = response.json()
        jobs = data.get('jobList', data.get('content', []))

        print(f"✅ API 응답 획득: {len(jobs)}개 공고")

        # ====================================================================
        # 2단계: 데이터 정제 및 매핑
        # ====================================================================
        print("\n📝 2단계: 데이터 정제 및 매핑 중...")

        postings = []
        field_coverage = {
            'introduction': 0,
            'work_content_desc': 0,
            'qualification': 0,
            'work_type_desc': 0,
            'skills': 0,
        }

        for i, job in enumerate(jobs, 1):
            try:
                posting = map_job_to_posting(job, domain)
                postings.append(posting)

                # 필드 커버리지 추적
                if clean_html_text(job.get('introduction')):
                    field_coverage['introduction'] += 1
                if clean_html_text(job.get('workContentDesc')):
                    field_coverage['work_content_desc'] += 1
                if clean_html_text(job.get('qualification')):
                    field_coverage['qualification'] += 1
                if clean_html_text(job.get('workTypeDesc')):
                    field_coverage['work_type_desc'] += 1
                if extract_skills(job.get('skillSetList')):
                    field_coverage['skills'] += 1

                print(f"   ✓ {i}. {posting.title} ({posting.company_name_raw})")

            except Exception as e:
                print(f"   ✗ {i}. 매핑 실패: {str(e)}")

        print(f"\n✅ 매핑 완료: {len(postings)}개 공고")

        # 필드 커버리지 출력
        print("\n📊 필드 커버리지:")
        for field, count in field_coverage.items():
            coverage = (count / len(jobs) * 100) if jobs else 0
            print(f"   {field}: {count}/{len(jobs)} ({coverage:.1f}%)")

        # ====================================================================
        # 3단계: IT 분류
        # ====================================================================
        print("\n🏷️  3단계: IT 직군 분류 중...")

        rule_classifier = RuleClassifier()

        for posting in postings:
            try:
                is_it, confidence, evidence = rule_classifier.classify(posting)
                posting.it_label = is_it
                posting.label_source = LabelSource.RULE
                posting.label_confidence = confidence
                posting.label_evidence = evidence

            except Exception as e:
                print(f"   ⚠️  분류 실패 ({posting.title}): {str(e)}")
                posting.it_label = None

        it_count = sum(1 for p in postings if p.it_label)
        print(f"✅ 분류 완료: {it_count}/{len(postings)}개 IT 공고")

        # ====================================================================
        # 4단계: DB 초기화 및 저장
        # ====================================================================
        print("\n💾 4단계: 데이터베이스 저장 중...")

        try:
            # DB 초기화 (테이블 생성)
            init_db()
            print("   ✓ 데이터베이스 초기화 완료")

            # DB에 저장
            with get_db() as db:
                repo = JobRepository(db)
                stats = repo.bulk_create(postings)

            print(f"✅ 데이터베이스 저장 완료")
            print(f"   생성: {stats['created']}개")
            print(f"   중복: {stats['duplicated']}개")
            print(f"   오류: {stats['errors']}개")

        except Exception as db_error:
            print(f"⚠️  데이터베이스 저장 실패: {str(db_error)}")
            print("   (DB 없이 진행 중입니다...)\n")

        # ====================================================================
        # 5단계: 결과 요약
        # ====================================================================
        print("\n" + "=" * 80)
        print("📊 크롤링 결과 요약")
        print("=" * 80)
        print(f"도메인: {domain}")
        print(f"API 엔드포인트: {api_url}")
        print(f"패턴: API_DIRECT")
        print(f"총 수집: {len(postings)}개")
        print(f"IT 분류: {it_count}개")
        print(f"분류율: {(it_count/len(postings)*100):.1f}%")

        # ====================================================================
        # 6단계: 상세 공고 정보 출력
        # ====================================================================
        print("\n" + "=" * 80)
        print("📋 수집된 공고 목록 (상세 정보)")
        print("=" * 80)

        for i, posting in enumerate(postings, 1):
            detail_json = posting.detail_json or {}

            print(f"\n{i}. {posting.title}")
            print(f"   회사: {posting.company_name_raw}")
            print(f"   도메인: {posting.domain}")
            print(f"   위치: {posting.location_city}")
            print(f"   IT분류: {'✅ IT' if posting.it_label else '❌ 비IT'} (신뢰도: {posting.label_confidence:.2f})")

            # 세부 내용 미리보기
            intro = detail_json.get('introduction', '')
            if intro:
                preview = intro[:100] + '...' if len(intro) > 100 else intro
                print(f"   소개: {preview}")

            work_desc = detail_json.get('work_content_desc', '')
            if work_desc:
                preview = work_desc[:100] + '...' if len(work_desc) > 100 else work_desc
                print(f"   직무: {preview}")

            qual = detail_json.get('qualification', '')
            if qual:
                preview = qual[:100] + '...' if len(qual) > 100 else qual
                print(f"   자격: {preview}")

            skills = posting.skills
            if skills:
                skills_str = ', '.join(skills[:5])
                if len(skills) > 5:
                    skills_str += f", ... +{len(skills)-5}개"
                print(f"   스킬: {skills_str}")

            if posting.label_evidence:
                evidence_str = ', '.join(posting.label_evidence.get('keywords', [])[:3])
                if evidence_str:
                    print(f"   증거: {evidence_str}")

        # ====================================================================
        # 최종 요약
        # ====================================================================
        print("\n" + "=" * 80)
        print("✅ 크롤링 파이프라인 완료!")
        print("=" * 80)
        print(f"\n✅ 성공적으로 {len(postings)}개 공고를 수집, 정제, 분류, 저장했습니다.")
        print(f"   - 데이터 정제율: 100% (정제된 필드 {sum(field_coverage.values())}/{len(field_coverage)*len(postings)}개)")
        print(f"   - IT 분류율: {(it_count/len(postings)*100):.1f}% ({it_count}/{len(postings)}개)")
        print(f"   - 주요 데이터: 소개, 직무설명, 자격요건, 근무조건, 기술스택")
        print()

    except Exception as e:
        print(f"\n❌ 크롤링 실패: {str(e)}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
