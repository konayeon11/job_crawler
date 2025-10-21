# 파일: api/main.py

import base64
import json
import os
import datetime as dt
import sqlite3
import threading
import time
from typing import Annotated, Optional

from fastapi import FastAPI, File, Form, HTTPException, Body, Header
from fastapi.staticfiles import StaticFiles
from starlette.responses import RedirectResponse

# (선택) .env 지원
try:
    from dotenv import load_dotenv
    load_dotenv()
except Exception:
    pass

# --- LangGraph 워크플로우와 필요한 에이전트 ---
from core.graph_builder import app as agent_workflow, image_app  # image_app 임포트
from agents.inventory_agent import InventoryAgent

# (LLM) OpenAI SDK
try:
    from openai import OpenAI
    _openai_client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
except Exception:
    _openai_client = None  # 키 또는 SDK 미설치시 폴백

# --- FastAPI 앱 초기화 ---
app = FastAPI(title="AI 영양사 에이전트 API", version="0.1.0")

# ✅ 프론트 정적 마운트 (Same-origin 권장)
# project-root/frontend 폴더에 프론트 파일을 넣으세요.
if os.path.isdir("frontend"):
    app.mount("/ui", StaticFiles(directory="frontend", html=True), name="ui")

    @app.get("/", include_in_schema=False)
    async def root():
        return RedirectResponse("/ui")

# (선택) 헬스 체크
@app.get("/health", tags=["보조 기능"])
async def health():
    return {"ok": True}

# ==============================
#  DB (SQLite) — XP 적립/조회
# ==============================
DB_PATH = os.path.join("data", "app.db")
_db_lock = threading.Lock()

def _db():
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.execute("PRAGMA journal_mode=WAL;")
    return conn

def ensure_db():
    with _db_lock:
        conn = _db()
        cur = conn.cursor()
        cur.execute("""
        CREATE TABLE IF NOT EXISTS xp_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id TEXT NOT NULL,
            quest_id TEXT,
            title TEXT,
            xp INTEGER NOT NULL,
            reason TEXT,
            payload_json TEXT,
            ts TEXT NOT NULL
        );
        """)
        cur.execute("""
        CREATE TABLE IF NOT EXISTS user_profile (
            user_id TEXT PRIMARY KEY,
            total_xp INTEGER NOT NULL DEFAULT 0
        );
        """)
        conn.commit()
        conn.close()

def add_xp(user_id: str, xp: int, quest_id: str, title: str, reason: str, payload: dict):
    ts = time.strftime("%Y-%m-%d %H:%M:%S")
    pj = json.dumps(payload, ensure_ascii=False)
    with _db_lock:
        conn = _db()
        cur = conn.cursor()
        cur.execute(
            "INSERT INTO xp_log (user_id, quest_id, title, xp, reason, payload_json, ts) "
            "VALUES (?, ?, ?, ?, ?, ?, ?)",
            (user_id, quest_id, title, int(xp), reason or "", pj, ts),
        )
        # upsert total_xp
        cur.execute(
            "INSERT INTO user_profile (user_id, total_xp) VALUES (?, ?) "
            "ON CONFLICT(user_id) DO UPDATE SET total_xp = user_profile.total_xp + excluded.total_xp",
            (user_id, int(xp)),
        )
        conn.commit()
        conn.close()

def get_profile(user_id: str):
    with _db_lock:
        conn = _db()
        cur = conn.cursor()
        cur.execute("SELECT total_xp FROM user_profile WHERE user_id=?", (user_id,))
        row = cur.fetchone()
        total = row[0] if row else 0
        cur.execute(
            "SELECT id, quest_id, title, xp, reason, ts "
            "FROM xp_log WHERE user_id=? ORDER BY id DESC LIMIT 50",
            (user_id,),
        )
        logs = [
            {"id": r[0], "quest_id": r[1], "title": r[2], "xp": r[3], "reason": r[4], "ts": r[5]}
            for r in cur.fetchall()
        ]
        conn.close()
    return {"user_id": user_id, "total_xp": total, "recent": logs}

