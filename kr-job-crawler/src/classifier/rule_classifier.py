"""
Rule-based IT Classifier - 룰 기반 IT 직군 분류
"""
from typing import Dict, Any, Tuple
import re

from src.schema import JobPostingCreate, LabelSource


class RuleClassifier:
    """룰 기반 IT 분류기"""
    
    # IT 관련 키워드
    IT_KEYWORDS = {
        "title": [
            "개발자", "developer", "engineer", "programmer",
            "소프트웨어", "software", "웹", "web", "앱", "app",
            "프론트엔드", "백엔드", "풀스택", "frontend", "backend", "fullstack",
            "데이터", "data", "AI", "ML", "머신러닝", "딥러닝",
            "DevOps", "데브옵스", "클라우드", "cloud",
            "보안", "security", "네트워크", "network",
            "DBA", "데이터베이스", "database"
        ],
        "skills": [
            "Python", "Java", "JavaScript", "TypeScript", "C++", "C#",
            "React", "Vue", "Angular", "Node.js", "Django", "Flask",
            "Spring", "Kubernetes", "Docker", "AWS", "Azure", "GCP",
            "TensorFlow", "PyTorch", "SQL", "MongoDB", "Redis",
            "Git", "Jenkins", "CI/CD"
        ],
        "category": [
            "IT", "개발", "Engineering", "Tech", "Software",
            "기술", "정보통신", "컴퓨터"
        ]
    }
    
    # 비IT 제외 키워드
    EXCLUDE_KEYWORDS = [
        "영업", "sales", "마케팅", "marketing",
        "인사", "HR", "총무", "경영지원",
        "회계", "재무", "finance", "accounting"
    ]
    
    def classify(self, posting: JobPostingCreate) -> Tuple[bool, float, Dict[str, Any]]:
        """IT 직군 여부 분류
        
        Args:
            posting: 분류할 공고
            
        Returns:
            (it_label, confidence, evidence)
        """
        
        evidence = {
            "matched_keywords": [],
            "match_locations": [],
            "score_breakdown": {}
        }
        
        score = 0.0
        max_score = 0.0
        
        # 1. 사이트 카테고리 우선 (가중치 높음)
        if posting.site_category_path:
            cat_score, cat_matches = self._check_keywords(
                posting.site_category_path,
                self.IT_KEYWORDS["category"]
            )
            if cat_score > 0:
                score += cat_score * 3.0  # 가중치 3배
                max_score += 3.0
                evidence["matched_keywords"].extend(cat_matches)
                evidence["match_locations"].append("site_category")
                evidence["score_breakdown"]["category"] = cat_score * 3.0
        
        # 2. 제목 확인 (가중치 중간)
        if posting.job_title_raw or posting.title:
            title = posting.title or posting.job_title_raw
            title_score, title_matches = self._check_keywords(
                title,
                self.IT_KEYWORDS["title"]
            )
            if title_score > 0:
                score += title_score * 2.0  # 가중치 2배
                max_score += 2.0
                evidence["matched_keywords"].extend(title_matches)
                evidence["match_locations"].append("title")
                evidence["score_breakdown"]["title"] = title_score * 2.0
        
        # 3. 스킬 확인 (가중치 높음)
        if posting.skills:
            skills_text = " ".join(posting.skills)
            skill_score, skill_matches = self._check_keywords(
                skills_text,
                self.IT_KEYWORDS["skills"]
            )
            if skill_score > 0:
                score += skill_score * 2.5  # 가중치 2.5배
                max_score += 2.5
                evidence["matched_keywords"].extend(skill_matches)
                evidence["match_locations"].append("skills")
                evidence["score_breakdown"]["skills"] = skill_score * 2.5
        
        # 4. 부서명 확인 (가중치 낮음)
        if posting.department_raw:
            dept_score, dept_matches = self._check_keywords(
                posting.department_raw,
                self.IT_KEYWORDS["category"]
            )
            if dept_score > 0:
                score += dept_score * 1.0
                max_score += 1.0
                evidence["matched_keywords"].extend(dept_matches)
                evidence["match_locations"].append("department")
                evidence["score_breakdown"]["department"] = dept_score
        
        # 5. 제외 키워드 확인 (패널티)
        exclude_penalty = self._check_exclude_keywords(posting)
        if exclude_penalty > 0:
            score -= exclude_penalty
            evidence["exclude_penalty"] = exclude_penalty
        
        # Confidence 계산
        if max_score > 0:
            confidence = min(score / max_score, 1.0)
        else:
            confidence = 0.0
        
        # IT 여부 판단 (threshold: 0.3)
        is_it = confidence >= 0.3
        
        evidence["total_score"] = score
        evidence["max_score"] = max_score
        evidence["confidence"] = confidence
        
        return is_it, confidence, evidence
    
    def _check_keywords(self, text: str, keywords: list) -> Tuple[float, list]:
        """키워드 매칭 확인"""
        if not text:
            return 0.0, []
        
        text_lower = text.lower()
        matched = []
        
        for keyword in keywords:
            if keyword.lower() in text_lower:
                matched.append(keyword)
        
        # 매칭 비율 계산
        score = len(matched) / len(keywords) if keywords else 0.0
        
        return score, matched
    
    def _check_exclude_keywords(self, posting: JobPostingCreate) -> float:
        """제외 키워드 확인 (패널티)"""
        text = " ".join(filter(None, [
            posting.job_title_raw,
            posting.title,
            posting.department_raw
        ]))
        
        if not text:
            return 0.0
        
        text_lower = text.lower()
        penalty = 0.0
        
        for keyword in self.EXCLUDE_KEYWORDS:
            if keyword.lower() in text_lower:
                penalty += 0.5  # 키워드당 0.5 패널티
        
        return penalty
