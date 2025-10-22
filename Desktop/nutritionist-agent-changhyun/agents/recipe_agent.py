"""
RecipeAgent: 재고/제약조건 → 레시피 후보 (인터페이스만)
"""
from typing import List, Dict, Any

def suggest_recipes(ingredients: List[str], constraints: Dict[str, Any]) -> List[Dict[str, Any]]:
    """
    Input:
      ingredients: ["egg","spinach",...]
      constraints: {"diet": "keto"|"vegan"|None, "time_min": int, ...}
    Output:
      [{"title": str, "ingredients": List[str], "steps": List[str]}, ...]
    """
    raise NotImplementedError
