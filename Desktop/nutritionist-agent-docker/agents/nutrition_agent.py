import os
import json
from typing import Dict, Any
from openai import OpenAI
from dotenv import load_dotenv
from pydantic import ValidationError

# core/models.py에서 우리가 정의한 데이터 모델을 가져옵니다.
from core.models import NutritionAnalysisReport

# .env 파일에서 환경 변수 로드
load_dotenv()

def analyze_nutrition_report(meal_plan_or_food_log: Dict[str, Any]) -> NutritionAnalysisReport:
    """
    OpenAI API를 사용하여 식단표 또는 음식 기록을 바탕으로 영양 분석 리포트를 생성합니다.
    """
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise ValueError("OPENAI_API_KEY 환경 변수가 설정되지 않았습니다.")

    client = OpenAI(api_key=api_key)

    # LLM 프롬프트 구성 (모델이 따라야 할 규칙을 더 명확하게)
    system_prompt = """
    당신은 전문 영양사입니다. 사용자가 제공한 데이터를 바탕으로 영양 분석 리포트를 생성해야 합니다.
    결과는 반드시 아래의 JSON 스키마를 정확히 따라야 합니다.
    모든 숫자 필드는 float 타입이어야 하며, feedback은 string 타입이어야 합니다.
    필수 필드(total_calories, total_protein, total_carbs, total_fat, feedback)는 절대 누락해서는 안됩니다.

    {
      "total_calories": float,
      "total_protein": float,
      "total_carbs": float,
      "total_fat": float,
      "feedback": "string",
      "analysis_details": {"key": "value"}
    }
    """
    user_prompt = f"다음 식단/음식 기록을 분석하여 JSON 형식의 영양 리포트를 생성해주세요:\n{json.dumps(meal_plan_or_food_log, ensure_ascii=False, indent=2)}"

    try:
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            temperature=0.2, # 좀 더 일관된 결과를 위해 온도를 낮춤
            response_format={"type": "json_object"}
        )
        
        llm_output = response.choices[0].message.content.strip()
        report_data = json.loads(llm_output)

        # --- ✨ 핵심 수정 부분 ✨ ---
        # Pydantic 모델로 변환을 시도하고, 실패 시 상세한 오류를 출력합니다.
        try:
            validated_report = NutritionAnalysisReport(**report_data)
            return validated_report
        except ValidationError as e:
            print("--- Pydantic 유효성 검사 오류 ---")
            print("LLM이 생성한 JSON 데이터가 core/models.py의 형식과 맞지 않습니다.")
            print(f"오류 상세 내용:\n{e}")
            print("\nLLM이 반환한 원본 JSON:")
            print(report_data)
            raise ValueError("LLM 응답 데이터 형식 오류") from e

    except Exception as e:
        print(f"API 호출 또는 JSON 파싱 중 오류 발생: {e}")
        raise ValueError("영양 분석 리포트 생성 실패") from e

# 기존 estimate_nutrition 함수는 그대로 유지
def estimate_nutrition(recipe: Dict[str, Any]) -> Dict[str, float]:
    """
    Input: recipe payload (title/ingredients/amounts)
    Output: {"kcal": float, "protein": float, "carbs": float, "fat": float}
    """
    raise NotImplementedError

