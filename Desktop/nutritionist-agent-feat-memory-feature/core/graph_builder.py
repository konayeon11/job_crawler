from langgraph.graph import StateGraph, END
from typing import TypedDict, List, Dict, Any, Optional
import base64
from datetime import date, datetime, timedelta # datetime, timedelta 임포트 추가

# --- 필요한 모든 에이전트와 모델들을 가져옵니다 ---
from agents.vision_agent import VisionAgent
from agents.inventory_agent import InventoryAgent
from agents.recipe_agent import suggest_recipes as suggest_recipes_from_agent
from agents.planner_agent import create_daily_plan_and_shopping_list
from agents.chat_agent import ChatAgent # ChatAgent 임포트
from core.models import DailyMealPlan, ShoppingList # DatabaseManager 임포트
from core.database import DatabaseManager

# --- 상태 정의 ---
class AgentState(TypedDict):
    image_base64: Optional[str] # 챗봇 입력 시에는 없을 수 있음
    chat_message: Optional[str] # 챗봇 입력 메시지
    intent: Optional[Dict[str, Any]] # ChatAgent가 파악한 의도
    constraints: Optional[Dict[str, Any]]
    new_items: List[dict]
    inventory: Dict
    ingredients: List[str]
    recipes: List[Dict]
    meal_plan: Optional[DailyMealPlan]
    shopping_list: Optional[ShoppingList]
    response: Optional[str] # 챗봇 응답을 위한 필드 추가

# --- 에이전트 인스턴스 ---
vision_agent = VisionAgent()
inventory_agent = InventoryAgent()
chat_agent = ChatAgent() # ChatAgent 인스턴스 추가

# --- 그래프 노드 함수 ---
def run_chat_agent(state: AgentState) -> dict:
    # print("--- Chat Agent 실행: 의도 파악 ---") # 임시 주석 처리
    chat_message = state.get("chat_message")
    if not chat_message:
        return {"intent": {"intent": "general_chat", "response": "메시지가 없습니다."}}
    
    intent_data = chat_agent.determine_intent(chat_message)
    # print(f"파악된 의도: {intent_data}") # 임시 주석 처리
    return {"intent": intent_data}

# ... (other functions)

def general_chat_response_node(state: AgentState) -> dict:
    # print("--- 일반 채팅 응답 노드 실행 ---") # 임시 주석 처리
    intent_data = state.get("intent", {})
    response_message = intent_data.get("response", "무슨 말씀이신지 잘 모르겠습니다.")
    return {"response": response_message}

def run_vision_agent(state: AgentState) -> dict:
    print("--- 1. Vision Agent 실행 ---")
    image_base64 = state["image_base64"]
    new_items = vision_agent.analyze_image(image_base64)
    ingredients = [item.get("item_name") for item in new_items if item.get("item_name")]
    return {"new_items": new_items, "ingredients": ingredients}

def run_inventory_agent(state: AgentState) -> dict:
    print("--- 2. Inventory Agent 실행 ---")
    new_items = state["new_items"]
    updated_inventory = inventory_agent.update_inventory(new_items)
    return {"inventory": updated_inventory}

def run_recipe_agent(state: AgentState) -> dict:
    print("--- 3. Recipe Agent 실행 ---")
    # ingredients는 vision_node 또는 chat_node에서 올 수 있음
    ingredients = state.get("ingredients")
    if not ingredients and state.get("intent") and state["intent"].get("ingredients"):
        ingredients = state["intent"]["ingredients"]
    
    if not ingredients:
        print("레시피 추천을 위한 재료가 없습니다.")
        return {"recipes": []}

    constraints = state.get("constraints") or {}
    recipes = suggest_recipes_from_agent(ingredients=ingredients, constraints=constraints)
    return {"recipes": recipes}

# --- ✨ PlannerAgent를 위한 노드 수정 ✨ ---
def run_planner_agent(state: AgentState) -> dict:
    print("--- 4. Planner Agent 실행 ---")
    recipes = state.get("recipes", [])
    inventory = state.get("inventory", {})
    
    if not recipes:
        return {}

    # PlannerAgent 함수를 직접 호출합니다.
    meal_plan, shopping_list = create_daily_plan_and_shopping_list(
        user_selected_recipes=recipes, # 실제 앱에서는 사용자가 선택한 레시피
        current_inventory=inventory
    )
    
    return {"meal_plan": meal_plan, "shopping_list": shopping_list}

