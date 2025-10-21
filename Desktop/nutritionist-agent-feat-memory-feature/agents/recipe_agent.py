"""
Service-friendly RecipeAgent (GPT-only, Marketing Copy + Clean Output)

요청 반영:
- 🔥 '한 줄 요약'을 사용자 프로필(식단/선호/시간/건강문맥/인벤토리)을 기반으로
  마케팅 카피톤으로 생성하여 카드 최상단에 표시
- ✅ 신뢰 출처 URL(있으면) 포함, 모든 텍스트 한국어
- 🧠 풍부한 정보 유지: 영양, 알레르겐, 장비, 대체재, 보관/재가열, 팁, 경고 등
- 🧩 인벤토리 교집합(uses) + STOPWORDS 제외 누락(missing) 계산
- 🔒 품질 필터: 인벤토리 최소 1개 일치 & 누락 ≤ max_missing
- 🏁 정렬: 누락 0 → 누락 적음 → 매칭 많음 → 점수

의존성: openai, pydantic
"""

from __future__ import annotations
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass
from pydantic import BaseModel, Field
import os, re, json, unicodedata, logging, hashlib

# --- .env 로드 ---
from dotenv import load_dotenv
load_dotenv()

# --- DB Import ---
from core.database import DatabaseManager

# ------------------- 로깅 -------------------
logger = logging.getLogger("recipe_agent")
if not logger.handlers:
    h = logging.StreamHandler()
    h.setFormatter(logging.Formatter("[%(levelname)s] %(message)s"))
    logger.addHandler(h)
logger.setLevel(logging.INFO)

# ------------------- 정규화/동의어/필터 -------------------
STOPWORDS = {"약간","적당량","조금","소금","후추","식용유","물","참기름","설탕","간장","식초","다진마늘","다시다","치킨스톡"}
SYNONYM_MAP = {"egg":{"계란","달걀"}, "pork":{"돼지 고기","돼지고기"}, "beef":{"소 고기","소고기"}, "tofu":{"두부"}, "garlic":{"마늘"}, "onion":{"양파"}, "kimchi":{"김치"}}

def _normalize(s: str) -> str:
    if s is None: return ""
    return unicodedata.normalize("NFKC", str(s).strip().lower())

def _expand_synonyms(token: str) -> set[str]:
    token = _normalize(token)
    ex = {token}
    for _, syns in SYNONYM_MAP.items():
        if token in syns:
            ex |= set(_normalize(x) for x in syns)
    return ex

def _stable_id(*parts: str) -> str:
    h = hashlib.sha256()
    for p in sorted(parts):
        h.update((_normalize(p) + "|").encode("utf-8"))
    return h.hexdigest()[:16]

# ------------------- 데이터 모델 -------------------
class SourceModel(BaseModel): name: Optional[str] = None; url: Optional[str] = None
class NutritionModel(BaseModel): calories_kcal: Optional[int] = None; protein_g: Optional[float] = None; carbs_g: Optional[float] = None; fat_g: Optional[float] = None; sodium_mg: Optional[int] = None
class SuitabilityModel(BaseModel): summary: Optional[str] = None; health: Optional[str] = None; inventory: Optional[str] = None; time: Optional[str] = None; occasion: Optional[str] = None; skill: Optional[str] = None; tips: Optional[List[str]] = None; warnings: Optional[List[str]] = None
class RecipeItem(BaseModel): title: str; ingredients: List[str]; steps: List[str]; time_minutes: Optional[int] = None; difficulty: Optional[str] = None; tags: Optional[List[str]] = None; servings: Optional[int] = None; time_breakdown: Optional[Dict[str,int]] = None; source: Optional[SourceModel] = None; nutrition: Optional[NutritionModel] = None; allergens: Optional[List[str]] = None; equipment: Optional[List[str]] = None; substitutions: Optional[Dict[str, List[str]]] = None; storage: Optional[str] = None; reheat: Optional[str] = None; suitability: Optional[SuitabilityModel] = None

@dataclass
class _Candidate: rec: RecipeItem; score: float; missing_count: int; matched_count: int; uses: List[str]; missing: List[str]

