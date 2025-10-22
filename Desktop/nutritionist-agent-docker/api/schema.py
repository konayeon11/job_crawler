from pydantic import BaseModel
from typing import List, Dict, Any, Optional

from core.models import DailyMealPlan # Add this import

class ImageAnalyzeRequest(BaseModel):
    image_b64: str  # base64

class InventoryChange(BaseModel):
    name: str
    delta: float
    unit: str

class RecipeSuggestRequest(BaseModel):
    ingredients: List[str]
    constraints: Optional[Dict[str, Any]] = None

class PlanProfile(BaseModel):
    age: int
    sex: str  # "M" or "F"
    goal: str # "cut"|"bulk"|"maintain"

class NutritionEstimateRequest(BaseModel):
    recipe: Dict[str, Any]

class NutritionAnalysisRequest(BaseModel):
    meal_plan: Optional[DailyMealPlan] = None
    food_log: Optional[List[Dict[str, Any]]] = None # e.g., [{"name": "apple", "quantity": 1, "unit": "ea"}]
