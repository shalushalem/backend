import traceback
import uuid
from typing import Dict, Any, Tuple, Callable

# =========================
# ENGINE IMPORTS
# =========================
from brain.engines.fitness.fitness_engine import fitness_engine
from brain.engines.meals.meal_planner_engine import meal_planner_engine
from brain.engines.organize.organize_engine import organize_engine
from brain.engines.planning.plan_engine import plan_engine

try:
    from brain.shopping.shopping_system import shopping_system
except Exception:
    shopping_system = None
from brain.engines.calendar_runtime import run_calendar_runtime
from brain.engines.packing.packing_engine import packing_engine
from brain.engines.styling.style_builder import style_engine

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
        request_id = str(uuid.uuid4())

        try:
            # =========================
            # STEP 0 ? INTENT DETECTION
            # =========================
            mode, domain = self._detect_mode_domain(text)

            # =========================
            # STEP 1 ? CONTEXT ENRICHMENT ??
            # =========================
            intent_data = {"intent": domain, "slots": {}, "confidence": 1.0}
            enriched_context = context_engine.build_context(
                user_id or "anonymous",
                intent_data,
                wardrobe=context.get("wardrobe", []),
                user_profile=context.get("user_profile"),
                history=context.get("history", []),
                vision=context.get("vision"),
            )

            # ?? STYLE DNA
            if hasattr(style_dna_engine, "build"):
                style_dna = style_dna_engine.build({
                    "user_profile": context.get("user_profile"),
                    "signals": context.get("signals"),
                    "wardrobe": context.get("wardrobe", [])
                })
                enriched_context["style_dna"] = style_dna
            elif hasattr(style_dna_engine, "enrich_context"):
                enriched_context = style_dna_engine.enrich_context(enriched_context)

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
                "request_id": request_id,
                "meta": {
                    "mode": mode,
                    "domain": domain
                },
                "message": final_text,
                "data": engine_output.get("data", {}),
                "cards": engine_output.get("cards", []),
                "actions": engine_output.get("actions", [])
            }

        except Exception:
            print("ERROR: Orchestrator error:\n", traceback.format_exc())

            return {
                "success": False,
                "request_id": request_id,
                "error": {
                    "code": "ORCHESTRATOR_ERROR",
                    "message": "Something went wrong",
                    "details": request_id
                }
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
    def _safe_engine_call(self, fn: Callable, text: str, context: Dict, user_id: str):
        """
        Call engines with backward-compatible signatures.
        """
        try:
            return fn(text, context, user_id)
        except TypeError:
            try:
                return fn(text, context)
            except TypeError:
                return fn(text)

    def _run_engine(self, mode, domain, text, context, user_id):

        ENGINE_MAP = {

            # 🔥 SHOPPING
            ("style", "shopping"): lambda t, c, u: (
                self._normalize_output(
                    shopping_system.run(
                        t,
                        {
                            "signals": c.get("signals"),
                            "wardrobe": c.get("wardrobe", []),
                            "product_candidate": c.get("product_candidate"),
                            "style_dna": c.get("style_dna"),
                            "user_id": u,
                        }
                    )
                )
                if shopping_system is not None
                else {
                    "message": "Shopping engine is unavailable right now.",
                    "data": {},
                    "cards": [],
                    "actions": []
                }
            ),

            # 🔥 STYLING
            ("style", "styling"): lambda t, c, u: self._normalize_output({
                "message": "",
                "data": style_engine.build_outfit({
                    "slots": c.get("slots", {}),
                    "wardrobe": c.get("wardrobe", []),
                    "style_dna": c.get("style_dna"),
                    "user_id": u,
                }),
                "cards": [],
                "actions": []
            }),

            # 🔥 PACKING
            ("plan", "packing"): lambda t, c, u: self._normalize_output({
                "message": "",
                "data": (
                    packing_engine.build_packing_list({
                        "days": c.get("days", 3),
                        "purpose": c.get("purpose"),
                        "gender": c.get("gender", "women"),
                        "user_id": u,
                    })
                    if hasattr(packing_engine, "build_packing_list")
                    else packing_engine.build_packing({
                        "days": c.get("days", 3),
                        "purpose": c.get("purpose"),
                        "gender": c.get("gender", "women"),
                        "user_id": u,
                    })
                ),
                "cards": [],
                "actions": []
            }),

            # 🔥 CALENDAR
            ("plan", "calendar"): lambda t, c, u: self._normalize_output({
                "message": "",
                "data": run_calendar_runtime({
                    "title": t,
                    "user_id": u
                }),
                "cards": [],
                "actions": []
            }),

            # 🔥 FITNESS
            ("health", "fitness"): lambda t, c, u: self._normalize_output(
                self._safe_engine_call(fitness_engine.run, t, c, u)
            ),

            # 🔥 MEALS
            ("health", "meals"): lambda t, c, u: self._normalize_output(
                self._safe_engine_call(meal_planner_engine.run, t, c, u)
            ),

            # 🔥 ORGANIZE
            ("organize", "tasks"): lambda t, c, u: self._normalize_output(
                self._safe_engine_call(organize_engine.run, t, c, u)
            ),

            # 🔥 GENERAL PLANNING
            ("plan", "general"): lambda t, c, u: self._normalize_output(
                self._safe_engine_call(plan_engine.run, t, c, u)
            ),
        }

        handler = ENGINE_MAP.get((mode, domain))

        if handler:
            return handler(text, context, user_id)

        return {
            "message": "Tell me what you need — I'll help you figure it out.",
            "data": {},
            "cards": [],
            "actions": []
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
