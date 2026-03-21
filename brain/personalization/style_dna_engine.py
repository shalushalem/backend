# backend/brain/personalization/style_dna_engine.py

from typing import Dict, Any, List

class StyleDNAEngine:
    def enrich_context(self, context: Dict[str, Any]) -> Dict[str, Any]:
        profile = context.get("user_profile", {})
        history = context.get("history", [])

        dna = self._build_dna(profile, history)
        context["style_dna"] = dna

        return context

    def _build_dna(self, profile: Dict, history: List[Dict]):
        preferred_colors = profile.get("preferred_colors", [])
        style = profile.get("style", "casual")

        return {
            "style": style,
            "preferred_colors": preferred_colors,
            "disliked_items": []
        }

    def score_item(self, item: Dict[str, Any], dna: Dict[str, Any]) -> int:
        score = 0

        if item.get("color") in dna.get("preferred_colors", []):
            score += 2

        if dna.get("style") in item.get("vibe", []):
            score += 2

        if item.get("name") in dna.get("disliked_items", []):
            score -= 3

        return score

style_dna_engine = StyleDNAEngine()