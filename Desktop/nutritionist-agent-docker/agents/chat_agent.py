import os
import json
from typing import Dict, Any
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage
from dotenv import load_dotenv

load_dotenv()

class ChatAgent:
    def __init__(self):
        if not os.getenv("OPENAI_API_KEY"):
            raise ValueError("OPENAI_API_KEY 환경변수가 설정되지 않았습니다.")
        self.llm = ChatOpenAI(model="gpt-4o", temperature=0)

    def determine_intent(self, message: str) -> Dict[str, Any]:
        """
        사용자 메시지의 의도를 파악하고 필요한 엔티티를 추출합니다.
        """
        prompt = f"""
        당신은 사용자 메시지의 의도를 파악하고 필요한 정보를 JSON 형식으로 추출하는 AI 비서입니다.
        사용자의 메시지를 분석하여 다음 중 하나의 'intent'를 결정하세요:
        - 'get_recipes': "레시피 추천", "뭐 해먹지" 와 같은 명시적인 요청이나, "김", "사과, 바나나" 처럼 재료 이름만 입력되는 경우.
        - 'get_inventory': 현재 재고를 확인하려는 경우.
        - 'add_inventory': 재고를 추가하려는 경우.
        - 'update_preferences': 사용자 선호도를 업데이트하려는 경우.
        - 'general_chat': 위 범주에 속하지 않는 일반적인 대화.

        'get_recipes' 의도일 경우, 메시지에서 레시피 추천에 필요한 'ingredients' (리스트)를 추출하세요.
        'add_inventory' 의도일 경우, 메시지에서 추가할 'item_name' (문자열)과 'quantity' (문자열)를 추출하세요.
        'update_preferences' 의도일 경우, 'allergies' (리스트), 'dislikes' (리스트), 'dietary_goals' (문자열) 등을 추출하세요.

        응답은 반드시 JSON 형식이어야 하며, 'intent'와 추출된 엔티티를 포함해야 합니다.
        다른 설명은 절대 추가하지 마세요.

        [사용자 메시지]
        {message}

        [출력 예시]
        사용자 메시지: 닭고기랑 양파로 만들 수 있는 레시피 추천해줘
        출력: {{"intent": "get_recipes", "ingredients": ["닭고기", "양파"]}}

        사용자 메시지: 김
        출력: {{"intent": "get_recipes", "ingredients": ["김"]}}

        사용자 메시지: 내 냉장고에 뭐가 있는지 알려줘
        출력: {{"intent": "get_inventory"}}

        사용자 메시지: 사과 3개 냉장고에 넣어줘
        출력: {{"intent": "add_inventory", "item_name": "사과", "quantity": "3개"}}

        사용자 메시지: 나는 새우 알레르기가 있고 저탄수화물 식단을 원해
        출력: {{"intent": "update_preferences", "allergies": ["새우"], "dietary_goals": "저탄수화물"}}

        사용자 메시지: 안녕, 잘 지내?
        출력: {{"intent": "general_chat"}}
        """

        try:
            response = self.llm.invoke([HumanMessage(content=prompt)])
            cleaned_response = response.content.strip().replace('```json\n', '').replace('```', '').strip()
            return json.loads(cleaned_response)
        except Exception as e:
            print(f"LLM 의도 파악 중 오류 발생: {e}")
            return {"intent": "general_chat"}

if __name__ == '__main__':
    print("Chat Agent 단위 테스트를 시작합니다...")
    chat_agent = ChatAgent()

    # 테스트 케이스
    test_messages = [
        "닭고기랑 양파로 만들 수 있는 레시피 추천해줘",
        "내 냉장고에 뭐가 있는지 알려줘",
        "사과 3개 냉장고에 넣어줘",
        "나는 새우 알레르기가 있고 저탄수화물 식단을 원해",
        "안녕, 잘 지내?",
        "오늘 저녁 뭐 먹지?"
    ]

    for msg in test_messages:
        print(f"\n사용자 메시지: {msg}")
        intent_data = chat_agent.determine_intent(msg)
        print(f"파악된 의도: {intent_data}")
        assert "intent" in intent_data

    print("\nChat Agent 단위 테스트 완료.")
