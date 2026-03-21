# backend/brain/engines/style_builder.py

import os
import json
from itertools import product

class StyleBuilderEngine:
    def __init__(self):
        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        self.banks_dir = os.path.join(base_dir, "banks")

        self.events_bank = self._load_json("events/events_bank_v1.json")
        self.weather_bank = self._load_json("contextual/season_weather_overlays_bank_v1.json")
        self.formulas_bank = self._load_json("formulas/ahvi_outfit_builder_logic_v1.json")

    def _load_json(self, relative_path: str) -> dict:
        try:
            full_path = os.path.join(self.banks_dir, relative_path)
            with open(full_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except:
            return {}

    # =========================================================
    # 🔍 FILTER HELPERS (🚀 NULL-SAFE)
    # =========================================================
    def _filter_by_type(self, wardrobe, keyword):
        # Safely convert to string before calling .lower() to prevent Appwrite null crashes
        return [i for i in wardrobe if keyword in str(i.get("type") or i.get("category", "")).lower()]

    # =========================================================
    # 🎯 ITEM SCORING (🚀 NULL-SAFE)
    # =========================================================
    def _score_item(self, item, occasion, weather, vibe, dna):
        score = 0

        # Use 'or []' to prevent iterating over None
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

        return score

    # =========================================================
    # 🎨 COLOR COMPATIBILITY
    # =========================================================
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

    # =========================================================
    # 🧠 OUTFIT SCORING
    # =========================================================
    def _score_outfit(self, t, b, s, occasion, weather, vibe, dna):
        score = 0
        score += self._score_item(t, occasion, weather, vibe, dna)
        score += self._score_item(b, occasion, weather, vibe, dna)
        score += self._score_item(s, occasion, weather, vibe, dna)

        score += self._color_score(t.get("color"), b.get("color"))
        score += self._color_score(b.get("color"), s.get("color"))

        return score

    # =========================================================
    # 🔥 MAIN ENGINE
    # =========================================================
    def build_outfit(self, context: dict) -> dict:
        slots = context.get("slots", {})
        wardrobe = context.get("wardrobe", [])
        dna = context.get("style_dna", {})

        occasion = slots.get("occasion")
        weather = slots.get("weather")
        vibe = slots.get("vibe")

        # 1. FILTER wardrobe
        tops = self._filter_by_type(wardrobe, "top")
        bottoms = self._filter_by_type(wardrobe, "bottom")
        shoes = self._filter_by_type(wardrobe, "footwear") or self._filter_by_type(wardrobe, "shoes")

        outfits = []

        # 2. GENERATE COMBINATIONS
        for t, b, s in product(tops, bottoms, shoes):
            score = self._score_outfit(t, b, s, occasion, weather, vibe, dna)
            outfits.append({
                "top": t,
                "bottom": b,
                "shoes": s,
                "score": score
            })

        # 3. SORT BEST
        outfits = sorted(outfits, key=lambda x: x["score"], reverse=True)
        top_outfits = outfits[:3]

        # 4. FALLBACK (if wardrobe empty)
        if not top_outfits:
            return {
                "board_type": "style_board",
                "outfits": [],
                "context": "Not enough matching items found in your wardrobe!"
            }

        # 5. APPLY EVENT RULES
        accessories = []
        if occasion and self.events_bank:
            event_rules = self.events_bank.get(occasion, {})
            accessories = event_rules.get("recommended_accessories", [])

        # 6. FORMAT RESPONSE
        formatted = []
        for o in top_outfits:
            formatted.append({
                "top": o["top"].get("name", "Top"),
                "bottom": o["bottom"].get("name", "Bottom"),
                "shoes": o["shoes"].get("name", "Shoes"),
                "score": o["score"]
            })

        return {
            "board_type": "style_board",
            "context": f"Top outfit picks for {occasion or 'your vibe'}"
                + (f" in {weather} weather." if weather else ""),
            "outfits": formatted,
            "accessories": accessories,
            "ui_layout": "carousel"
        }

style_engine = StyleBuilderEngine()