def log_meal_history(state: AgentState) -> dict:
    print("--- 5. 식단 기록 에이전트 실행 ---")
    meal_plan = state.get("meal_plan")
    recipes_from_agent = state.get("recipes", []) # RecipeAgent에서 생성된 전체 레시피 목록

    if not meal_plan:
        print("기록할 식단 계획이 없습니다.")
        return {}

    db_manager = DatabaseManager()
    try:
        today_str = date.today().strftime("%Y-%m-%d")
        logged_count = 0

        # meal_plan의 각 식사 (아침, 점심, 저녁)에 대해 처리
        for meal_time_attr in ["breakfast", "lunch", "dinner"]:
            recipe_title = getattr(meal_plan, meal_time_attr, None)
            if recipe_title:
                # 해당 제목의 레시피를 recipes_from_agent에서 찾기
                found_recipe = next((r for r in recipes_from_agent if r.get("title") == recipe_title), None)
                if found_recipe:
                    db_manager.add_meal_to_history(
                        meal_date=today_str,
                        recipe_id=found_recipe.get("id"),
                        recipe_title=found_recipe.get("title"),
                        ingredients=found_recipe.get("ingredients")
                    )
                    logged_count += 1
                else:
                    print(f"경고: '{recipe_title}' 레시피를 찾을 수 없어 기록하지 못했습니다.")
        
        if logged_count > 0:
            response_message = f"총 {logged_count}개의 식단이 기록되었습니다. 추천된 레시피는 다음과 같습니다:\n"
            for recipe in recipes_from_agent:
                response_message += f"- {recipe.get('title')}\n"
            print(response_message)
            return {"response": response_message, "recipes": recipes_from_agent} # recipes도 함께 반환
        else:
            response_message = "기록할 식단이 없습니다. 레시피를 찾지 못했거나 식단 계획이 생성되지 않았습니다."
            print(response_message)
            return {"response": response_message}

    except Exception as e:
        print(f"식단 기록 중 오류 발생: {e}")
        return {"response": f"식단 기록 중 오류 발생: {e}"}
    finally:
        db_manager.close()


# --- 새로운 노드 함수들 (챗봇 관련) ---
def add_inventory_item_node(state: AgentState) -> dict:
    print("--- 재고 추가 에이전트 실행 ---")
    intent_data = state["intent"]
    item_name = intent_data.get("item_name")
    quantity = intent_data.get("quantity")

    if not item_name or not quantity:
        return {"response": "재고 추가에 필요한 정보가 부족합니다."}

    db_manager = DatabaseManager()
    try:
        # LLM을 통해 유통기한 추정 (InventoryAgent 로직 재사용)
        inventory_agent_instance = InventoryAgent() # 임시 인스턴스 생성
        shelf_life_data = inventory_agent_instance.get_shelf_life_from_llm([item_name])
        shelf_life_days = shelf_life_data.get(item_name, 7) # 기본값 7일
        
        today = datetime.now()
        expiry_date = today + timedelta(days=shelf_life_days)

        db_manager.upsert_inventory_item(
            item_name=item_name,
            quantity=quantity,
            added_date=today.strftime("%Y-%m-%d"),
            expiry_date=expiry_date.strftime("%Y-%m-%d")
        )
        return {"response": f"{item_name} {quantity}를 재고에 추가했습니다. 유통기한: {expiry_date.strftime('%Y-%m-%d')}"}
    except Exception as e:
        return {"response": f"재고 추가 중 오류 발생: {e}"}
    finally:
        db_manager.close()

def update_preferences_node(state: AgentState) -> dict:
    print("--- 사용자 선호도 업데이트 에이전트 실행 ---")
    intent_data = state["intent"]
    allergies = intent_data.get("allergies")
    dislikes = intent_data.get("dislikes")
    dietary_goals = intent_data.get("dietary_goals")

    db_manager = DatabaseManager()
    try:
        db_manager.update_user_preferences(
            user_id="default_user", # 현재는 default_user 사용
            allergies=allergies, # None이면 업데이트 안함
            preferences={"dislikes": dislikes} if dislikes else None, # None이면 업데이트 안함
            dietary_goals=dietary_goals # None이면 업데이트 안함
        )
        return {"response": "사용자 선호도를 업데이트했습니다."}
    except Exception as e:
        return {"response": f"선호도 업데이트 중 오류 발생: {e}"}
    finally:
        db_manager.close()

