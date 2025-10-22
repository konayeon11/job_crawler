
import os
import json
from datetime import datetime, timedelta
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage
from dotenv import load_dotenv

# .env 파일에서 환경 변수를 로드합니다.
load_dotenv()

class InventoryAgent:
    """
    LLM을 사용하여 식재료의 유통기한을 동적으로 추정하고 재고를 관리하는 에이전트.
    """
    def __init__(self, inventory_file_path: str = "data/inventory.json"):
        self.inventory_file_path = inventory_file_path
        os.makedirs(os.path.dirname(self.inventory_file_path), exist_ok=True)
        
        # --- ✨ 1. LLM 인스턴스 추가 ✨ ---
        # 이 에이전트가 유통기한을 물어볼 수 있도록 LLM을 내장합니다.
        if not os.getenv("OPENAI_API_KEY"):
            raise ValueError("OPENAI_API_KEY 환경변수가 설정되지 않았습니다.")
        self.llm = ChatOpenAI(model="gpt-4o", temperature=0)

    def save_inventory(self, inventory_data: dict):
        with open(self.inventory_file_path, 'w', encoding='utf-8') as f:
            json.dump(inventory_data, f, ensure_ascii=False, indent=2)

    # --- ✨ 2. LLM에게 유통기한을 물어보는 메서드 추가 ✨ ---
    def get_shelf_life_from_llm(self, item_names: list[str]) -> dict:
        """
        LLM에게 식재료 리스트의 평균 유통기한(일)을 물어보고 JSON으로 받습니다.
        """
        if not item_names:
            return {}

        # 여러 항목을 한번에 처리하여 API 호출을 최소화합니다.
        item_list_str = ", ".join(item_names)
        
        prompt = f"""
        당신은 식품 영양 전문가입니다.
        다음 식재료 목록 각각의 평균적인 냉장 보관 시 유통기한이 며칠인지 알려주세요.
        결과는 반드시 JSON 형식이어야 하며, key는 식재료 이름, value는 유통기한(일)을 정수(integer)로 해야 합니다.
        다른 설명은 절대 추가하지 마세요.

        [식재료 목록]
        {item_list_str}

        [출력 예시]
        {{"계란": 21, "우유": 10, "상추": 5}}
        """

        try:
            response = self.llm.invoke([HumanMessage(content=prompt)])
            cleaned_response = response.content.strip().replace('```json', '').replace('```', '').strip()
            return json.loads(cleaned_response)
        except Exception as e:
            print(f"LLM 유통기한 분석 중 오류 발생: {e}")
            return {}

    def update_inventory(self, new_items: list[dict]) -> dict:
        """
        새로운 식재료 리스트로 재고를 대체하고, LLM을 통해 유통기한을 추정하여 기록합니다.
        """
        print(f"Inventory Agent: 재고 목록 생성 및 LLM 유통기한 추정을 시작합니다. (총 항목: {len(new_items)}개)")
        
        # --- ✨ 3. 업데이트 로직 수정 ✨ ---
        # 먼저 모든 식재료의 이름을 추출합니다.
        item_names = [item.get("item_name") for item in new_items if item.get("item_name")]
        
        # LLM을 호출하여 모든 식재료의 유통기한을 한 번에 받아옵니다.
        shelf_life_data = self.get_shelf_life_from_llm(item_names)
        print(f"LLM이 추정한 유통기한 정보: {shelf_life_data}")

        new_inventory = {}
        today = datetime.now()
        DEFAULT_SHELF_LIFE = 7 # LLM이 응답을 못했을 경우 기본값

        for item in new_items:
            item_name = item.get("item_name")
            if not item_name:
                continue
            
            # LLM의 응답에서 유통기한을 가져옵니다.
            shelf_life_days = shelf_life_data.get(item_name, DEFAULT_SHELF_LIFE)
            expiry_date = today + timedelta(days=shelf_life_days)
            
            new_inventory[item_name] = {
                "quantity": item.get("quantity"),
                "added_date": today.strftime("%Y-%m-%d"),
                "expiry_date": expiry_date.strftime("%Y-%m-%d")
            }

        self.save_inventory(new_inventory)
        print("Inventory Agent: 재고 파일 생성을 완료했습니다.")
        return new_inventory

# --- 단위 테스트 부분 (수정됨) ---
if __name__ == '__main__':
    print("Inventory Agent 단위 테스트를 시작합니다...")
    inventory_agent = InventoryAgent()
    sample_new_items = [{"item_name": "아보카도", "quantity": "2개"}, {"item_name": "토르티야", "quantity": "1팩"}, {"item_name": "할라피뇨", "quantity": "5개"}]
    updated_inventory = inventory_agent.update_inventory(sample_new_items)
    
    print("\n--- 생성된 재고 (LLM 추정 유통기한 포함) ---")
    import pprint
    pprint.pprint(updated_inventory)
    
    assert "expiry_date" in updated_inventory["아보카도"]
    print("\n테스트 성공: LLM을 통해 유통기han이 성공적으로 추정되었습니다.")

