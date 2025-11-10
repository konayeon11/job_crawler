"""
Hash utilities for duplicate detection and snapshot comparison
"""
import hashlib
import json
from typing import Any, Dict


def compute_content_hash(content: str) -> str:
    """콘텐츠 해시 계산 (SHA256)"""
    return hashlib.sha256(content.encode('utf-8')).hexdigest()


def compute_json_hash(data: Dict[str, Any]) -> str:
    """JSON 데이터 해시 (정렬 후 계산)"""
    json_str = json.dumps(data, sort_keys=True, ensure_ascii=False)
    return compute_content_hash(json_str)


def compute_list_hash(items: list) -> str:
    """리스트 해시 (Facet Mapper용 - 리스트 전후 비교)"""
    combined = "\n".join(str(item) for item in sorted(items))
    return compute_content_hash(combined)
