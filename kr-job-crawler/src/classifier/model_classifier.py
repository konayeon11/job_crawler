"""
Model-based IT Classifier - 모델 기반 분류 (스텁)
"""
from typing import Dict, Any, Tuple

from src.schema import JobPostingCreate


class ModelClassifier:
    """모델 기반 IT 분류기 (향후 구현)"""
    
    def __init__(self, model_path: str = None):
        """
        Args:
            model_path: 학습된 모델 경로
        """
        self.model_path = model_path
        self.model = None
        
        # TODO: 모델 로딩 구현
        # if model_path and os.path.exists(model_path):
        #     self.model = self._load_model(model_path)
    
    def classify(self, posting: JobPostingCreate) -> Tuple[bool, float, Dict[str, Any]]:
        """IT 직군 여부 분류 (모델 기반)
        
        Args:
            posting: 분류할 공고
            
        Returns:
            (it_label, confidence, evidence)
        """
        
        # 스텁 구현: 항상 False 반환
        # TODO: 실제 모델 추론 구현
        
        if not self.model:
            # 모델 없으면 더미 반환
            return False, 0.0, {"status": "model_not_loaded"}
        
        # TODO: 모델 추론 로직
        # features = self._extract_features(posting)
        # prediction = self.model.predict(features)
        # confidence = self.model.predict_proba(features)[0][1]
        
        return False, 0.0, {"status": "stub"}
    
    def _extract_features(self, posting: JobPostingCreate) -> Dict[str, Any]:
        """공고에서 모델 입력 피처 추출 (스텁)"""
        # TODO: TF-IDF, 임베딩 등 피처 추출
        return {}
    
    def _load_model(self, model_path: str):
        """모델 로딩 (스텁)"""
        # TODO: pickle, joblib, transformers 등으로 모델 로드
        pass
