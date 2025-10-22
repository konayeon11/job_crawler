# 파일 위치: api/main.py

import base64
import json
import os
from typing import Annotated, Optional
from fastapi import FastAPI, File, Form, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, Response
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from pathlib import Path

# --- 내부 모듈 임포트 ---
from core.graph_builder import app as agent_workflow, image_app
from agents.inventory_agent import InventoryAgent


# ======================================================
# 🔹 FastAPI 기본 설정
# ======================================================
app = FastAPI(
    title="AI 영양사 에이전트 API",
    version="0.1.0",
    docs_url="/docs",   # Swagger는 /docs로 유지
    redoc_url=None
)

# --- CORS 설정 (배포 시 도메인 제한 가능) ---
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # ex) ["https://nutritionist-agent.onrender.com"]
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ======================================================
# 🔹 프론트엔드 정적 파일 서빙 (frontend/dist)
# ======================================================
PROJECT_ROOT = Path(__file__).resolve().parents[1]
DIST_DIR = PROJECT_ROOT / "frontend" / "dist"

# /assets/* 정적 리소스
assets_dir = DIST_DIR / "assets"
if assets_dir.is_dir():
    app.mount("/assets", StaticFiles(directory=str(assets_dir)), name="assets")

# favicon.ico 요청 대응 (투명 PNG)
@app.get("/favicon.ico", include_in_schema=False)
def favicon():
    transparent_png = (
        b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01"
        b"\x08\x06\x00\x00\x00\x1f\x15\xc4\x89\x00\x00\x00\x0cIDATx\x9cc``\x00\x00\x00\x02\x00\x01"
        b"\xe2!\xbc3\x00\x00\x00\x00IEND\xaeB`\x82"
    )
    return Response(content=transparent_png, media_type="image/png")

# / → index.html 반환
@app.get("/", include_in_schema=False)
def serve_frontend():
    index_path = DIST_DIR / "index.html"
    if index_path.exists():
        return FileResponse(index_path)
    return {"error": f"index.html not found in {index_path}. Run 'npm run build' first."}

# 헬스체크
@app.get("/health", include_in_schema=False)
def health():
    return {"status": "ok"}


# ======================================================
# 🔹 API 모델 정의
# ======================================================
class ChatMessage(BaseModel):
    message: str


# ======================================================
# 🔹 핵심 기능 엔드포인트
# ======================================================

@app.post("/analyze-and-suggest", tags=["핵심 기능"])
async def analyze_and_suggest(
    file: Annotated[bytes, File()],
    constraints: Optional[str] = Form(default="{}")
):
    """냉장고 이미지 분석 → 재고 인식 → 레시피 추천"""
    try:
        constraints_dict = json.loads(constraints)
    except json.JSONDecodeError:
        raise HTTPException(status_code=400, detail="'constraints'가 유효한 JSON 형식이 아닙니다.")

    image_base64 = base64.b64encode(file).decode("utf-8")

    # LangGraph 워크플로우 실행
    initial_state = {"image_base64": image_base64, "constraints": constraints_dict}
    final_state = image_app.invoke(initial_state, config={"configurable": {"thread_id": "image_analysis_thread"}})

    recognized_inventory = {
        item.get("item_name"): {"quantity": item.get("quantity", 1)}
        for item in final_state.get("new_items", [])
        if item.get("item_name")
    }

    return {
        "inventory": recognized_inventory,
        "recipes": final_state.get("recipes", []),
        "shopping_list": final_state.get("shopping_list")
    }


@app.post("/chat", tags=["챗봇"])
async def chat_with_agent(chat_request: ChatMessage):
    """AI 에이전트 챗봇"""
    initial_state = {"chat_message": chat_request.message}
    final_state = agent_workflow.invoke(initial_state)

    response_data = {"response": final_state.get("response", "요청을 처리할 수 없습니다.")}

    # 레시피 관련 의도 처리
    if final_state.get("intent", {}).get("intent") == "get_recipes":
        if (shopping_list_data := final_state.get("shopping_list")):
            response_data["shopping_list"] = shopping_list_data
        if (recipes_data := final_state.get("recipes")):
            response_data["recipes"] = recipes_data

    return response_data


@app.get("/inventory", tags=["보조 기능"])
def read_inventory():
    """현재 저장된 재고 목록 반환"""
    inventory_agent = InventoryAgent()
    current_inventory = inventory_agent.load_inventory()
    return {"items": current_inventory}


# ======================================================
# 🔹 Catch-All: 프론트엔드 라우터 지원 (/about, /home 등)
# ======================================================
@app.get("/{full_path:path}", include_in_schema=False)
def frontend_routes(full_path: str):
    """Vue Router의 history 모드 지원"""
    index_path = DIST_DIR / "index.html"
    if index_path.exists():
        return FileResponse(index_path)
    return {"error": "frontend/dist/index.html not found"}