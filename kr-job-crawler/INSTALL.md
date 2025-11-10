# 📦 설치 가이드

## 시스템 요구사항

### 필수
- **Python**: 3.11 이상
- **PostgreSQL**: 15 이상
- **Docker**: 20.10 이상 (Docker Compose v2 포함)
- **메모리**: 최소 4GB RAM
- **디스크**: 최소 2GB 여유 공간

### 운영체제
- Linux (Ubuntu 20.04+, CentOS 8+)
- macOS (12.0+)
- Windows 10/11 (WSL2 권장)

## 방법 1: 빠른 설치 (추천)

```bash
# 1. 저장소 다운로드
cd kr-job-crawler

# 2. 빠른 시작 스크립트 실행
chmod +x quickstart.sh
./quickstart.sh

# 완료! 크롤링 시작 가능
```

## 방법 2: 수동 설치

### Step 1: Python 환경 설정

```bash
# 가상환경 생성
python3 -m venv venv

# 활성화
# Linux/Mac:
source venv/bin/activate
# Windows:
venv\Scripts\activate

# pip 업그레이드
pip install --upgrade pip
```

### Step 2: 의존성 설치

```bash
# Python 패키지 설치
pip install -r requirements.txt

# Playwright 브라우저 설치
playwright install chromium

# (선택) Firefox/WebKit도 설치 가능
playwright install firefox webkit
```

### Step 3: 데이터베이스 설정

#### Option A: Docker Compose (권장)

```bash
# PostgreSQL 컨테이너 시작
docker-compose up -d

# 로그 확인
docker-compose logs -f postgres

# 상태 확인
docker-compose ps
```

#### Option B: 로컬 PostgreSQL

```bash
# PostgreSQL 설치 (Ubuntu 예시)
sudo apt update
sudo apt install postgresql postgresql-contrib

# 데이터베이스 및 사용자 생성
sudo -u postgres psql

CREATE DATABASE job_crawler;
CREATE USER crawler WITH PASSWORD 'crawlerpass';
GRANT ALL PRIVILEGES ON DATABASE job_crawler TO crawler;
\q

# DDL 실행
psql -U crawler -d job_crawler -f migrations/init_schema.sql
```

### Step 4: 환경 변수 설정

```bash
# .env 파일 생성
cp .env.example .env

# .env 편집 (필요시)
vim .env  # 또는 nano, code 등
```

#### 주요 설정값

```ini
# 데이터베이스 (로컬 PostgreSQL 사용 시)
DATABASE_URL=postgresql://crawler:crawlerpass@localhost:5432/job_crawler

# Playwright 설정
PLAYWRIGHT_HEADLESS=true
PLAYWRIGHT_BROWSER=chromium

# 크롤링 설정
REQUEST_DELAY_MIN=1.0
REQUEST_DELAY_MAX=3.0
MAX_RETRIES=3
```

## 설치 확인

### 1. PostgreSQL 연결 테스트

```bash
# Docker Compose 사용 시
docker exec -it job_crawler_db psql -U crawler -d job_crawler -c "SELECT version();"

# 로컬 PostgreSQL 사용 시
psql -U crawler -d job_crawler -c "SELECT version();"
```

### 2. 테이블 생성 확인

```bash
docker exec -it job_crawler_db psql -U crawler -d job_crawler -c "\dt"

# 예상 결과:
#              List of relations
#  Schema |     Name      | Type  |  Owner  
# --------+---------------+-------+---------
#  public | job_postings  | table | crawler
```

### 3. Python 패키지 확인

```bash
python -c "import playwright; import sqlalchemy; print('✅ 모든 패키지 정상')"
```

### 4. 기본 테스트 실행

```bash
pytest tests/test_basic.py -v
```

## 트러블슈팅

### 문제 1: Playwright 브라우저 설치 실패

```bash
# 시스템 종속성 설치 (Ubuntu/Debian)
sudo playwright install-deps chromium

# 수동 설치
playwright install --force chromium
```

### 문제 2: PostgreSQL 연결 실패

```bash
# Docker 컨테이너 로그 확인
docker-compose logs postgres

# 컨테이너 재시작
docker-compose restart postgres

# 포트 충돌 확인
sudo lsof -i :5432
```

### 문제 3: 권한 오류

```bash
# Docker 소켓 권한
sudo usermod -aG docker $USER
newgrp docker

# 로그 디렉토리 생성
mkdir -p logs
chmod 755 logs
```

### 문제 4: Python 버전 불일치

```bash
# Python 버전 확인
python --version  # 3.11 이상 필요

# pyenv 사용 시
pyenv install 3.11.6
pyenv local 3.11.6
```

## 다음 단계

설치가 완료되었다면:

1. **첫 크롤링 실행**: `README.md`의 "빠른 시작" 섹션 참고
2. **프로파일 생성**: 타겟 사이트의 프로파일 YAML 작성
3. **분류기 커스터마이징**: 필요시 룰 또는 모델 수정

## 도움말

- 📚 **전체 문서**: `README.md`
- 🐛 **이슈 리포트**: GitHub Issues
- 💬 **질문**: Discussions 탭 활용