# ------------------- 매칭/스코어링 -------------------
def _tokenize_ings(ings: List[str]) -> List[str]:
    out = set()
    for raw in ings:
        if not isinstance(raw, str): continue
        s = re.sub(r"\([^)]*\)", "", raw)
        s = re.sub(r"[\d./]+(g|kg|ml|l|개|컵|스푼|큰술|작은술|쪽|마리|줌|장|ea)\b", "", s, flags=re.I)
        parts = re.split(r'[,/·•|]', s)
        for p in parts:
            t = _normalize(p.strip())
            if t and t not in STOPWORDS:
                out.add(t)
    return sorted(list(out))

def _match_and_missing(inv: List[str], rec_ing: List[str]) -> Tuple[List[str], List[str]]:
    inv_names = {_normalize(x) for x in inv}
    rec_tokens = set(_tokenize_ings(rec_ing))
    matched, missing = [], []
    for need in rec_tokens:
        hit = any(need in _expand_synonyms(iv) or iv in _expand_synonyms(need) for iv in inv_names)
        if hit: matched.append(need)
        else: missing.append(need)
    return sorted(matched), sorted(missing)

def _score_recipe(rec: RecipeItem, inventory: List[str], constraints: Dict[str, Any]) -> Optional[_Candidate]:
    max_missing = int(constraints.get("max_missing", 3))
    uses, missing = _match_and_missing(inventory, rec.ingredients)
    if not uses or len(missing) > max_missing:
        return None
    
    health_bonus = 0
    diet = (constraints.get("dietary_goals") or "").lower()
    if diet == "low_sodium" and rec.nutrition and rec.nutrition.sodium_mg is not None and rec.nutrition.sodium_mg <= 700:
        health_bonus += 8
        
    coverage = len(uses) / max(1, len(uses) + len(missing))
    score = (100 if len(missing) == 0 else 60 - 5*len(missing)) + 40*coverage + health_bonus
    
    return _Candidate(rec=rec, score=score, missing_count=len(missing), matched_count=len(uses), uses=uses, missing=missing)

# ------------------- OpenAI 유틸 -------------------
def _openai_client(constraints: Dict[str, Any]):
    try: from openai import OpenAI
    except ImportError: logger.error("openai library not found. pip install openai"); return None
    api_key = constraints.get("openai_api_key") or os.getenv("OPENAI_API_KEY")
    if not api_key: logger.warning("OPENAI_API_KEY not set; OpenAI stages will be skipped."); return None
    os.environ["OPENAI_API_KEY"] = api_key
    return OpenAI()

def _parse_json_safe(txt: str) -> Any:
    txt = (txt or "").strip()
    match = re.search(r"\{.*\}|.*\[.*\]", txt, re.DOTALL)
    if not match: return None
    try: return json.loads(match.group(0))
    except json.JSONDecodeError: return None

# ------------------- LLM 스키마/프롬프트/호출 -------------------
def _schema_spec() -> Dict[str, Any]:
    return {"type":"object", "required":["recipes"], "properties":{"recipes":{"type":"array", "items":RecipeItem.model_json_schema()}}}

