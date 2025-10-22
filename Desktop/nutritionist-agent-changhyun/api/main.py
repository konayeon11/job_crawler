# 파일: api/main.py

from __future__ import annotations

import os
import sys
from pathlib import Path
from typing import List

from fastapi import FastAPI, Body, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, Response
from fastapi.staticfiles import StaticFiles

# --- PYTHONPATH 보강 (api/ 상위 = 리포 루트) ---
sys.path.append(os.path.dirname(os.path.dirname(__file__)))

# --- 내부 모듈 임포트 (상대/절대 경로 혼동 방지) ---
# 기존 코드 호환: 상대 import가 가능하면 유지
try:
    from .schema import (
        ImageAnalyzeRequest,
        InventoryChange,
        RecipeSuggestRequest,
        PlanProfile,
        NutritionEstimateRequest,
        NutritionAnalysisRequest,
    )
    from .planner import router as planner_router
except ImportError:
    # 만약 패키지 초기화가 안 되어 있을 때 절대 경로로 폴백
    from api.schema import (  # type: ignore
        ImageAnalyzeRequest,
        InventoryChange,
        RecipeSuggestRequest,
        PlanProfile,
        NutritionEstimateRequest,
        NutritionAnalysisRequest,
    )
    from api.planner import router as planner_router  # type: ignore

from agents.nutrition_agent import analyze_nutrition_report
from core.models import NutritionAnalysisReport


# ======================================================
# FastAPI 앱
# ======================================================
app = FastAPI(
    title="AI Nutritionist Agent API",
    version="0.1.0",
    docs_url="/docs",
    redoc_url=None,
)

# CORS (초기엔 *로 열고, 운영에서는 도메인 제한 권장)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 예: ["https://nutritionist-agent.onrender.com"]
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ======================================================
# 프론트엔드 정적 파일 서빙 (frontend/dist)
# ======================================================
PROJECT_ROOT = Path(__file__).resolve().parents[1]
DIST_DIR = PROJECT_ROOT / "frontend" / "dist"

# /assets/* 정적 리소스 (Vite 산출물)
assets_dir = DIST_DIR / "assets"
if assets_dir.is_dir():
    app.mount("/assets", StaticFiles(directory=str(assets_dir)), name="assets")

# favicon 404 방지 (투명 1x1 PNG)
@app.get("/favicon.ico", include_in_schema=False)
def favicon():
    transparent_png = (
        b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01"
        b"\x08\x06\x00\x00\x00\x1f\x15\xc4\x89\x00\x00\x00\x0cIDATx\x9cc``\x00\x00\x00\x02\x00\x01"
        b"\xe2!\xbc3\x00\x00\x00\x00IEND\xaeB`\x82"
    )
    return Response(content=transparent_png, media_type="image/png")

# 루트 → index.html
@app.get("/", include_in_schema=False)
def serve_front():
    index_path = DIST_DIR / "index.html"
    if index_path.exists():
        return FileResponse(index_path)
    return {"error": f"index.html not found at {index_path}. Build frontend first."}

# Vue Router를 위한 catch-all (항상 API 라우트 정의 ‘후’에 두는 게 안전하지만,
# 여기서는 /docs, /health, /plan/*, /nutrition/* 등의 고정 경로가 우선 매칭됨)
@app.get("/{full_path:path}", include_in_schema=False)
def spa_catch_all(full_path: str):
    index_path = DIST_DIR / "index.html"
    if index_path.exists():
        return FileResponse(index_path)
    return {"detail": "Not Found"}


# ======================================================
# 라우터 / 헬스체크
# ======================================================
app.include_router(planner_router, prefix="/plan", tags=["plan"])

@app.get("/health")
def health():
    return {"status": "ok"}


# ======================================================
# 아래는 네가 준 엔드포인트 시그니처를 그대로 유지
# (feat/* 브랜치에서 실제 구현)
# ======================================================

@app.post("/vision/analyze")
def analyze_image(payload: ImageAnalyzeRequest):
    """
    Input: ImageAnalyzeRequest(image_b64)
    Output: [{"name": str, "confidence": float}, ...]
    """
    return {"detail": "implement in feat/*"}

@app.get("/inventory")
def read_inventory():
    """
    Output: {"items":[{"name": str, "quantity": float, "unit": str}, ...]}
    """
    return {"detail": "implement in feat/*"}

@app.post("/inventory/update")
def update_inventory(changes: List[InventoryChange]):
    """
    Input: list of InventoryChange
    Output: {"ok": bool}
    """
    return {"detail": "implement in feat/*"}

@app.post("/recipes/suggest")
def suggest_recipes(payload: RecipeSuggestRequest):
    """
    Output:
      [{"title": str, "ingredients": List[str], "steps": List[str]}, ...]
    """
    return {"detail": "implement in feat/*"}

@app.post("/nutrition/estimate")
def estimate_nutrition(payload: NutritionEstimateRequest):
    """
    Output: {"kcal": float, "protein": float, "carbs": float, "fat": float}
    """
    return {"detail": "implement in feat/*"}

@app.post("/nutrition/analyze", response_model=NutritionAnalysisReport, tags=["nutrition"])
def analyze_nutrition(request: NutritionAnalysisRequest = Body(...)):
    """
    식단표 또는 음식 기록을 바탕으로 영양 분석 리포트를 생성합니다.
    """
    # meal_plan과 food_log 중 하나는 반드시 제공
    if not request.meal_plan and not request.food_log:
        raise HTTPException(status_code=400, detail="meal_plan 또는 food_log 중 하나는 반드시 제공되어야 합니다.")

    # LLM 입력 구성
    input_data = {}
    if request.meal_plan:
        input_data["meal_plan"] = request.meal_plan.dict()
    if request.food_log:
        input_data["food_log"] = request.food_log

    report = analyze_nutrition_report(input_data)
    return report
