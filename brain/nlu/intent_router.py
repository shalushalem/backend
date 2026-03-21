# backend/brain/nlu/intent_router.py
import re

class IntentRouter:
    def __init__(self):
        # Styling keywords
        self.styling_keywords = ["wear", "outfit", "dress", "clothes", "style", "look", "matching", "fit"]
        
        self.occasions = {
            "party looks": ["party", "club", "clubbing", "night out", "birthday", "pub"],
            "office fits": ["office", "work", "interview", "formal", "meeting", "business", "corporate"],
            "vacation": ["vacation", "trip", "holiday", "beach", "travel", "tour", "goa"],
            "occasion": ["wedding", "marriage", "pelli", "shaadi", "reception", "sangeet", "festival", "event", "pooja", "occasion"],
            "everything else": ["casual", "daily", "normal", "everyday", "relaxing", "random", "outside", "grocery", "everything else"]
        }
        
        self.weather_conditions = {
            "rainy": ["rain", "rainy", "monsoon", "wet"],
            "summer": ["hot", "summer", "sunny", "warm", "sweat"],
            "winter": ["cold", "winter", "chill", "snow", "freezing"]
        }

        # 🚀 NEW: Holistic Life Coach Keywords
        self.life_keywords = {
            "meal_planning": ["meal", "diet", "food", "protein", "vegan", "breakfast", "lunch", "dinner", "recipe", "calories"],
            "life_goals": ["goal", "habit", "milestone", "focus", "resolution", "progress"],
            "health_wellness": ["workout", "gym", "skincare", "skin", "meds", "medicine", "pill", "fitness", "exercise"],
            "finance_home": ["bill", "coupon", "expense", "budget", "home", "utilities", "savings"]
        }

    def normalize_text(self, text: str) -> str:
        return text.lower().strip()

    def extract_slots(self, text: str) -> dict:
        """Extracts specific details (slots) from the user's message."""
        text = self.normalize_text(text)
        slots = {
            "occasion": None,
            "weather": None,
            "vibe": None,
            "life_category": None # Added new slot
        }

        for occasion, keywords in self.occasions.items():
            if any(re.search(rf"\b{kw}\b", text) for kw in keywords):
                slots["occasion"] = occasion
                break

        for weather, keywords in self.weather_conditions.items():
            if any(re.search(rf"\b{kw}\b", text) for kw in keywords):
                slots["weather"] = weather
                break
                
        # Find Life Category
        for category, keywords in self.life_keywords.items():
            if any(re.search(rf"\b{kw}\b", text) for kw in keywords):
                slots["life_category"] = category
                break

        return slots

    def classify_intent(self, text: str) -> dict:
        """The main function: Determines what the user is asking for."""
        text = self.normalize_text(text)
        slots = self.extract_slots(text)
        
        # 1. Check if it is a Life Coach request
        if slots["life_category"]:
            return {
                "status": "success",
                "intent": slots["life_category"],
                "slots": slots,
                "confidence": 0.95
            }
        
        # 2. Check if it is a styling request
        is_styling = any(kw in text for kw in self.styling_keywords)

        if is_styling or slots["occasion"] or slots["weather"]:
            return {
                "status": "success",
                "intent": "styling",
                "slots": slots,
                "confidence": 0.9 if slots["occasion"] else 0.5
            }
            
        # 3. Fallback (Let LLaMA handle it)
        return {
            "status": "unrecognized",
            "intent": "unknown",
            "slots": slots,
            "confidence": 0.0
        }

# Instantiate for easy import in other files
nlu_router = IntentRouter()