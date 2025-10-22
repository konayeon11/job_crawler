from fastapi import APIRouter, Body
from typing import List
from core.models import Recipe, Ingredient, DailyMealPlan, ShoppingList
from agents.planner_agent import create_daily_plan_and_shopping_list
from core.memory_manager import load_session, save_session
from pydantic import BaseModel

router = APIRouter()

class PlannerRequest(BaseModel):
    user_selected_recipes: List[Recipe]
    current_inventory: List[Ingredient]

@router.post("/daily-plan", response_model=DailyMealPlan)
def get_daily_plan(request: PlannerRequest = Body(...)):
    """
    사용자가 선택한 레시피와 현재 재고를 바탕으로 일일 식단과 쇼핑 리스트를 생성합니다.
    """
    meal_plan, shopping_list = create_daily_plan_and_shopping_list(
        user_selected_recipes=request.user_selected_recipes,
        current_inventory=request.current_inventory
    )
    # For now, this endpoint only returns the meal plan.
    # We can create another endpoint for the shopping list.
    return meal_plan

@router.post("/shopping-list", response_model=ShoppingList)
def get_shopping_list(request: PlannerRequest = Body(...)):
    """
    사용자가 선택한 레시피와 현재 재고를 바탕으로 쇼핑 리스트를 생성하고,
    결과를 세션에 저장합니다.
    """
    # meal_plan은 현재 사용되지 않으므로 _로 받음
    _, shopping_list = create_daily_plan_and_shopping_list(
        user_selected_recipes=request.user_selected_recipes,
        current_inventory=request.current_inventory
    )

    # 세션에 쇼핑 리스트 저장
    # TODO: 실제 프로덕션에서는 헤더나 쿠키에서 세션 ID를 동적으로 받아와야 합니다.
    session_id = "default_session"
    session_state = load_session(session_id)
    session_state["shopping_list"] = shopping_list.dict() # Pydantic 모델을 dict로 변환
    save_session(session_id, session_state)

    return shopping_list
