"""
Profile Loader - 사이트 프로파일 YAML 로드/저장
"""
import yaml
import os
from pathlib import Path
from typing import Optional
from datetime import datetime

from src.schema import SiteProfile
from src.config import settings


class ProfileLoader:
    """사이트 프로파일 관리"""
    
    def __init__(self, profile_dir: str = None):
        self.profile_dir = Path(profile_dir or settings.profile_dir)
        self.profile_dir.mkdir(parents=True, exist_ok=True)
    
    def load(self, domain: str) -> Optional[SiteProfile]:
        """프로파일 로드
        
        Args:
            domain: 도메인명 (예: careers.example.com)
            
        Returns:
            SiteProfile 또는 None
        """
        profile_path = self.profile_dir / f"{domain}.yaml"
        
        if not profile_path.exists():
            return None
        
        try:
            with open(profile_path, 'r', encoding='utf-8') as f:
                data = yaml.safe_load(f)
            
            return SiteProfile(**data)
        
        except Exception as e:
            print(f"⚠️  프로파일 로드 실패 ({domain}): {e}")
            return None
    
    def save(self, profile: SiteProfile) -> bool:
        """프로파일 저장
        
        Args:
            profile: 저장할 프로파일
            
        Returns:
            성공 여부
        """
        profile_path = self.profile_dir / f"{profile.domain}.yaml"
        
        try:
            # Pydantic 모델 → dict
            data = profile.model_dump(mode='json', exclude_none=True)
            
            # 저장 시점 기록
            data['last_verified'] = datetime.now().isoformat()
            
            with open(profile_path, 'w', encoding='utf-8') as f:
                yaml.dump(
                    data,
                    f,
                    allow_unicode=True,
                    default_flow_style=False,
                    sort_keys=False
                )
            
            print(f"✅ 프로파일 저장 완료: {profile_path}")
            return True
        
        except Exception as e:
            print(f"❌ 프로파일 저장 실패 ({profile.domain}): {e}")
            return False
    
    def update(self, domain: str, updates: dict) -> bool:
        """프로파일 부분 업데이트
        
        Args:
            domain: 도메인명
            updates: 업데이트할 필드 딕셔너리
            
        Returns:
            성공 여부
        """
        profile = self.load(domain)
        
        if not profile:
            print(f"⚠️  프로파일 없음: {domain}")
            return False
        
        # 버전 증가
        current_version = profile.version.split(".")
        current_version[-1] = str(int(current_version[-1]) + 1)
        updates['version'] = ".".join(current_version)
        
        # 업데이트 적용
        data = profile.model_dump()
        data.update(updates)
        
        # 재저장
        updated_profile = SiteProfile(**data)
        return self.save(updated_profile)
    
    def list_profiles(self) -> list:
        """저장된 프로파일 목록"""
        profiles = []
        
        for yaml_file in self.profile_dir.glob("*.yaml"):
            domain = yaml_file.stem
            profile = self.load(domain)
            if profile:
                profiles.append({
                    "domain": domain,
                    "version": profile.version,
                    "pattern": profile.pattern.value,
                    "last_verified": profile.last_verified
                })
        
        return profiles
    
    def delete(self, domain: str) -> bool:
        """프로파일 삭제"""
        profile_path = self.profile_dir / f"{domain}.yaml"
        
        if profile_path.exists():
            profile_path.unlink()
            print(f"🗑️  프로파일 삭제: {domain}")
            return True
        
        return False