# 앱 시작 시 DB 준비
ensure_db()

# ==============================
#   LLM 기반 퀘스트 생성 유틸
# ==============================
def generate_dynamic_quests(inventory: dict, constraints: dict) -> list[dict]:
    """
    inventory/constraints 기반으로 LLM이 맞춤 퀘스트를 생성.
    실패하면 휴리스틱 기본 퀘스트로 폴백.
    스키마: [{"id":"q1","title":"...","xp":20,"reason":"...","checks":["..."]}, ...]
    """
    today = dt.date.today()
    items, imminent = [], []

    for name, meta in (inventory or {}).items():
        exp = (meta or {}).get("expiry_date")
        left = None
        try:
            if exp:
                left = (dt.date.fromisoformat(exp) - today).days
        except Exception:
            pass
        items.append({
            "name": name,
            "quantity": (meta or {}).get("quantity"),
            "days_left": left,
        })
        if left is not None and left <= 2:
            imminent.append(name)

    # 1) LLM으로 생성 시도
    if _openai_client:
        try:
            prompt = {
                "role": "user",
                "content": (
                    "당신은 게이미피케이션된 영양 코치입니다.\n"
                    "사용자의 냉장고 인벤토리와 제약조건을 보고 오늘의 데일리 퀘스트 3개를 제안하세요.\n"
                    "임박(유통기한↓) 재료 사용을 우선시하고, 각 퀘스트는 5~30 XP 범위로 점수화하세요.\n"
                    "아래의 JSON 배열 형식으로만 응답하세요:\n"
                    '[{"id":"q1","title":"...","xp":20,"reason":"...","checks":["..."]}, ...]\n\n'
                    f"inventory: {json.dumps(items, ensure_ascii=False)}\n"
                    f"constraints: {json.dumps(constraints or {}, ensure_ascii=False)}\n"
                )
            }
            resp = _openai_client.chat.completions.create(
                model="gpt-4o-mini",
                temperature=0.4,
                messages=[prompt]
            )
            text = resp.choices[0].message.content
            quests = json.loads(text)

            if not isinstance(quests, list):
                raise ValueError("LLM 응답이 배열이 아님")

            # 간단 스키마 보정
            out = []
            for i, q in enumerate(quests, 1):
                if not isinstance(q, dict):
                    continue
                out.append({
                    "id": q.get("id") or f"q{i}",
                    "title": q.get("title") or f"퀘스트 {i}",
                    "xp": int(q.get("xp") or 10),
                    "reason": q.get("reason") or "",
                    "checks": q.get("checks") or [],
                })
            if out:
                return out[:5]
        except Exception:
            pass  # LLM 실패 시 폴백으로

    # 2) 폴백: 임박/시간/나트륨 기반
    fb = []
    if imminent:
        fb.append({
            "id": "q1",
            "title": f"임박 재료 {min(2, len(imminent))}개 사용",
            "xp": 20,
            "reason": "유통기한 임박 재료 우선 소진",
            "checks": imminent[:3]
        })
    fb.append({
        "id": "q2",
        "title": f"목표 시간({(constraints or {}).get('max_time', 20)}분) 내 1끼",
        "xp": 10,
        "reason": "빠른 조리 루틴",
        "checks": []
    })
    if (constraints or {}).get("max_sodium"):
        fb.append({
            "id": "q3",
            "title": f"나트륨 {(constraints or {}).get('max_sodium')}mg 이하",
            "xp": 15,
            "reason": "저나트륨 식단",
            "checks": []
        })
    return fb

# ==============================
#          API 엔드포인트
# ==============================

