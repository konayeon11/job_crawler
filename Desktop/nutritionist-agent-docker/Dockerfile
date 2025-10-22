# Dockerfile

# 1. 베이스 이미지
FROM python:3.10-slim

# 2. 작업 디렉토리
WORKDIR /app

# 3. requirements.txt 복사 및 설치
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 4. 프로젝트 전체 파일 복사 (agents, api, core 등)
COPY . .

# 5. 실행 명령어 (api/main.py 파일의 'app' 변수를 실행)
CMD ["uvicorn", "api.main:app", "--host", "0.0.0.0", "--port", "8000"]