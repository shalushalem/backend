import traceback
from typing import Dict, Any, Tuple

# =========================
# ENGINE IMPORTS
# =========================
from brain.engines.fitness_engine import fitness_engine
from brain.engines.meal_planner_engine import meal_planner_engine
from brain.engines.organize_engine import organize_engine
from brain.engines.plan_engine import plan_engine

from brain.shopping.shopping_system import shopping_system
from brain.engines.calendar_runtime import run_calendar_runtime
from brain.engines.packing_engine import packing_engine
from brain.engines.style_builder import style_engine

# =========================
# CORE SYSTEMS
# =========================
from brain.context.context_engine import context_engine
from brain.personalization.style_dna_engine import style_dna_engine
from brain.response.response_assembler import response_assembler


class AhviOrchestrator:

    # =========================
    # MAIN ENTRYPOINT
    # =========================
    def run(self, text: str, user_id: str = None, context: Dict = None) -> Dict[str, Any]:
        """
        Main brain entry
        """

        context = context or {}

        try:
            # =========================
            # STEP 0 — CONTEXT ENRICHMENT 🧠
            # =========================
            enriched_context = context_engine.build_context({
                "text": text,
                "user_profile": context.get("user_profile"),
                "signals": context.get("signals"),
                "wardrobe": context.get("wardrobe", [])
            })

            # 🔥 STYLE DNA
            style_dna = style_dna_engine.build({
                "user_profile": context.get("user_profile"),
                "signals": context.get("signals"),
                "wardrobe": context.get("wardrobe", [])
            })

            enriched_context["style_dna"] = style_dna

            # =========================
            # STEP 1 — INTENT DETECTION
            # =========================
            mode, domain = self._detect_mode_domain(text)

            # =========================
            # STEP 2 — ENGINE EXECUTION
            # =========================
            engine_output = self._run_engine(
                mode,
                domain,
                text,
                enriched_context,
                user_id
            )

            # =========================
            # STEP 3 — NORMALIZATION
            # =========================
            engine_output = self._normalize_output(engine_output)

            # =========================
            # STEP 4 — RESPONSE BUILD
            # =========================
            final_text = response_assembler.assemble(
                engine_output,
                {
                    "mode": mode,
                    "domain": domain,
                    "user_profile": enriched_context.get("user_profile"),
                    "signals": enriched_context.get("signals"),
                }
            )

            # =========================
            # STEP 5 — FINAL RESPONSE
            # =========================
            return {
                "success": True,
                "meta": {
                    "mode": mode,
                    "domain": domain
                },
                "data": {
                    "message": final_text,
                    "raw": engine_output
                }
            }

        except Exception:
            print("❌ Orchestrator error:\n", traceback.format_exc())

            return {
                "success": False,
                "error": "Something went wrong"
            }

    # =========================
    # INTENT DETECTION (IMPROVED)
    # =========================
    def _detect_mode_domain(self, text: str) -> Tuple[str, str]:
        t = text.lower()

        # 🔥 SHOPPING
        if any(k in t for k in ["buy", "price", "worth", "compare", "recommend", "suggest"]):
            return "style", "shopping"

        # 🔥 STYLE
        if any(k in t for k in ["wear", "outfit", "style", "match", "look"]):
            return "style", "styling"

        # 🔥 PACKING / TRAVEL
        if any(k in t for k in ["pack", "packing", "trip", "travel"]):
            return "plan", "packing"

        # 🔥 CALENDAR
        if any(k in t for k in ["meeting", "event", "appointment", "reminder", "schedule"]):
            return "plan", "calendar"

        # 🔥 FITNESS
        if any(k in t for k in ["workout", "fitness", "exercise", "gym"]):
            return "health", "fitness"

        # 🔥 MEALS
        if any(k in t for k in ["diet", "meal", "food", "eat", "calories"]):
            return "health", "meals"

        # 🔥 ORGANIZE
        if any(k in t for k in ["organize", "tasks", "todo", "groceries", "list"]):
            return "organize", "tasks"

        # 🔥 PLANNING
        if any(k in t for k in ["plan", "routine", "schedule my day"]):
            return "plan", "general"

        return "general", "general"

    # =========================
    # ENGINE ROUTER (SCALABLE)
    # =========================
    def _run_engine(self, mode, domain, text, context, user_id):

        ENGINE_MAP = {

            # 🔥 SHOPPING
            ("style", "shopping"): lambda t, c, u: shopping_system.run(
                t,
                {
                    "signals": c.get("signals"),
                    "wardrobe": c.get("wardrobe", []),
                    "product_candidate": c.get("product_candidate"),
                    "style_dna": c.get("style_dna")
                }
            ),

            # 🔥 STYLING
            ("style", "styling"): lambda t, c, u: style_engine.build_outfit({
                "slots": c.get("slots", {}),
                "wardrobe": c.get("wardrobe", []),
                "style_dna": c.get("style_dna")
            }),

            # 🔥 PACKING
            ("plan", "packing"): lambda t, c, u: packing_engine.build_packing_list({
                "days": c.get("days", 3),
                "purpose": c.get("purpose"),
                "gender": c.get("gender", "women")
            }),

            # 🔥 CALENDAR
            ("plan", "calendar"): lambda t, c, u: run_calendar_runtime({
                "title": t
            }),

            # 🔥 FITNESS
            ("health", "fitness"): lambda t, c, u: fitness_engine.run(t, c),

            # 🔥 MEALS
            ("health", "meals"): lambda t, c, u: meal_planner_engine.run(t, c),

            # 🔥 ORGANIZE
            ("organize", "tasks"): lambda t, c, u: organize_engine.run(t, c),

            # 🔥 GENERAL PLANNING
            ("plan", "general"): lambda t, c, u: plan_engine.run(t, c),
        }

        handler = ENGINE_MAP.get((mode, domain))

        if handler:
            return handler(text, context, user_id)

        return {
            "message": "Tell me what you need — I’ll help you figure it out."
        }

    # =========================
    # OUTPUT NORMALIZER
    # =========================
    def _normalize_output(self, output: Dict[str, Any]) -> Dict[str, Any]:
        """
        Ensures every engine returns same structure
        """

        if not isinstance(output, dict):
            return {"message": str(output), "data": {}, "cards": [], "actions": []}

        return {
            "message": output.get("message", ""),
            "data": output.get("data", {}),
            "cards": output.get("cards", []),
            "actions": output.get("actions", [])
        }


# ✅ SINGLETON
ahvi_orchestrator = AhviOrchestrator()