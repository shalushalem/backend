# backend/brain/orchestrator/master_orchestrator.py

from brain.nlu.intent_router import nlu_router
from brain.context.context_engine import context_engine
from brain.personalization.style_dna_engine import style_dna_engine

from brain.engines.style_builder import style_engine
from brain.engines.recipe_rewriter import recipe_rewriter


class MasterOrchestrator:

    def run(self, user_input: str, user_profile: dict, wardrobe: list, memory: str):

        # =========================
        # 1. INTENT DETECTION
        # =========================
        intent_data = nlu_router.classify_intent(user_input)

        intent = intent_data.get("intent")
        slots = intent_data.get("slots", {})

        # =========================
        # 2. ROUTING DECISION
        # =========================
        if intent == "style":
            return self.handle_style(intent_data, user_profile, wardrobe)

        elif intent == "food":
            return self.handle_food(intent_data, user_profile)

        elif intent == "event":
            return self.handle_event(intent_data)

        else:
            return {
                "type": "chat",
                "data": "I'm not fully sure yet — can you clarify?"
            }

    # =========================
    # 👕 STYLE FLOW
    # =========================
    def handle_style(self, intent_data, user_profile, wardrobe):

        context = context_engine.build_context(
            user_id="temp_user",
            intent_data=intent_data,
            wardrobe=wardrobe,
            user_profile=user_profile,
            history=[],
            vision={}
        )

        context = style_dna_engine.enrich_context(context)

        outfit_data = style_engine.build_outfit(context)

        return {
            "type": "style",
            "data": outfit_data
        }

    # =========================
    # 🍲 FOOD FLOW
    # =========================
    def handle_food(self, intent_data, user_profile):

        # Example base recipe (later → DB)
        base_recipe = {
            "title": "Upma",
            "ingredients": ["rava", "onion", "salt", "chilli"],
            "steps": ["Roast rava", "Cook with onion and spices"]
        }

        preferences = {
            "appliance": intent_data.get("slots", {}).get("appliance", "tawa"),
            "spice_tolerance": user_profile.get("spice_level", "medium"),
            "toggles": user_profile.get("dietary_preferences", {})
        }

        new_recipe = recipe_rewriter.rewrite(base_recipe, preferences)

        return {
            "type": "food",
            "data": new_recipe
        }

    # =========================
    # 🎉 EVENT FLOW
    # =========================
    def handle_event(self, intent_data):

        event_type = intent_data.get("slots", {}).get("occasion", "general")

        return {
            "type": "event",
            "data": {
                "event_type": event_type,
                "message": f"Planning for {event_type}"
            }
        }


# Singleton
master_orchestrator = MasterOrchestrator()