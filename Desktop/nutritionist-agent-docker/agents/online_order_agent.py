import os
import json

class OnlineOrderParserAgent:
    """
    JSON 형식의 온라인 주문 내역 파일을 읽어, 
    구매한 상품 목록을 추출하는 에이전트.
    """
    def __init__(self):
        """
        에이전트를 초기화합니다. (현재는 특별한 설정이 필요 없습니다.)
        """
        pass

    def parse_order_from_file(self, file_path: str) -> list[dict]:
        """
        주어진 파일 경로에서 JSON 주문 내역을 읽고, 상품 리스트를 반환합니다.

        Args:
            file_path (str): 읽어올 JSON 파일의 경로.

        Returns:
            list[dict]: 각 상품의 이름과 수량을 담은 딕셔너리 리스트.
                        (예: [{"item_name": "계란", "quantity": "1판"}])
                        오류 발생 시 빈 리스트를 반환합니다.
        """
        print(f"Online Order Parser Agent: '{file_path}' 파일 분석을 시작합니다...")

        # 파일이 존재하는지 먼저 확인합니다.
        if not os.path.exists(file_path):
            print(f"오류: 파일을 찾을 수 없습니다. ({file_path})")
            return []

        try:
            # 'with' 구문을 사용하여 파일을 안전하게 엽니다.
            with open(file_path, 'r', encoding='utf-8') as f:
                order_data = json.load(f)
            
            # 'items' 키가 있는지 확인하고, 있으면 해당 리스트를 가져옵니다.
            items_list = order_data.get("items", [])
            
            if not items_list:
                print("경고: 주문 내역 파일에 'items' 목록이 비어있거나 없습니다.")
                return []
            
            print(f"분석 완료. {len(items_list)}개의 상품을 찾았습니다.")
            return items_list

        except json.JSONDecodeError:
            print(f"오류: '{file_path}' 파일이 올바른 JSON 형식이 아닙니다.")
            return []
        except Exception as e:
            print(f"파일 처리 중 예상치 못한 오류가 발생했습니다: {e}")
            return []

# --- 이 파일을 직접 실행하여 단위 테스트를 수행하는 부분 ---
# (터미널에서 `python agents/online_order_agent.py` 실행)
if __name__ == '__main__':
    print("Online Order Parser Agent 단위 테스트를 시작합니다...")
    
    # 1. 분석할 샘플 데이터 파일 경로를 지정합니다.
    sample_file_path = "data/sample_online_order.json"

    # 2. (선택) 만약 샘플 파일이 없다면, 테스트를 위해 자동으로 생성합니다.
    if not os.path.exists(sample_file_path):
        print(f"경고: 샘플 파일이 없어 '{sample_file_path}'에 새로 생성합니다.")
        if not os.path.exists("data"):
            os.makedirs("data")
        
        sample_data = {
          "order_id": "ORD-TEST-001",
          "items": [
            {"item_name": "테스트용 계란", "quantity": "10개"},
            {"item_name": "테스트용 우유", "quantity": "1개"}
          ]
        }
        with open(sample_file_path, 'w', encoding='utf-8') as f:
            json.dump(sample_data, f, ensure_ascii=False, indent=2)

    # 3. 에이전트 인스턴스를 생성하고, 파일 분석 메서드를 실행합니다.
    order_parser_agent = OnlineOrderParserAgent()
    purchased_items = order_parser_agent.parse_order_from_file(sample_file_path)

    # 4. 최종 결과를 확인합니다.
    print("\n--- 최종 분석 결과 ---")
    if purchased_items:
        import pprint
        pprint.pprint(purchased_items)
        
        # 간단한 형식 검증
        assert isinstance(purchased_items, list)
        assert "item_name" in purchased_items[0]
        print("\n테스트 성공: 결과가 유효한 형식입니다.")
    else:
        print("분석된 상품이 없거나 오류가 발생했습니다.")
        print("테스트 실패")