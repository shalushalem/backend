import os
import json

# 🔥 NEW: Tone Engine
from brain.tone.tone_engine import tone_engine


class ResponseAssembler:

    def __init__(self):
        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

        # 🔥 Load Assembly Profiles
        profile_path = os.path.join(base_dir, "config", "assembly_profiles.json")

        try:
            with open(profile_path, "r", encoding="utf-8") as f:
                self.config = json.load(f).get("assembly_profiles", {})
        except Exception as e:
            print(f"WARN: Assembly profile load failed: {e}")
            self.config = {}

    # =========================
    # MAIN
    # =========================
    def assemble(self, engine_output: dict, intent: dict = None):
        """
        engine_output = output from engines
        intent = {
            mode,
            domain,
            user_profile,
            signals
        }
        """

        intent = intent or {}

        profile_name = self._select_profile(intent)
        profile = self.config.get("profiles", {}).get(profile_name, {})

        parts = []

        # 🔥 1. REACTION
        reaction = self._reaction()
        parts.append(reaction)

        # 🔥 2. PRIMARY INTELLIGENCE
        intelligence = (
            engine_output.get("message")
            or engine_output.get("context")
            or ""
        )

        if intelligence:
            parts.append(intelligence)

        # 🔥 3. OPTIONS MODE (for combos)
        if "combos" in engine_output:
            combos = engine_output["combos"][:3]  # enforce max 3
            parts.extend(combos)

        # 🔥 4. ACCESSORY / SUGGESTION
        if engine_output.get("accessories"):
            suggestion = f"Try adding {engine_output['accessories'][0]} to complete the look."
            parts.append(suggestion)

        # 🔥 5. CLOSER (max 1 question)
        closer = self._closer(engine_output)
        parts.append(closer)

        # 🔥 6. APPLY GLOBAL RULES
        final_text = self._apply_global_rules(parts)

        # 🔥 7. APPLY TONE ENGINE (FINAL LAYER)
        final_text = tone_engine.apply(
            final_text,
            user_profile=intent.get("user_profile"),
            signals=intent.get("signals")
        )

        return final_text

    # =========================
    # PROFILE SELECTION
    # =========================
    def _select_profile(self, intent):
        if not intent:
            return "layer_1_default"

        mode = intent.get("mode")
        domain = intent.get("domain")

        if domain == "shopping":
            return "route_to_shopping_engine"

        if mode == "style":
            return "layer_2_expandable_depth"

        return "layer_1_default"

    # =========================
    # COMPONENTS
    # =========================
    def _reaction(self):
        return "Nice — this is coming together."

    def _closer(self, engine_output):
        if engine_output.get("question"):
            return engine_output["question"]

        return "Want me to refine this further?"

    # =========================
    # GLOBAL RULE ENFORCER
    # =========================
    def _apply_global_rules(self, parts):
        rules = self.config.get("global_rules", {})

        # 🔥 Max questions enforcement
        max_q = rules.get("max_questions_per_response", 1)
        question_count = 0

        cleaned = []

        for p in parts:
            if "?" in p:
                if question_count >= max_q:
                    continue
                question_count += 1

            cleaned.append(p)

        # 🔥 Sentence limit
        max_sent = rules.get("max_sentences_layer_1", 3)

        final = "\n\n".join(cleaned)

        sentences = final.split(". ")
        if len(sentences) > max_sent:
            final = ". ".join(sentences[:max_sent])

        return final.strip()


# Singleton
response_assembler = ResponseAssembler()
