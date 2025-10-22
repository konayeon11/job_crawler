import os
import json
from typing import List, Tuple, Dict, Any
from openai import OpenAI
from dotenv import load_dotenv
from urllib.parse import quote

# core/models.py 파일이 있다는 가정 하에 모델들을 가져옵니다.
from core.models import DailyMealPlan, ShoppingList, ShoppingItem

# .env 파일에서 환경 변수 로드
load_dotenv()

def create_daily_plan_and_shopping_list(
    user_selected_recipes: List[Dict],
    current_inventory: Dict
) -> Tuple[DailyMealPlan, ShoppingList]:
    """
    사용자가 선택한 레시피와 현재 재고를 바탕으로 일일 식단과 쇼핑 리스트를 생성합니다.
    """
    # 1. 식단 생성
    meal_plan = DailyMealPlan()
    if len(user_selected_recipes) > 0:
        meal_plan.breakfast = user_selected_recipes[0].get('title')
    if len(user_selected_recipes) > 1:
        meal_plan.lunch = user_selected_recipes[1].get('title')
    if len(user_selected_recipes) > 2:
        meal_plan.dinner = user_selected_recipes[2].get('title')

    # 2. 쇼핑 리스트 생성
    shopping_list = ShoppingList(items=[])
    
    missing_ingredients = set()
    for recipe in user_selected_recipes:
        for item in recipe.get("missing", []):
            missing_ingredients.add(item)
    
    print(f"Planner Agent: 부족한 재료 목록: {list(missing_ingredients)}")

    # 부족한 재료로 쇼핑 리스트 생성
    for name in missing_ingredients:
        # ✨ 수정된 URL 생성 함수를 호출합니다 ✨
        url = _generate_shopping_url(name)
        shopping_list.items.append(
            ShoppingItem(name=name, quantity="필요한 만큼", url=url)
        )

    return meal_plan, shopping_list


# --- ✨ URL 생성 로직 전체 수정 ✨ ---
def _generate_shopping_url(item_name: str) -> str:
    """
    LLM을 사용해 최적의 '검색 키워드'를 찾고, 파이썬으로 안정적인 URL을 생성합니다.
    """
    api_key = os.getenv("OPENAI_API_KEY")
    search_keyword = "" # 검색 키워드를 담을 변수

    if not api_key:
        # API 키가 없으면, 직접 인코딩하여 기본 URL을 반환합니다.
        search_keyword = item_name.split(",")[0].split("(")[0].strip()
    else:
        client = OpenAI(api_key=api_key)
        # 프롬프트: URL 대신 '검색 키워드'를 요청하도록 변경
        prompt = f"'{item_name}'을 쿠팡 같은 온라인 쇼핑몰에서 검색하기 위한 가장 좋은 검색 키워드 하나만 알려줘. 다른 설명은 모두 빼고 오직 검색 키워드만 응답해줘. (예: '돼지고기 목살 300g' -> '돼지고기 목살')"

        try:
            response = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": "You are a helpful assistant that extracts the best search keyword from a given product description."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0,
                max_tokens=50
            )
            # ✨ LLM 응답에서 URL이나 다른 텍스트가 섞여도 키워드만 남도록 처리 ✨
            llm_response = response.choices[0].message.content.strip().replace('"', '')
            # 만약 응답에 공백이 있다면 첫 단어만 키워드로 간주 (더 안정적)
            search_keyword = llm_response.split(" ")[0]

        except Exception as e:
            # API 오류 발생 시, 직접 키워드를 추출하는 fallback 로직
            print(f"LLM 키워드 추출 중 오류 발생: {e}. 기본 키워드를 사용합니다.")
            search_keyword = item_name.split(",")[0].split("(")[0].strip()

    # ✨ 최종 URL 생성은 항상 파이썬이 담당 ✨
    # 파이썬의 quote 함수를 사용하여 안정적으로 URL을 생성합니다.
    encoded_keyword = quote(search_keyword)
    print(f"'{item_name}' -> 검색 키워드: '{search_keyword}' -> URL 생성")
    return f"https://www.coupang.com/np/search?q={encoded_keyword}"


# --- 단위 테스트 ---
if __name__ == '__main__':
    print("Planner Agent 단위 테스트를 시작합니다...")
    
    sample_recipes = [
        {"title": "돼지고기 김치찌개", "missing": ["돼지고기 목살 300g", "두부 반 모"]}
    ]
    sample_inventory = {}
    
    meal_plan, shopping_list = create_daily_plan_and_shopping_list(sample_recipes, sample_inventory)

    print("\n[생성된 식단 계획]:")
    print(meal_plan.model_dump_json(indent=2, ensure_ascii=False))

    print("\n[생성된 쇼핑 리스트 (URL 포함)]:")
    print(shopping_list.model_dump_json(indent=2, ensure_ascii=False))
    
    assert "coupang.com" in shopping_list.items[0].url
    print("\n테스트 성공!")

