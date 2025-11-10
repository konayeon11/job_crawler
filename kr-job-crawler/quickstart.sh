#!/bin/bash
# Quick Start Script for KR Job Crawler

set -e

echo "🚀 대한민국 IT 채용공고 크롤러 - 빠른 시작"
echo "==========================================="
echo ""

# 1. 가상환경 확인
if [ ! -d "venv" ]; then
    echo "📦 가상환경 생성 중..."
    python3 -m venv venv
fi

echo "🔧 가상환경 활성화..."
source venv/bin/activate

# 2. 의존성 설치
echo "📥 의존성 설치 중..."
pip install -q -r requirements.txt

# 3. Playwright 설치
echo "🎭 Playwright 브라우저 설치 중..."
playwright install chromium

# 4. 환경 변수 설정
if [ ! -f ".env" ]; then
    echo "⚙️  환경 변수 설정..."
    cp .env.example .env
fi

# 5. Docker Compose 실행
echo "🐳 PostgreSQL 시작 중..."
docker-compose up -d

echo ""
echo "⏳ 데이터베이스 준비 대기 (10초)..."
sleep 10

# 6. 데이터베이스 상태 확인
echo "🔍 데이터베이스 연결 확인..."
docker exec job_crawler_db pg_isready -U crawler

echo ""
echo "✅ 설치 완료!"
echo ""
echo "📋 다음 명령어로 크롤링을 시작하세요:"
echo ""
echo "  python -m src.runner.cli crawl \\"
echo "    --domain careers.example.com \\"
echo "    --base-url https://careers.example.com/jobs \\"
echo "    --auto-profile \\"
echo "    --target IT \\"
echo "    --limit 50"
echo ""
echo "📚 더 많은 명령어는 README.md를 참고하세요."
echo ""
