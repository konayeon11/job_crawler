# ai-nutritionist-agent (skeleton)

협업용 기본 뼈대만 포함합니다. 구현 코드는 각자 feat/* 브랜치에서 진행 후 PR로 dev에 병합합니다.

## 구조
```plaintext
📦 ai-nutritionist-agent
│
├── agents/                     # 각 기능별 AI Agent 모듈
│   ├── __init__.py
<<<<<<< HEAD
│   ├── vision_agent.py         # 냉장고 이미지 분석
│   ├── online_order_agent      # 온라인 주문 데이터를 처리
=======
│   ├── vision_agent.py         # 냉장고/영수증 이미지 분석
>>>>>>> you
│   ├── inventory_agent.py      # 재고·유통기한 관리
│   ├── recipe_agent.py         # 맞춤형 레시피 추천
│   ├── planner_agent.py        # 주간 식단·쇼핑리스트 생성
│   └── nutrition_agent.py      # 영양분 분석 및 피드백
│
├── core/                       # LangGraph / Memory / Utils 등 핵심 로직
│   ├── __init__.py
│   ├── graph_builder.py        # 멀티에이전트 플로우 정의
│   ├── memory_manager.py       # 세션·장기 기억 관리
│   └── utils.py                # 공용 유틸 함수
│
├── api/                        # FastAPI 기반 서버 엔트리포인트
│   ├── __init__.py
│   ├── main.py                 # FastAPI 엔트리 포인트
│   └── schema.py               # Pydantic 데이터 모델 정의
│
├── data/                       # 샘플 데이터 / 리소스
│   └── sample_inventory.json
│
├── tests/                      # 단위 테스트 코드
│   ├── test_agents.py
│   ├── test_api.py
│   └── test_memory.py
│
├── README.md                   # 프로젝트 개요 및 실행 가이드
├── requirements.txt             # 패키지 의존성 목록
└── .gitignore                   # 캐시·환경파일 제외 설정
```


## 빠른 실행 (개발용)
pip install -r requirements.txt
uvicorn api.main:app --reload

## 브랜치 전략
- main: 배포/안정
- dev: 통합 개발
- feat/*: 개인 기능 브랜치 → PR → dev
<<<<<<< HEAD

# 🍳 RecipeAgent — 인벤토리 기반 맞춤 레시피 추천

냉장고 속 재료와 사용자 제약조건을 바탕으로, 신뢰 가능한 출처(있다면 URL 포함) 또는 합성(synthetic) 레시피를 한국어로 추천합니다.  
기본 양념(물, 소금, 간장, 후추, 식용유 등)은 누락 재료에서 자동 제외됩니다.

──────────────────────────────
✨ 주요 기능
──────────────────────────────
- ✅ 알레르기 / 기피 식품 자동 필터링
- ✅ 인벤토리 교집합(uses) + 누락(missing) 계산
- ✅ 식단(diet), 건강 목표, 시간 제약 반영
- ✅ 출처 URL 포함 (없으면 synthetic)
- ✅ 마케팅 톤의 ‘한 줄 요약’ 생성 (customer_card)
- ❌ ‘재가열’ 항목은 출력하지 않음

──────────────────────────────
📦 설치 및 실행
──────────────────────────────
pip install -r requirements.txt

# 최종 결과(JSON)만 보기
python agents/recipe_agent.py --debug --pretty

# 인벤토리 파일 지정 실행
python agents/recipe_agent.py --debug --inv data/sample_inventory.json --pretty

환경변수 설정:
export OPENAI_API_KEY="sk-..."

──────────────────────────────
🔌 인터페이스 개요
──────────────────────────────
함수:
suggest_recipes(ingredients: List[str], constraints: Dict[str, Any]) -> List[Dict[str, Any]]

입력값 예시:
{
  "ingredients": ["계란", "양파", "대파"],
  "constraints": {
    "target_count": 3,
    "max_missing": 2,
    "diet": "low_sodium",
    "time_max": 20
  }
}

──────────────────────────────
📤 반환값 구조 (프론트 계약)
──────────────────────────────
[
  {
    "id": "dabc3dd854a96882",
    "title": "대파 계란 볶음",
    "ingredients": ["계란","대파","양파"],
    "steps": ["대파와 양파를 볶는다", "풀어둔 계란을 넣는다", "간을 맞춘다"],
    "time_minutes": 15,
    "time_breakdown": {"prep":5, "cook":10, "total":15},
    "servings": 2,
    "difficulty": "쉬움",
    "tags": ["한식","간단"],
    "source": {"name": "한국 요리 블로그", "url": "https://koreanfoodblog.com"},
    "nutrition": {"calories_kcal":250, "protein_g":15.0, "carbs_g":20.0, "fat_g":10.0, "sodium_mg":150},
    "uses": ["계란","대파","양파"],
    "missing": [],
    "suitability": {
      "summary": "빠르고 담백한 한 끼",
      "health": "저염 조리로 부담 적음",
      "inventory": "계란·대파·양파 활용",
      "time": "15분 내",
      "occasion": "일상 반찬",
      "skill": "초보자 적합",
      "tips": ["대파 먼저 볶아 향 올리기"]
    },
    "storage": "냉장 1일 권장",
    "customer_card": "• 한 줄 요약: 냉장고 속 계란, 대파로 · 저염 한끼 · 집밥 감성 — 지금 바로 즐기는 「대파 계란 볶음」\n• 영양 요약(1인분): 250 kcal, 단백질 15.0g, 탄수화물 20.0g, 지방 10.0g, 나트륨 150mg\n• 추천 이유: 저염식, 인벤토리 최대 활용, 15분 컷\n• 냉장고에서 사용하는 재료: 계란, 대파, 양파\n• 보관: 냉장 1일 권장"
  }
]


=======
>>>>>>> you