def get_inventory_node(state: AgentState) -> dict:
    print("--- 재고 조회 에이전트 실행 ---")
    db_manager = DatabaseManager()
    try:
        inventory = db_manager.get_inventory()
        if inventory:
            response_str = "현재 재고 목록입니다:\n"
            for item, details in inventory.items():
                response_str += f"- {item}: {details['quantity']} (유통기한: {details['expiry_date']})\n"
            return {"response": response_str}
        else:
            return {"response": "현재 재고가 비어있습니다."}
    except Exception as e:
        return {"response": f"재고 조회 중 오류 발생: {e}"}
    finally:
        db_manager.close()

def general_chat_response_node(state: AgentState) -> dict:
    print("--- 일반 채팅 응답 노드 실행 ---")
    intent_data = state.get("intent", {})
    response_message = intent_data.get("response", "무슨 말씀이신지 잘 모르겠습니다.")
    return {"response": response_message}

# --- 그래프 생성 및 연결 ---
workflow = StateGraph(AgentState)

# 노드 추가
workflow.add_node("chat_node", run_chat_agent)
workflow.add_node("vision_node", run_vision_agent)
workflow.add_node("inventory_node", run_inventory_agent)
workflow.add_node("recipe_node", run_recipe_agent)
workflow.add_node("planner_node", run_planner_agent)
workflow.add_node("log_meal_node", log_meal_history)
workflow.add_node("add_inventory_node", add_inventory_item_node)
workflow.add_node("update_preferences_node", update_preferences_node)
workflow.add_node("get_inventory_node", get_inventory_node)
workflow.add_node("general_chat_node", general_chat_response_node)

# 시작점 설정
workflow.set_entry_point("chat_node")

# 조건부 엣지 추가
workflow.add_conditional_edges(
    "chat_node",
    lambda state: state["intent"]["intent"],
    {
        "get_recipes": "recipe_node",
        "get_inventory": "get_inventory_node",
        "add_inventory": "add_inventory_node",
        "update_preferences": "update_preferences_node",
        "general_chat": "general_chat_node",
    },
)

# 엣지 연결
workflow.add_edge("vision_node", "inventory_node") # 이미지 분석 -> 재고 업데이트 (기존 워크플로우)
workflow.add_edge("inventory_node", "recipe_node") # 재고 업데이트 -> 레시피 추천 (기존 워크플로우)

workflow.add_edge("recipe_node", "planner_node")
workflow.add_edge("planner_node", "log_meal_node")
workflow.add_edge("log_meal_node", END)

workflow.add_edge("add_inventory_node", END) # 재고 추가는 바로 종료
workflow.add_edge("update_preferences_node", END) # 선호도 업데이트는 바로 종료
workflow.add_edge("get_inventory_node", END) # 재고 조회는 바로 종료
workflow.add_edge("general_chat_node", END) # 일반 채팅은 바로 종료

app = workflow.compile()
print("LangGraph 워크플로우가 [챗봇 기능]을 포함하여 완성되었습니다.")

# --- 이미지 분석 전용 워크플로우 --- #
image_workflow = StateGraph(AgentState)

image_workflow.add_node("vision_node", run_vision_agent)
image_workflow.add_node("inventory_node", run_inventory_agent)
image_workflow.add_node("recipe_node", run_recipe_agent)
image_workflow.add_node("planner_node", run_planner_agent)
image_workflow.add_node("log_meal_node", log_meal_history)

# --- 이미지 분석 전용 워크플로우 --- #
image_workflow = StateGraph(AgentState)

image_workflow.add_node("vision_node", run_vision_agent)
image_workflow.add_node("inventory_node", run_inventory_agent)
image_workflow.add_node("recipe_node", run_recipe_agent)
image_workflow.add_node("planner_node", run_planner_agent)
image_workflow.add_node("log_meal_node", log_meal_history)

image_workflow.set_entry_point("vision_node")
image_workflow.add_edge("vision_node", "inventory_node")
image_workflow.add_edge("inventory_node", "recipe_node")
image_workflow.add_edge("recipe_node", "planner_node")
image_workflow.add_edge("planner_node", "log_meal_node")
image_workflow.add_edge("log_meal_node", END)

image_app = image_workflow.compile()
print("LangGraph 워크플로우가 [이미지 분석 기능]을 포함하여 완성되었습니다.")
