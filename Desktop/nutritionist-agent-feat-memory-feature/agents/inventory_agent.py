import os
import json
from datetime import datetime, timedelta
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage
from dotenv import load_dotenv

from core.database import DatabaseManager

# .env 파일에서 환경 변수를 로드합니다.
load_dotenv()

class InventoryAgent:
    """
    LLM을 사용하여 식재료의 유통기한을 동적으로 추정하고 데이터베이스를 통해 재고를 관리하는 에이전트.
    """
    def __init__(self):
        if not os.getenv("OPENAI_API_KEY"):
            raise ValueError("OPENAI_API_KEY 환경변수가 설정되지 않았습니다.")
        self.llm = ChatOpenAI(model="gpt-4o", temperature=0)
        self.db_manager = DatabaseManager()

    def get_shelf_life_from_llm(self, item_names: list[str]) -> dict:
        """
        LLM에게 식재료 리스트의 평균 유통기한(일)을 물어보고 JSON으로 받습니다.
        """
        if not item_names:
            return {}

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
        새로운 식재료로 재고를 업데이트하고, LLM을 통해 유통기한을 추정하여 DB에 기록합니다.
        기존 재고는 유지되며, 새로운 아이템이 추가되거나 수량이 변경됩니다.
        """
        print(f"Inventory Agent: 재고 업데이트 및 LLM 유통기한 추정을 시작합니다. (신규/업데이트 항목: {len(new_items)}개)")
        
        item_names = [item.get("item_name") for item in new_items if item.get("item_name")]
        
        shelf_life_data = self.get_shelf_life_from_llm(item_names)
        print(f"LLM이 추정한 유통기한 정보: {shelf_life_data}")

        today = datetime.now()
        DEFAULT_SHELF_LIFE = 7

        for item in new_items:
            item_name = item.get("item_name")
            if not item_name:
                continue
            
            shelf_life_days = shelf_life_data.get(item_name, DEFAULT_SHELF_LIFE)
            expiry_date = today + timedelta(days=shelf_life_days)
            
            self.db_manager.upsert_inventory_item(
                item_name=item_name,
                quantity=item.get("quantity"),
                added_date=today.strftime("%Y-%m-%d"),
                expiry_date=expiry_date.strftime("%Y-%m-%d")
            )

        print("Inventory Agent: 데이터베이스 재고 업데이트를 완료했습니다.")
        
        # DB에서 최종 재고를 다시 불러와 반환
        updated_inventory = self.db_manager.get_inventory()
        return updated_inventory

# --- 단위 테스트 부분 (수정됨) ---
if __name__ == '__main__':
    print("Inventory Agent 단위 테스트를 시작합니다...")
    inventory_agent = InventoryAgent()
    sample_new_items = [{"item_name": "아보카도", "quantity": "3개"}, {"item_name": "토르티야", "quantity": "1팩"}]
    
    print("\n--- 1차 업데이트: 아보카도와 토르티야 추가 ---")
    updated_inventory = inventory_agent.update_inventory(sample_new_items)
    import pprint
    pprint.pprint(updated_inventory)
    assert "아보카도" in updated_inventory
    assert updated_inventory["아보카도"]["quantity"] == "3개"

    print("\n--- 2차 업데이트: 아보카도 수량 변경 및 할라피뇨 추가 ---")
    second_update_items = [{"item_name": "아보카도", "quantity": "1개"}, {"item_name": "할라피뇨", "quantity": "5개"}]
    final_inventory = inventory_agent.update_inventory(second_update_items)
    pprint.pprint(final_inventory)
    
    assert final_inventory["아보카도"]["quantity"] == "1개"
    assert "할라피뇨" in final_inventory
    assert "토르티야" in final_inventory # 기존 항목 유지 확인

    print("\n테스트 성공: 데이터베이스 기반 재고 추가, 업데이트 및 유지가 성공적으로 확인되었습니다.")