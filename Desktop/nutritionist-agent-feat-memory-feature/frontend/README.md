# AI Nutritionist Frontend (Vue CDN, Mobile-first) — Backend Schema v2
백엔드의 `/analyze-and-suggest` 가 `file(bytes)` + `constraints(JSON 문자열)`을 받는 스키마에 맞춰 프론트를 수정한 버전입니다.

## 전송 포맷
- `file`: 이미지 파일 (필수) — `File(...)` 로 수신
- `constraints`: JSON 문자열 (예: `{"prompt":"레시피 추천","max_time":20,"max_sodium":1500}`)

## 실행
```bash
cd ai-nutritionist-vue-v2
python -m http.server 5500
# http://localhost:5500
```

### 다른 포트/도메인 백엔드와 연결 시
`index.html` 가장 위에:
```html
<script>window.BACKEND_BASE_URL = "http://localhost:8000";</script>
```

/health 엔드포인트가 없을 수 있으므로, 상태 텍스트는 "연결 확인 필요"로 표시될 수 있습니다.
