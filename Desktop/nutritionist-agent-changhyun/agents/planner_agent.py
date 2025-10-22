"""
PlannerAgent: 사용자가 선택한 레시피를 바탕으로 일일 식단을 계획하고,
부족한 재료로 쇼핑 리스트를 생성합니다.
"""
import os
from typing import List
from openai import OpenAI
from dotenv import load_dotenv

from core.models import Recipe, DailyMealPlan, ShoppingList, ShoppingItem, Ingredient

# .env 파일에서 환경 변수 로드
load_dotenv()

def create_daily_plan_and_shopping_list(
    user_selected_recipes: List[Recipe],
    current_inventory: List[Ingredient]
) -> (DailyMealPlan, ShoppingList):
    """
    사용자가 선택한 레시피와 현재 재고를 바탕으로 일일 식단과 쇼핑 리스트를 생성합니다.

    Args:
        user_selected_recipes (List[Recipe]): 사용자가 선택한 레시피 목록
        current_inventory (List[Ingredient]): 현재 재고 목록

    Returns:
        (DailyMealPlan, ShoppingList): 생성된 일일 식단과 쇼핑 리스트
    """
    # 1. 식단 생성
    # 현재는 간단하게 아침, 점심, 저녁으로 할당합니다.
    # 추후, 사용자가 식사 시간을 선택할 수 있도록 확장할 수 있습니다.
    meal_plan = DailyMealPlan()
    if len(user_selected_recipes) > 0:
        meal_plan.breakfast = user_selected_recipes[0].name
    if len(user_selected_recipes) > 1:
        meal_plan.lunch = user_selected_recipes[1].name
    if len(user_selected_recipes) > 2:
        meal_plan.dinner = user_selected_recipes[2].name

    # 2. 쇼핑 리스트 생성
    shopping_list = ShoppingList(items=[])
    
    # 필요한 모든 재료 집계
    required_ingredients = {}
    for recipe in user_selected_recipes:
        for ingredient in recipe.ingredients:
            if ingredient.name in required_ingredients:
                required_ingredients[ingredient.name] += ingredient.quantity
            else:
                required_ingredients[ingredient.name] = ingredient.quantity

    # 현재 재고와 비교하여 부족한 재료 파악
    missing_ingredients = {}
    inventory_dict = {item.name: item.quantity for item in current_inventory}
    
    for name, required_qty in required_ingredients.items():
        if name not in inventory_dict or inventory_dict[name] < required_qty:
            missing_qty = required_qty - (inventory_dict.get(name, 0))
            missing_ingredients[name] = missing_qty

    # 부족한 재료로 쇼핑 리스트 생성
    for name, qty in missing_ingredients.items():
        # LLM을 사용하여 상품 URL 검색
        url = get_product_url_from_llm(name)
        shopping_list.items.append(
            ShoppingItem(name=name, quantity=str(qty), url=url)
        )

    return meal_plan, shopping_list


def get_product_url_from_llm(item_name: str) -> str:
    """
    Uses the OpenAI API to generate a Coupang search URL for the given item name.
    Includes a fallback to manual URL generation if the API fails or returns an invalid URL.
    """
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        # Fallback if API key is not set
        from urllib.parse import quote
        return f"https://www.coupang.com/np/search?q={quote(item_name)}"

    client = OpenAI(api_key=api_key)

    prompt = f"'{item_name}'에 대한 쿠팡(Coupang) 검색 URL을 만들어줘. 다른 설명 없이 URL만 응답해줘."

    try:
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "You are a bot that creates a valid Coupang search URL for a given product name. You only return a single URL and nothing else."},
                {"role": "user", "content": prompt}
            ],
            temperature=0,
            max_tokens=200
        )
        raw_response = response.choices[0].message.content.strip()

        # More flexible check for a valid Coupang search URL
        if raw_response.startswith("https://www.coupang.com/np/search?") and "q=" in raw_response:
            return raw_response
        else:
            # If the LLM fails, fall back to manual URL encoding as a safeguard
            from urllib.parse import quote
            return f"https://www.coupang.com/np/search?q={quote(item_name)}"
    except Exception:
        # Fallback in case of any API error
        from urllib.parse import quote
        return f"https://www.coupang.com/np/search?q={quote(item_name)}"
