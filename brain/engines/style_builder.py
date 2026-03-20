# backend/brain/engines/style_builder.py
import os
import json
import random

class StyleBuilderEngine:
    def __init__(self):
        # Define the path to your JSON banks
        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        self.banks_dir = os.path.join(base_dir, "banks")
        
        # Load the necessary JSON files into memory when the server starts
        self.events_bank = self._load_json("events/events_bank_v1.json")
        self.weather_bank = self._load_json("contextual/season_weather_overlays_bank_v1.json")
        self.formulas_bank = self._load_json("formulas/ahvi_outfit_builder_logic_v1.json")

    def _load_json(self, relative_path: str) -> dict:
        """Helper to safely load JSON files from the banks folder."""
        full_path = os.path.join(self.banks_dir, relative_path)
        try:
            with open(full_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except FileNotFoundError:
            print(f"Warning: Could not find {full_path}. Returning empty dict.")
            return {}

    def build_outfit(self, intent_data: dict) -> dict:
        """Builds an outfit based on NLU slots and JSON rules."""
        slots = intent_data.get("slots", {})
        occasion = slots.get("occasion")
        weather = slots.get("weather")

        # 1. Start with a baseline fallback outfit
        suggested_top = "basic_tshirt"
        suggested_bottom = "blue_jeans"
        suggested_shoes = "sneakers"
        accessories = []

        # 2. Apply Occasion Rules (From events_bank_v1.json)
        if occasion and self.events_bank:
            # Example: Looking up rules for 'wedding' or 'office'
            event_rules = self.events_bank.get(occasion, {})
            if event_rules:
                # Pick a random top/bottom combination allowed for this event
                suggested_top = random.choice(event_rules.get("allowed_tops", [suggested_top]))
                suggested_bottom = random.choice(event_rules.get("allowed_bottoms", [suggested_bottom]))
                suggested_shoes = random.choice(event_rules.get("allowed_shoes", [suggested_shoes]))
                accessories = event_rules.get("recommended_accessories", [])

        # 3. Apply Weather Overlays (From season_weather_overlays_bank_v1.json)
        if weather and self.weather_bank:
            weather_rules = self.weather_bank.get(weather, {})
            if weather_rules:
                # Add layers if cold, change to breathable fabrics if hot
                if "add_layer" in weather_rules:
                    suggested_top = f"{weather_rules['add_layer']} over {suggested_top}"
                if weather == "rainy":
                    suggested_shoes = "waterproof_boots"

        # 4. Format the final payload for Flutter
        response_payload = {
            "board_type": "style_board",
            "context": f"Outfit built for {occasion or 'casual wear'} " + (f"in {weather} weather." if weather else ""),
            "suggested_items": {
                "top": suggested_top,
                "bottom": suggested_bottom,
                "shoes": suggested_shoes,
                "accessories": accessories
            },
            "ui_layout": "side_by_side" # Tells Flutter how to render it
        }

        return response_payload

# Instantiate for easy import
style_engine = StyleBuilderEngine()