# backend/brain/nlu/intent_router.py
import re

class IntentRouter:
    def __init__(self):
        # Master dictionaries based on your old TS routing logic
        self.styling_keywords = ["wear", "outfit", "dress", "clothes", "style", "look", "matching", "fit"]
        
        # UPDATED TO MATCH YOUR FLUTTER APP'S OCCASIONS
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

    def normalize_text(self, text: str) -> str:
        return text.lower().strip()

    def extract_slots(self, text: str) -> dict:
        """Extracts specific details (slots) from the user's message."""
        text = self.normalize_text(text)
        slots = {
            "occasion": None,
            "weather": None,
            "vibe": None
        }

        # Find Occasion
        for occasion, keywords in self.occasions.items():
            if any(re.search(rf"\b{kw}\b", text) for kw in keywords):
                slots["occasion"] = occasion
                break

        # Find Weather
        for weather, keywords in self.weather_conditions.items():
            if any(re.search(rf"\b{kw}\b", text) for kw in keywords):
                slots["weather"] = weather
                break

        return slots

    def classify_intent(self, text: str) -> dict:
        """The main function: Determines what the user is asking for."""
        text = self.normalize_text(text)
        
        # 1. Check if it is a styling request
        is_styling = any(kw in text for kw in self.styling_keywords)
        slots = self.extract_slots(text)

        # If it has styling keywords OR an occasion/weather was detected, it's a styling intent
        if is_styling or slots["occasion"] or slots["weather"]:
            return {
                "status": "success",
                "intent": "styling",
                "slots": slots,
                "confidence": 0.9 if slots["occasion"] else 0.5
            }
            
        # 2. Fallback (Let LLaMA handle it)
        return {
            "status": "unrecognized",
            "intent": "unknown",
            "slots": slots,
            "confidence": 0.0
        }

# Instantiate for easy import in other files
nlu_router = IntentRouter()