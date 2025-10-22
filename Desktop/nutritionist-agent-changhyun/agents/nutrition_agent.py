"""
NutritionAgent: 사용자가 섭취한 음식을 바탕으로 영양 성분을 분석하고 건강 리포트를 생성합니다.
"""
import os
import json
from typing import Dict, Any
from openai import OpenAI
from dotenv import load_dotenv

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



    # LLM 프롬프트 구성

    system_prompt = """

    당신은 전문 영양사입니다. 사용자가 제공한 식단표 또는 음식 기록을 바탕으로 영양 성분을 분석하고,

    건강 목표에 따른 피드백을 포함한 영양 분석 리포트를 JSON 형식으로 생성해야 합니다.

    JSON 형식은 다음과 같습니다:

    {

      "total_calories": float,

      "total_protein": float,

      "total_carbs": float,

      "total_fat": float,

      "feedback": "string",

      "analysis_details": {"key": "value"} (선택 사항)

    }

    'feedback'은 사용자의 건강 목표(예: 체중 감량, 근육 증가 등)를 고려하여 구체적이고 실용적인 조언을 포함해야 합니다.

    'analysis_details'는 필요에 따라 추가적인 상세 분석 정보를 포함할 수 있습니다.

    """



    user_prompt = f"다음 식단표 또는 음식 기록을 분석하여 영양 분석 리포트를 생성해주세요:\n{json.dumps(meal_plan_or_food_log, ensure_ascii=False, indent=2)}"



    try:

        response = client.chat.completions.create(

            model="gpt-4o", # gpt-4o is better for JSON output

            messages=[

                {"role": "system", "content": system_prompt},

                {"role": "user", "content": user_prompt}

            ],

            temperature=0.7,

            max_tokens=1000,

            response_format={"type": "json_object"} # Ensure JSON output

        )

        

        llm_output = response.choices[0].message.content.strip()



        report_data = json.loads(llm_output)

        return NutritionAnalysisReport(**report_data)



    except json.JSONDecodeError as e:

        print(f"LLM 응답 JSON 파싱 오류: {e}")

        print(f"LLM Raw Output: {llm_output}")

        raise ValueError("영양 분석 리포트 생성 실패: LLM 응답이 유효한 JSON 형식이 아닙니다.") from e

    except Exception as e:

        print(f"OpenAI API 호출 중 오류 발생: {e}")

        raise ValueError("영양 분석 리포트 생성 실패: OpenAI API 호출 오류") from e



# 기존 estimate_nutrition 함수는 그대로 유지 (혹시 다른 곳에서 사용될 수 있으므로)

def estimate_nutrition(recipe: Dict[str, Any]) -> Dict[str, float]:

    """

    Input: recipe payload (title/ingredients/amounts)

    Output: {"kcal": float, "protein": float, "carbs": float, "fat": float}

    """

    raise NotImplementedError