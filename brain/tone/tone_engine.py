import os
import json
from datetime import datetime


class ToneEngine:

    def __init__(self):
        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        file_path = os.path.join(base_dir, "shared", "tone", "tone_engine.json")

        try:
            with open(file_path, "r", encoding="utf-8") as f:
                self.config = json.load(f).get("ahvi_tone_engine_v1", {})
        except Exception as e:
            print(f"WARN: Tone engine load failed: {e}")
            self.config = {}

    # =========================
    # MAIN ENTRY
    # =========================
    def apply(self, text: str, user_profile: dict = None, signals: dict = None):

        if not text:
            return text

        # 🔥 Step 1: detect generation
        generation = self._detect_generation(user_profile)

        # 🔥 Step 2: context caps
        context_mode = (signals or {}).get("context_mode", "general")
        context_rules = self.config.get("context_modes", {}).get(context_mode, {})

        # 🔥 Step 3: emotion override
        emotion = (signals or {}).get("emotion_state", "neutral")
        emotion_rules = self.config.get("emotion_overrides", {}).get(emotion, {})

        # 🔥 Step 4: apply constraints
        text = self._apply_constraints(text, context_rules, emotion_rules)

        return text

    # =========================
    # GENERATION DETECTION
    # =========================
    def _detect_generation(self, user_profile):
        if not user_profile or not user_profile.get("dob_iso"):
            return "other"

        year = int(user_profile["dob_iso"].split("-")[0])

        buckets = self.config.get("generation_buckets", {})

        for name, r in buckets.items():
            if r["dob_year_min"] <= year <= r["dob_year_max"]:
                return name

        return "other"

    # =========================
    # APPLY RULES
    # =========================
    def _apply_constraints(self, text, context_rules, emotion_rules):

        # 🔥 remove excessive exclamation
        text = text.replace("!!", "!")

        # 🔥 enforce calm tone if vulnerable
        if emotion_rules.get("sentence_style") == "soft":
            text = text.replace("!", ".")

        # 🔥 remove slang in strict modes
        if context_rules.get("slang_cap", 0) == 0:
            text = self._remove_slang(text)

        return text

    # =========================
    # SIMPLE SLANG FILTER
    # =========================
    def _remove_slang(self, text):
        slang_list = self.config.get("slang_libraries", {}).get("gen_z", {}).get("approved_tokens", [])

        for s in slang_list:
            text = text.replace(s, "")

        return text.strip()


# Singleton
tone_engine = ToneEngine()
