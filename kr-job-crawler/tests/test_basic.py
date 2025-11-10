"""
Basic tests for the crawler system
"""
import pytest
from src.config import settings
from src.schema import JobPostingCreate, PatternType, LabelSource
from src.classifier.rule_classifier import RuleClassifier


def test_settings_loaded():
    """설정이 올바르게 로드되는지 확인"""
    assert settings.database_url is not None
    assert settings.request_delay_min > 0
    assert settings.playwright_headless is not None


def test_job_posting_creation():
    """JobPostingCreate 스키마 생성 테스트"""
    posting = JobPostingCreate(
        domain="test.com",
        source_url="https://test.com/job/123",
        canonical_job_id="123",
        job_title_raw="Backend Developer",
        pattern_detected=PatternType.STATIC_TOGGLE
    )
    
    assert posting.domain == "test.com"
    assert posting.canonical_job_id == "123"
    assert posting.pattern_detected == PatternType.STATIC_TOGGLE


def test_rule_classifier_it_detection():
    """룰 기반 IT 분류기 테스트"""
    classifier = RuleClassifier()
    
    # IT 공고
    it_posting = JobPostingCreate(
        domain="test.com",
        source_url="https://test.com/job/1",
        canonical_job_id="1",
        job_title_raw="Python Developer",
        skills=["Python", "Django", "PostgreSQL"]
    )
    
    is_it, confidence, evidence = classifier.classify(it_posting)
    assert is_it is True
    assert confidence > 0.3
    assert len(evidence["matched_keywords"]) > 0
    
    # 비IT 공고
    non_it_posting = JobPostingCreate(
        domain="test.com",
        source_url="https://test.com/job/2",
        canonical_job_id="2",
        job_title_raw="영업 관리자",
        department_raw="영업팀"
    )
    
    is_it, confidence, evidence = classifier.classify(non_it_posting)
    assert is_it is False or confidence < 0.3


def test_pattern_type_enum():
    """PatternType Enum 테스트"""
    assert PatternType.STATIC_TOGGLE.value == "static_toggle"
    assert PatternType.API_DIRECT.value == "api_direct"
    
    # Enum 파싱
    pattern = PatternType("hash_routing")
    assert pattern == PatternType.HASH_ROUTING


def test_label_source_enum():
    """LabelSource Enum 테스트"""
    assert LabelSource.RULE.value == "rule"
    assert LabelSource.MODEL.value == "model"
    assert LabelSource.MIXED.value == "mixed"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
