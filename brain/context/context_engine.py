# backend/brain/context/context_engine.py

from typing import Dict, Any, List, Optional

class ContextEngine:
    def build_context(
        self,
        user_id: str,
        intent_data: Dict[str, Any],
        wardrobe: Optional[List[Dict[str, Any]]] = None,
        user_profile: Optional[Dict[str, Any]] = None,
        history: Optional[List[Dict[str, Any]]] = None,
        vision: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:

        slots = intent_data.get("slots", {})

        wardrobe = wardrobe or []
        user_profile = user_profile or {}
        history = history or []
        vision = vision or {}

        enriched_slots = self._enrich_slots(slots, history, vision)

        return {
            "user_id": user_id,
            "intent": intent_data.get("intent"),
            "confidence": intent_data.get("confidence", 0.0),

            "slots": enriched_slots,
            "user_profile": user_profile,
            "wardrobe": wardrobe,
            "history": history,
            "vision": vision,

            "meta": {
                "has_wardrobe": len(wardrobe) > 0,
                "has_profile": bool(user_profile),
                "has_history": len(history) > 0,
                "has_vision": bool(vision)
            }
        }

    def _enrich_slots(
        self,
        slots: Dict[str, Any],
        history: List[Dict[str, Any]],
        vision: Dict[str, Any]
    ) -> Dict[str, Any]:

        enriched = slots.copy()

        # Fill from history
        if history:
            prev = history[-1].get("slots", {})
            for key in ["occasion", "weather", "vibe"]:
                if not enriched.get(key) and prev.get(key):
                    enriched[key] = prev.get(key)

        # Fill from vision
        if vision and not enriched.get("vibe"):
            enriched["vibe"] = vision.get("detected_style")

        return enriched

context_engine = ContextEngine()