# ✨ 통합 워크플로우: 이미지 → 인벤토리/레시피 → +퀘스트
@app.post("/analyze-and-suggest", tags=["핵심 기능"])
async def analyze_and_suggest(
    file: Annotated[bytes, File(...)],              # 프론트 필드명: file
    constraints: Optional[str] = Form(default="{}") # 프론트 필드명: constraints(JSON 문자열)
):
    """
    냉장고 이미지를 받아 재고 분석부터 레시피 추천까지 LangGraph 워크플로우 실행.
    응답에 LLM 맞춤 퀘스트(quests)를 포함.
    """
    # constraints 파싱
    try:
        constraints_dict = json.loads(constraints) if constraints else {}
        if not isinstance(constraints_dict, dict):
            raise ValueError
    except Exception:
        raise HTTPException(status_code=400, detail="'constraints'가 유효한 JSON 객체 문자열이 아닙니다.")

    # 이미지 → base64
    try:
        image_base64 = base64.b64encode(file).decode("utf-8")
    except Exception:
        raise HTTPException(status_code=400, detail="이미지 바이트 처리에 실패했습니다.")

    # LangGraph 실행
    initial_state = {
        "image_base64": image_base64,
        "constraints": constraints_dict,
    }
    try:
        final_state = image_app.invoke(
            initial_state,
            config={"configurable": {"thread_id": "image_analysis_thread"}},
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"LangGraph 실행 중 오류: {e}")

    # ✅ LLM 맞춤 퀘스트 생성
    quests = generate_dynamic_quests(final_state.get("inventory", {}), constraints_dict)

    # 최종 반환
    return {
        "inventory": final_state.get("inventory", {}),
        "recipes": final_state.get("recipes", []),
        "quests": quests,
    }

# 퀘스트 완료 → XP 적립 & DB 저장
@app.post("/quests/complete", tags=["퀘스트"])
async def complete_quest(
    body: dict = Body(...),
    x_user_id: Optional[str] = Header(default=None, convert_underscores=False),
):
    """
    프론트에서 퀘스트를 완료했을 때 호출.
    body 예:
    {
      "quest_id": "q1",
      "title": "아보카도 샐러드 만들기",
      "xp": 25,
      "reason": "임박 재료 사용 보너스",
      "payload": { ...원하면 추가 정보... }
    }
    """
    user_id = x_user_id or "local"  # 헤더 X-User-Id 없으면 local로 집계
    quest_id = str(body.get("quest_id") or "")
    title = str(body.get("title") or "퀘스트")
    xp = int(body.get("xp") or 0)
    reason = str(body.get("reason") or "")
    payload = body.get("payload") or {}

    if xp <= 0:
        raise HTTPException(status_code=400, detail="xp가 1 이상이어야 합니다.")
    try:
        add_xp(user_id=user_id, xp=xp, quest_id=quest_id, title=title, reason=reason, payload=payload)
        prof = get_profile(user_id)
        return {"ok": True, "profile": prof}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"퀘스트 저장 오류: {e}")

# 사용자 프로필(누적 XP/최근 로그)
@app.get("/profile", tags=["퀘스트"])
async def read_profile(x_user_id: Optional[str] = Header(default=None, convert_underscores=False)):
    user_id = x_user_id or "local"
    return get_profile(user_id)

@app.post("/chat", tags=["챗봇"])
async def chat_with_agent(message: str):
    """
    챗봇 형식으로 AI 에이전트와 대화
    """
    try:
        initial_state = {"chat_message": message}
        final_state = agent_workflow.invoke(initial_state)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"에이전트 실행 오류: {e}")

    response_data = {
        "response": final_state.get("response", "요청을 처리할 수 없습니다.")
    }
    try:
        if final_state.get("intent", {}).get("intent") == "get_recipes":
            shopping_list_data = final_state.get("shopping_list")
            if shopping_list_data is not None:
                response_data["shopping_list"] = shopping_list_data
    except Exception:
        pass
    return response_data

# --- 보조 기능 ---
@app.get("/inventory", tags=["보조 기능"])
def read_inventory():
    """현재 저장된 재고 목록"""
    inventory_agent = InventoryAgent()
    current_inventory = inventory_agent.load_inventory()
    return {"items": current_inventory}
