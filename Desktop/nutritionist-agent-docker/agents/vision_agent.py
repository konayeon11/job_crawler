
import os
import base64
import json
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage
from dotenv import load_dotenv
from PIL import Image # 테스트용 이미지 생성에 필요

# .env 파일에서 환경 변수를 로드합니다.
# 프로젝트 최상단(.gitignore 파일 있는 곳)에 .env 파일을 만들고 아래와 같이 키를 추가하세요.
# OPENAI_API_KEY="sk-..."
load_dotenv()

class VisionAgent:
    """
    이미지(냉장고, 영수증)를 분석하여 식재료 목록을 JSON 형태로 추출하는 에이전트.
    """
    def __init__(self):
        """
        에이전트 초기화 시, 사용할 LLM 모델을 설정합니다.
        """
        # API 키가 로드되었는지 확인
        if not os.getenv("OPENAI_API_KEY"):
            raise ValueError("OPENAI_API_KEY 환경변수가 설정되지 않았습니다.")
        
        # 최신 모델인 gpt-4o를 사용하여 이미지 분석 성능을 극대화합니다.
        self.llm = ChatOpenAI(model="gpt-4o", temperature=0.1)

    def analyze_image(self, image_base64: str) -> list[dict]:
        """
        Base64로 인코딩된 이미지 문자열을 입력받아, 분석된 식재료 리스트를 반환합니다.

        Args:
            image_base64 (str): Base64로 인코딩된 이미지.

        Returns:
            list[dict]: 각 식재료의 이름과 수량을 담은 딕셔너리 리스트.
                        (예: [{"item_name": "계란", "quantity": "10개"}])
        """
        if not image_base64:
            print("Vision Agent: 입력된 이미지가 없습니다.")
            return []

        # LLM에게 전달할 프롬프트입니다. 역할을 명확히 하고 출력 형식을 엄격하게 지정합니다.
        prompt = """
        당신은 이미지를 보고 식재료 목록을 만드는 전문가입니다.
        주어진 이미지 속 식재료를 분석하고, 아래의 **절대적인 규칙**에 따라 JSON 리스트로 반환하세요.

        **[절대 규칙]**
        1.  **언어 규칙**: `item_name`은 **예외 없이 100% 한국어**로만 작성해야 합니다. 이미지에 영어가 쓰여 있어도 반드시 한국어로 번역하세요. (예: 'TORTILLAS' -> '토르티야', 'Chipotle Sauce' -> '치폴레 소스')
        2.  **중복 금지 규칙**: 의미가 같은 항목은 하나의 대표 이름으로 통일하세요. (예: 'Cheese'와 '치즈'가 보이면 '치즈' 하나로만 기록)
        3.  **정확성 규칙**: 이미지에 없는 것은 절대 지어내지 마세요. 특히 '대파', '우유', '계란'이 보이지 않으면 절대로 목록에 넣지 마세요.
        4.  **출력 형식 규칙**: 다른 설명 없이, `[{"item_name": "...", "quantity": "..."}, ...]` 형식의 JSON 리스트만 출력해야 합니다.
        """
        
        # LangChain의 HumanMessage 형식을 사용하여 텍스트와 이미지를 함께 전달합니다.
        messages = [
            HumanMessage(
                content=[
                    {"type": "text", "text": prompt},
                    {
                        "type": "image_url",
                        "image_url": {"url": f"data:image/jpeg;base64,{image_base64}"},
                    },
                ]
            )
        ]

        try:
            print("Vision Agent: 이미지 분석을 시작합니다...")
            response = self.llm.invoke(messages)
            
            # --- ✨ 수정된 핵심 부분 ✨ ---
            # LLM이 응답에 추가할 수 있는 markdown 코드 블록(```json ... ```)을 제거합니다.
            cleaned_response = response.content.strip().replace('```json', '').replace('```', '').strip()
            
            # 정리된 문자열을 Python 객체(리스트)로 변환합니다.
            result = json.loads(cleaned_response)
            print(f"Vision Agent: 분석 완료. {len(result)}개의 재료를 찾았습니다.")
            return result
        except json.JSONDecodeError:
            print("Vision Agent 오류: LLM이 유효한 JSON을 반환하지 않았습니다.")
            # 디버깅을 위해 LLM의 원본 응답을 출력합니다.
            print("LLM 원본 응답:", response.content)
            return []
        except Exception as e:
            print(f"Vision Agent에서 예상치 못한 오류가 발생했습니다: {e}")
            return []

# --- 이 파일을 직접 실행하여 단위 테스트를 수행하는 부분 ---
# (터미널에서 `python agents/vision_agent.py` 실행)
if __name__ == '__main__':
    print("Vision Agent 단위 테스트를 시작합니다...")
    
    # 1. 테스트할 이미지 파일 경로 설정 (프로젝트 구조에 맞게 수정)
    # 현재 폴더 구조(`NUTRITIONIST-AGENT-DEV`)에 맞춰 경로를 수정했습니다.
    image_path = "data/images/sample_fridge.jpg" 

    # 2. 이미지 파일 존재 여부 확인 및 생성
    if not os.path.exists(image_path):
        print(f"경고: 테스트 이미지 파일을 찾을 수 없습니다. ({image_path})")
        # 테스트용으로 이미지를 담을 폴더가 없으면 생성
        image_dir = os.path.dirname(image_path)
        if not os.path.exists(image_dir):
            os.makedirs(image_dir)
        # 빨간색 임시 이미지 생성
        Image.new('RGB', (100, 100), color = 'red').save(image_path)
        print(f"임시 테스트 이미지를 '{image_path}'에 생성했습니다. 정확한 테스트를 위해 실제 냉장고 사진으로 교체해주세요.")

    # 3. 이미지 파일을 Base64로 인코딩
    try:
        with open(image_path, "rb") as image_file:
            test_image_base64 = base64.b64encode(image_file.read()).decode('utf-8')
        print(f"'{image_path}' 이미지를 성공적으로 로드했습니다.")
    except Exception as e:
        print(f"이미지 파일 로드 중 오류 발생: {e}")
        test_image_base64 = ""

    # 4. 에이전트 실행 및 결과 확인
    if test_image_base64:
        vision_agent = VisionAgent()
        ingredients_list = vision_agent.analyze_image(test_image_base64)

        print("\n--- 최종 분석 결과 ---")
        if ingredients_list:
            import pprint
            pprint.pprint(ingredients_list)
            
            # 간단한 검증
            assert isinstance(ingredients_list, list)
            # 리스트가 비어있지 않은 경우에만 내부 검증
            if ingredients_list:
                assert isinstance(ingredients_list[0], dict)
                assert "item_name" in ingredients_list[0]
            print("\n테스트 성공: 결과가 유효한 형식입니다.")
        else:
            print("분석된 재료가 없거나 오류가 발생했습니다.")
            print("테스트 실패")

