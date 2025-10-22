<<<<<<< HEAD
"""
GraphBuilder: 에이전트 흐름 정의 (인터페이스만)
"""
from typing import Dict, Any

def build_graph(config: Dict[str, Any]) -> Any:
    """
    Input: {"nodes":[...], "edges":[...]} (TBD)
    Output: graph object / callable
    """
    raise NotImplementedError
=======
from langgraph.graph import StateGraph, END
from typing import TypedDict, List, Dict

# 에이전트 클래스들을 불러옵니다.
from agents.vision_agent import VisionAgent
from agents.inventory_agent import InventoryAgent

# 1. 상태 정의 (State Definition)
# 에이전트들이 서로 주고받을 데이터의 형식을 정의합니다.
# 이 '상태'가 바로 에이전트 간에 전달되는 '바통'입니다.
class AgentState(TypedDict):
    image_base64: str         # VisionAgent의 입력
    new_items: List[dict]     # VisionAgent의 출력 / InventoryAgent의 입력
    inventory: Dict           # InventoryAgent의 최종 출력

# 2. 에이전트 인스턴스 생성
# 각 전문가 에이전트를 실제로 사용할 수 있도록 준비시킵니다.
vision_agent = VisionAgent()
inventory_agent = InventoryAgent()

# 3. 그래프 노드 함수 정의
# LangGraph의 각 '노드'는 특정 작업을 수행하는 함수여야 합니다.
# 각 에이전트의 메서드를 이 함수들로 감싸줍니다.
def run_vision_agent(state: AgentState) -> dict:
    print("--- 1. Vision Agent 실행 ---")
    image_base64 = state["image_base64"]
    new_items = vision_agent.analyze_image(image_base64)
    # 다음 에이전트가 사용할 수 있도록 '상태'에 결과를 저장합니다.
    return {"new_items": new_items}

def run_inventory_agent(state: AgentState) -> dict:
    print("--- 2. Inventory Agent 실행 ---")
    new_items = state["new_items"]
    updated_inventory = inventory_agent.update_inventory(new_items)
    # 최종 결과를 '상태'에 저장합니다.
    return {"inventory": updated_inventory}


# 4. 그래프 생성 및 연결
# 이제 에이전트들의 작업 순서를 정의합니다.
workflow = StateGraph(AgentState)

# 노드(작업 단계) 추가
workflow.add_node("vision_node", run_vision_agent)
workflow.add_node("inventory_node", run_inventory_agent)

# 엣지(작업 순서) 설정
workflow.set_entry_point("vision_node") # 시작점은 'vision_node'
workflow.add_edge("vision_node", "inventory_node") # 'vision_node'가 끝나면 'inventory_node'로 이동
workflow.add_edge("inventory_node", END) # 'inventory_node'가 끝나면 전체 작업 종료

# 최종 실행 가능한 앱으로 컴파일
app = workflow.compile()

print("LangGraph 워크플로우가 성공적으로 컴파일되었습니다.")

# (선택) 이 파일을 직접 실행해서 테스트하는 코드
if __name__ == '__main__':
    import base64
    
    # 테스트 이미지
    image_path = "data/images/sample_fridge.jpg"
    with open(image_path, "rb") as image_file:
        test_image_base64 = base64.b64encode(image_file.read()).decode('utf-8')
        
    # 초기 상태를 지정하여 그래프 실행
    initial_state = {"image_base64": test_image_base64}
    final_state = app.invoke(initial_state)
    
    print("\n--- 전체 워크플로우 실행 완료 ---")
    import pprint
    pprint.pprint(final_state['inventory'])
>>>>>>> you
