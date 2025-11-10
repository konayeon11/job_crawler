"""
Database connection and session management
"""
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from contextlib import contextmanager
from typing import Generator, Optional

from src.models import Base

# Global variables for lazy initialization
_engine: Optional[object] = None
_SessionLocal: Optional[object] = None

def _get_engine():
    """Lazy load engine"""
    global _engine
    if _engine is None:
        from src.config import settings
        # Windows에서 UTF-8 인코딩 설정
        _engine = create_engine(
            settings.database_url,
            pool_pre_ping=True,
            pool_size=5,
            max_overflow=10,
            echo=False
        )
    return _engine

def _get_session_factory():
    """Lazy load session factory"""
    global _SessionLocal
    if _SessionLocal is None:
        engine = _get_engine()
        _SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    return _SessionLocal


def init_db():
    """데이터베이스 초기화 (테이블 생성)"""
    Base.metadata.create_all(bind=_get_engine())


@contextmanager
def get_db() -> Generator[Session, None, None]:
    """데이터베이스 세션 컨텍스트 매니저"""
    SessionFactory = _get_session_factory()
    db = SessionFactory()
    try:
        yield db
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


def get_db_session() -> Session:
    """세션 팩토리 (의존성 주입용)"""
    return _get_session_factory()()