def _synthesize_prompt(inv: List[str], constraints: Dict[str, Any], need: int) -> Dict[str, Any]:
    system = ("당신은 사용자의 재료와 요구사항에 맞춰 창의적인 레시피를 생성하는 전문 셰프입니다. "
              "모든 텍스트는 한국어로, 최종 결과는 JSON 형식으로만 응답해야 합니다. "
              "레시피의 모든 세부 정보(시간 분할, 알레르기 유발 물질, 필요한 장비, 대체 재료, 보관 및 재가열 방법, 적합성)를 최대한 상세하게 채워주세요.")
    
    user_constraints_str = ""
    if constraints.get("allergies"):
        user_constraints_str += f" - 알레르기: {', '.join(constraints['allergies'])} (이 재료는 절대 사용하지 마세요.)\n"
    if constraints.get("preferences", {}).get("dislikes"):
        user_constraints_str += f" - 기피 재료: {', '.join(constraints['preferences']['dislikes'])} (이 재료는 사용하지 마세요.)\n"
    if constraints.get("dietary_goals"):
        user_constraints_str += f" - 식단 목표: {constraints['dietary_goals']}\n"
    if constraints.get("time_max"):
        user_constraints_str += f" - 최대 소요 시간: {constraints['time_max']}분 이내\n"

    user = {
        "output_contract": _schema_spec(),
        "instruction": (f"다음 조건에 맞는 레시피 {need}개를 생성해주세요. JSON 외의 텍스트는 절대 포함하지 마세요.\n"
                        f"각 레시피에 대해 다음 필드를 상세하게 채워주세요:\n"
                        f"  - `time_minutes`: 총 소요 시간 (분)\n"
                        f"  - `difficulty`: 레시피 난이도 (예: 쉬움, 보통, 어려움)\n"
                        f"  - `tags`: 레시피 관련 태그 목록 (예: ['한식', '간편식'])\n"
                        f"  - `servings`: 레시피 제공량 (예: 2인분)\n"
                        f"  - `time_breakdown`: 준비 시간과 요리 시간을 분리하여 (예: {{'prep': 10, 'cook': 20}})\n"
                        f"  - `nutrition`: 추정 영양 정보 (calories_kcal, protein_g, carbs_g, fat_g, sodium_mg 필드 포함, 없으면 null)\n"
                        f"  - `allergens`: 레시피에 포함된 주요 알레르기 유발 물질 목록 (없으면 빈 리스트)\n"
                        f"  - `equipment`: 필요한 주요 조리 도구 목록 (없으면 빈 리스트)\n"
                        f"  - `substitutions`: 주요 재료에 대한 대체 재료 제안 (예: {{'닭고기': ['돼지고기', '두부']}})\n"
                        f"  - `storage`: 조리 후 보관 방법 및 기간\n"
                        f"  - `reheat`: 재가열 방법\n"
                        f"  - `suitability`: 레시피의 적합성 요약 (summary, health, inventory, time, occasion, skill, tips, warnings 필드 포함)\n"
                        f"사용자 제약 조건: \n{user_constraints_str if user_constraints_str else '없음'}\n"),
        "context": {"inventory": inv, "constraints": constraints}
    }
    return {"system": system, "user": user}

def _openai_call(system: str, user_payload: Dict[str, Any], constraints: Dict[str, Any]):
    client = _openai_client(constraints)
    if not client: return None
    model = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
    try:
        resp = client.chat.completions.create(
            model=model,
            messages=[{"role":"system", "content": system}, {"role":"user", "content": json.dumps(user_payload, ensure_ascii=False)}],
            temperature=0.6,
            response_format={"type": "json_object"}
        )
        return resp.choices[0].message.content
    except Exception as e: logger.error(f"OpenAI call failed: {e}"); return None

def _openai_generate_recipes(inventory: List[str], constraints: Dict[str, Any], need: int) -> List[RecipeItem]:
    p = _synthesize_prompt(inventory, constraints, need)
    raw = _openai_call(p["system"], p["user"], constraints)
    data = _parse_json_safe(raw) if raw else None
    items = (data or {}).get("recipes", [])
    out: List[RecipeItem] = []
    for r in items:
        try:
            r["source"] = {"name": "AI 생성 레시피"}
            out.append(RecipeItem(**r))
        except Exception as e:
            logger.warning(f"Failed to parse a generated recipe: {e}")
            continue
    return out

# ------------------- 마케팅 카피 / UI 카드 생성 -------------------
def _marketing_headline(rec: RecipeItem, uses: List[str], constraints: Dict[str, Any]) -> str:
    focus = []
    if uses: focus.append(f"냉장고 속 {', '.join(uses[:2])} 활용")
    if constraints.get("time_max"): focus.append(f"{constraints.get('time_max')}분 완성")
    if constraints.get("dietary_goals") == "low_sodium": focus.append("건강한 저염식")
    if not focus: focus.append("오늘의 특별 메뉴")
    return f"{ ' · '.join(focus)}: 「{rec.title}」"

