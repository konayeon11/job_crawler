# frontend/Dockerfile

# --- 1단계: 빌드 ---
# 'builder'라는 별명으로 빌드 환경 구성
# 버전을 18에서 20으로 수정
FROM node:20-alpine AS builder
WORKDIR /app
COPY package*.json ./
RUN npm install
COPY . .
RUN npm run build

# --- 2단계: 서빙 ---
# 경량화된 node 이미지에서 서빙
# 여기도 18에서 20으로 수정
FROM node:20-alpine
WORKDIR /app
# 'serve' 패키지를 전역으로 설치
RUN npm install -g serve
# 빌드 단계(builder)에서 /app/dist 폴더의 결과물만 복사
COPY --from=builder /app/dist ./dist

# 3000번 포트 개방
EXPOSE 3000

# 'serve'를 이용해 dist 폴더를 3000번 포트로 서빙
CMD ["serve", "-s", "dist", "-l", "3000"]