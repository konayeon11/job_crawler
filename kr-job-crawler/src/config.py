"""
Configuration management using Pydantic Settings
"""
from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import Optional
import os
from dotenv import load_dotenv


# 현재 src/config.py 파일 기준으로 .env 파일 찾기 (src/../.env)
_env_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), '.env')

# .env 파일을 먼저 로드 (override=True로 환경 변수 우선)
if os.path.exists(_env_path):
    load_dotenv(_env_path, override=True)

class Settings(BaseSettings):
    """Application configuration"""

    model_config = SettingsConfigDict(
        env_file=_env_path if os.path.exists(_env_path) else '.env',
        env_file_encoding='utf-8',
        case_sensitive=False
    )
    
    # Database
    database_url: str = "postgresql://crawler:crawlerpass@localhost:5432/job_crawler"
    
    # Crawler Settings
    user_agent: str = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
    request_delay_min: float = 1.0
    request_delay_max: float = 3.0
    max_retries: int = 3
    timeout_seconds: int = 30
    
    # Playwright
    playwright_headless: bool = True
    playwright_browser: str = "chromium"
    
    # Logging
    log_level: str = "INFO"
    log_file: str = "logs/crawler.log"
    
    # Profile Settings
    profile_dir: str = "src/profiles/sites"
    profile_cache_ttl: int = 86400  # 24 hours


# Global settings instance
settings = Settings()
