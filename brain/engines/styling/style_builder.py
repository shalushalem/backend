import os
import json
from itertools import product

# 🔥 Template Engine
from brain.templates.template_engine import build_board


class StyleBuilderEngine:
    def __init__(self):
        base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

        # 📦 BANKS (existing)
        self.banks_dir = os.path.join(base_dir, "banks")

        self.events_bank = self._load_json("events/events_bank_v1.json")
        self.weather_bank = self._load_json("contextual/season_weather_overlays_bank_v1.json")
        self.formulas_bank = self._load_json("formulas/ahvi_outfit_builder_logic_v1.json")

        # 🔥 NEW: STYLE KNOWLEDGE (HIGH LEVEL)
        self.style_knowledge = self._load_data_json("style_knowledge_v1.json")

    # =========================
    # LOADERS
    # =========================
    def _load_json(self, relative_path: str) -> dict:
        try:
            full_path = os.path.join(self.banks_dir, relative_path)
            with open(full_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            print(f"WARN: Bank load failed: {relative_path}. {e}")
            return {}

    def _load_data_json(self, filename: str) -> dict:
        try:
            base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
            data_dir = os.path.join(base_dir, "data")
            full_path = os.path.join(data_dir, filename)

            with open(full_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            print(f"WARN: Data file load failed: {filename}. {e}")
            return {}

    # =========================
    # STYLE INTELLIGENCE (NEW)
    # =========================
    def _apply_style_knowledge(self, wardrobe, slots, dna):
        """
        Filters wardrobe using body-type intelligence
        """

        if not self.style_knowledge:
            return wardrobe

        body_type = dna.get("body_type")
        gender = dna.get("gender", "women")

        body_data = (
            self.style_knowledge
            .get(gender, {})
            .get("body_types", {})
            .get(body_type, {})
        )

        if not body_data:
            return wardrobe

        preferred = body_data.get("best", {})
        preferred_keywords = []

        for key in ["tops", "pants", "skirts", "dresses"]:
            preferred_keywords.extend(preferred.get(key, []))

        filtered = []

        for item in wardrobe:
            name = str(item.get("name", "")).lower()

            if any(p.lower() in name for p in preferred_keywords):
                filtered.append(item)

        return filtered or wardrobe  # fallback

    # =========================
    # FILTER HELPERS
    # =========================
    def _filter_by_type(self, wardrobe, keyword):
        return [
            i for i in wardrobe
            if keyword in str(i.get("type") or i.get("category", "")).lower()
        ]

    # =========================
    # ITEM SCORING
    # =========================
    def _score_item(self, item, occasion, weather, vibe, dna):
        score = 0

        if occasion and occasion in (item.get("tags") or []):
            score += 3

        if weather and weather in (item.get("weather") or []):
            score += 2

        if vibe and vibe in (item.get("vibe") or []):
            score += 2

        if dna:
            if item.get("color") in (dna.get("preferred_colors") or []):
                score += 2
            if item.get("name") in (dna.get("disliked_items") or []):
                score -= 3

        # 🔥 Bonus for having style knowledge active
        if dna.get("body_type") and self.style_knowledge:
            score += 1

        return score

    # =========================
    # COLOR COMPATIBILITY
    # =========================
    def _color_score(self, c1, c2):
        if not c1 or not c2:
            return 0

        if c1 == c2:
            return -1

        good_pairs = [
            ("black", "white"),
            ("blue", "white"),
            ("navy", "beige"),
            ("black", "grey")
        ]

        if (c1, c2) in good_pairs or (c2, c1) in good_pairs:
            return 2

        return 1

    # =========================
    # OUTFIT SCORING
    # =========================
    def _score_outfit(self, t, b, s, occasion, weather, vibe, dna):
        score = 0

        score += self._score_item(t, occasion, weather, vibe, dna)
        score += self._score_item(b, occasion, weather, vibe, dna)
        score += self._score_item(s, occasion, weather, vibe, dna)

        score += self._color_score(t.get("color"), b.get("color"))
        score += self._color_score(b.get("color"), s.get("color"))

        return score

    # =========================
    # MAIN ENGINE
    # =========================
    def build_outfit(self, context: dict) -> dict:
        slots = context.get("slots", {})
        wardrobe = context.get("wardrobe", [])
        dna = context.get("style_dna", {})

        occasion = slots.get("occasion")
        weather = slots.get("weather")
        vibe = slots.get("vibe")

        # 🔥 STEP 0: APPLY STYLE INTELLIGENCE
        wardrobe = self._apply_style_knowledge(wardrobe, slots, dna)

        # =========================
        # 1. FILTER WARDROBE
        # =========================
        tops = self._filter_by_type(wardrobe, "top")
        bottoms = self._filter_by_type(wardrobe, "bottom")
        shoes = (
            self._filter_by_type(wardrobe, "footwear")
            or self._filter_by_type(wardrobe, "shoes")
        )

        outfits = []

        # =========================
        # 2. GENERATE COMBINATIONS
        # =========================
        for t, b, s in product(tops, bottoms, shoes):
            score = self._score_outfit(t, b, s, occasion, weather, vibe, dna)

            outfits.append({
                "top": t,
                "bottom": b,
                "shoes": s,
                "score": score
            })

        # =========================
        # 3. SORT BEST
        # =========================
        outfits = sorted(outfits, key=lambda x: x["score"], reverse=True)
        top_outfits = outfits[:3]

        # =========================
        # 4. FALLBACK
        # =========================
        if not top_outfits:
            return {
                "board_type": "style_board",
                "outfits": [],
                "context": "Not enough matching items found in your wardrobe!",
                "board": {}
            }

        # =========================
        # 5. ACCESSORIES FROM EVENT RULES
        # =========================
        accessories = []
        if occasion and self.events_bank:
            event_rules = self.events_bank.get(occasion, {})
            accessories = event_rules.get("recommended_accessories", [])

        # =========================
        # 6. FORMAT OUTFITS
        # =========================
        formatted = []
        for o in top_outfits:
            formatted.append({
                "top": o["top"].get("name", "Top"),
                "bottom": o["bottom"].get("name", "Bottom"),
                "shoes": o["shoes"].get("name", "Shoes"),
                "score": o["score"]
            })

        # =========================
        # 7. BUILD BOARD
        # =========================
        best = top_outfits[0]

        outfit_data = {
            "top": best["top"].get("name"),
            "bottom": best["bottom"].get("name"),
            "shoes": best["shoes"].get("name")
        }

        try:
            board = build_board(outfit_data, wardrobe)
        except Exception as e:
            print("⚠️ Board generation failed:", e)
            board = {}

        # =========================
        # FINAL RESPONSE
        # =========================
        return {
            "board_type": "style_board",
            "context": f"Top outfit picks for {occasion or 'your vibe'}"
                + (f" in {weather} weather." if weather else ""),
            "outfits": formatted,
            "accessories": accessories,
            "board": board
        }


# Singleton
style_engine = StyleBuilderEngine()
