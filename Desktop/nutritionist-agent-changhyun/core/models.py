from pydantic import BaseModel
from typing import List, Optional, Dict, Any

class Ingredient(BaseModel):
    name: str
    quantity: float
    unit: str

class Recipe(BaseModel):
    name: str
    ingredients: List[Ingredient]
    instructions: str
    difficulty: str
    cooking_time: str

class DailyMealPlan(BaseModel):
    breakfast: Optional[str] = None
    lunch: Optional[str] = None
    dinner: Optional[str] = None

class ShoppingItem(BaseModel):
    name: str
    quantity: str
    url: Optional[str] = None

class ShoppingList(BaseModel):
    items: List[ShoppingItem]

class NutritionAnalysisReport(BaseModel):
    total_calories: float
    total_protein: float
    total_carbs: float
    total_fat: float
    feedback: str
    analysis_details: Optional[Dict[str, Any]] = None
