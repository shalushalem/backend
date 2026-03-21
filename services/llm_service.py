def format_wardrobe_for_llm(items):
    """
    Converts Appwrite documents into a text summary for the AI.
    """
    if not items:
        return "The user's wardrobe is currently empty."
    
    wardrobe_msg = "The user has the following items in their wardrobe:\n"
    for item in items:
        # Assuming your Appwrite doc has 'name', 'category', and 'color'
        wardrobe_msg += f"- {item.get('name')} ({item.get('color')} {item.get('category')})\n"
    
    return wardrobe_msg