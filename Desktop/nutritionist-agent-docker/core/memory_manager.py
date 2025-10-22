"""
MemoryManager: 사용자 컨텍스트/히스토리 관리 (인메모리 구현)
"""
from typing import Dict, Any

# 간단한 인메모리 세션 저장소
_session_store: Dict[str, Dict[str, Any]] = {}

def load_session(session_id: str) -> Dict[str, Any]:
    """
    메모리에서 세션 상태를 불러옵니다.
    세션이 없으면 빈 딕셔너리를 반환합니다.
    """
    return _session_store.get(session_id, {})

def save_session(session_id: str, state: Dict[str, Any]) -> bool:
    """
    메모리에 세션 상태를 저장합니다.
    """
    _session_store[session_id] = state
    print(f"세션 '{session_id}' 저장됨. 현재 상태: {_session_store[session_id]}") # 확인을 위한 출력
    return True