def _build_customer_card(rec: RecipeItem, uses: List[str], missing: List[str], constraints: Dict[str, Any]) -> str:
    lines = [f"• 한 줄 요약: {_marketing_headline(rec, uses, constraints)}"]
    if rec.nutrition:
        macro = [f"{v} {k.split('_')[1].upper()}" for k, v in rec.nutrition.model_dump().items() if v is not None]
        if macro: lines.append("• 영양 정보 (1인분): " + ", ".join(macro))
    if rec.suitability:
        for key, value in rec.suitability.model_dump().items():
            if value: lines.append(f"• {key.capitalize()}: {value if isinstance(value, str) else ', '.join(value)}")
    if uses: lines.append("• 사용하는 재료: " + ", ".join(uses))
    if missing: lines.append("• 필요한 재료: " + ", ".join(missing))
    return "\n".join(lines)

# ------------------- 공개 인터페이스 -------------------
def suggest_recipes(ingredients: List[str], constraints: Dict[str, Any]) -> List[Dict[str, Any]]:
    # --- DB 연동: 사용자 설정 로드 ---
    db_manager = DatabaseManager()
    user_prefs = db_manager.get_user_preferences("default_user")
    db_manager.close()

    # DB 설정과 API 요청 제약을 병합 (API 요청이 우선)
    final_constraints = {**user_prefs, **constraints}
    logger.info(f"Final constraints for recipe generation: {final_constraints}")

    target = int(final_constraints.get("target_count", 3))
    inv_norm = [_normalize(x) for x in ingredients if _normalize(x)]
    
    generated_recipes = _openai_generate_recipes(inv_norm, final_constraints, need=target * 2)
    
    cands: List[_Candidate] = []
    for r in generated_recipes:
        cand = _score_recipe(r, inv_norm, final_constraints)
        if cand: cands.append(cand)

    cands.sort(key=lambda c: (c.missing_count, -c.matched_count, -c.score))
    
    results: List[Dict[str, Any]] = []
    seen_titles = set()
    for c in cands:
        if c.rec.title in seen_titles: continue
        seen_titles.add(c.rec.title)
        
        rec_dict = c.rec.model_dump()
        rec_dict["id"] = _stable_id(c.rec.title, *c.rec.ingredients)
        rec_dict["uses"] = c.uses
        rec_dict["missing"] = c.missing
        rec_dict["customer_card"] = _build_customer_card(c.rec, c.uses, c.missing, final_constraints)
        results.append(rec_dict)
        
        if len(results) >= target:
            break

    logger.info(f"레시피 추천 완료: {len(results)}개 반환")
    return results

# ------------------- CLI 테스트 -------------------
if __name__ == "__main__":
    inv = ["돼지고기", "김치", "양파", "두부", "계란", "오이", "새우"]
    # 제약조건은 이제 DB에서 불러옵니다.
    constraints = {"target_count": 2, "max_missing": 2}
    
    print("-" * 20)
    print(f"테스트 인벤토리: {inv}")
    print("DB에서 불러올 사용자 설정: 알레르기=['새우'], 기피=['오이'], 식단='저탄수화물'")
    print("-" * 20)

    recipes = suggest_recipes(inv, constraints)
    print(json.dumps(recipes, indent=2, ensure_ascii=False))

    print("\n" + "-" * 20)
    print("결과 검증")
    print("-" * 20)
    found_issue = False
    for recipe in recipes:
        for ingredient in recipe['ingredients']:
            if '새우' in ingredient:
                logger.error(f"검증 실패: 레시피 '{recipe['title']}'에 알레르기 항목인 '새우'가 포함되었습니다.")
                found_issue = True
            if '오이' in ingredient:
                logger.error(f"검증 실패: 레시피 '{recipe['title']}'에 기피 재료인 '오이'가 포함되었습니다.")
                found_issue = True
    
    if not found_issue:
        logger.info("검증 성공: 추천된 모든 레시피가 사용자의 알레르기 및 기피 재료 설정을 준수했습니다.")