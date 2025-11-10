"""
Storage Repository - DB 저장 및 쿼리 로직
"""
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from typing import List, Optional
from datetime import datetime

from src.models import JobPosting
from src.schema import JobPostingCreate, JobPostingResponse


class JobRepository:
    """채용공고 저장소"""
    
    def __init__(self, db: Session):
        self.db = db
    
    def create(self, posting: JobPostingCreate) -> Optional[JobPosting]:
        """공고 생성
        
        Args:
            posting: 생성할 공고 데이터
            
        Returns:
            생성된 JobPosting 또는 None (중복 시)
        """
        try:
            # Pydantic → ORM 변환
            db_posting = JobPosting(**posting.model_dump(exclude_none=True))
            
            self.db.add(db_posting)
            self.db.commit()
            self.db.refresh(db_posting)
            
            return db_posting
        
        except IntegrityError as e:
            self.db.rollback()
            # UNIQUE 제약 위반 (중복)
            if "unique_domain_job" in str(e):
                print(f"⚠️  중복 공고: {posting.domain}/{posting.canonical_job_id}")
                return None
            raise
        
        except Exception as e:
            self.db.rollback()
            print(f"❌ 공고 저장 실패: {e}")
            raise
    
    def bulk_create(self, postings: List[JobPostingCreate]) -> dict:
        """대량 공고 생성
        
        Args:
            postings: 공고 리스트
            
        Returns:
            통계 (created, duplicated, errors)
        """
        stats = {
            "created": 0,
            "duplicated": 0,
            "errors": 0
        }
        
        for posting in postings:
            try:
                result = self.create(posting)
                if result:
                    stats["created"] += 1
                else:
                    stats["duplicated"] += 1
            
            except Exception:
                stats["errors"] += 1
        
        return stats
    
    def get_by_id(self, posting_id: str) -> Optional[JobPosting]:
        """ID로 공고 조회"""
        return self.db.query(JobPosting).filter(
            JobPosting.id == posting_id
        ).first()
    
    def get_by_domain_and_job_id(
        self, 
        domain: str, 
        canonical_job_id: str
    ) -> Optional[JobPosting]:
        """도메인 + canonical_job_id로 공고 조회"""
        return self.db.query(JobPosting).filter(
            JobPosting.domain == domain,
            JobPosting.canonical_job_id == canonical_job_id
        ).first()
    
    def find_all(
        self,
        domain: Optional[str] = None,
        it_label: Optional[bool] = None,
        is_active: bool = True,
        limit: int = 100
    ) -> List[JobPosting]:
        """공고 목록 조회"""
        query = self.db.query(JobPosting)
        
        if domain:
            query = query.filter(JobPosting.domain == domain)
        
        if it_label is not None:
            query = query.filter(JobPosting.it_label == it_label)
        
        if is_active:
            query = query.filter(JobPosting.is_active == True)
        
        return query.limit(limit).all()
    
    def update(self, posting_id: str, updates: dict) -> Optional[JobPosting]:
        """공고 업데이트"""
        posting = self.get_by_id(posting_id)
        
        if not posting:
            return None
        
        for key, value in updates.items():
            if hasattr(posting, key):
                setattr(posting, key, value)
        
        posting.updated_at = datetime.now()
        
        self.db.commit()
        self.db.refresh(posting)
        
        return posting
    
    def delete(self, posting_id: str) -> bool:
        """공고 삭제"""
        posting = self.get_by_id(posting_id)
        
        if not posting:
            return False
        
        self.db.delete(posting)
        self.db.commit()
        
        return True
    
    def count_by_domain(self, domain: str) -> int:
        """도메인별 공고 수"""
        return self.db.query(JobPosting).filter(
            JobPosting.domain == domain
        ).count()
    
    def count_it_jobs(self, domain: Optional[str] = None) -> int:
        """IT 공고 수"""
        query = self.db.query(JobPosting).filter(
            JobPosting.it_label == True
        )
        
        if domain:
            query = query.filter(JobPosting.domain == domain)
        
        return query.count()

    def count_all(self) -> int:
        """전체 공고 수"""
        return self.db.query(JobPosting).count()
