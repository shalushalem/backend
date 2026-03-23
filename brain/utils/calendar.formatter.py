def unique(items):
    return list(set([i.strip() for i in items if i]))


def section(title, items):
    cleaned = [i.strip() for i in items if i and i.strip()]
    if not cleaned:
        return None
    return {
        "title": title,
        "items": cleaned
    }


def build_calendar_checklist_bundle(event: dict, predictive: dict):
    """
    event = classified event
    predictive = output from calendar_engine
    """

    packing_list = predictive.get("packing", [])
    prep_tasks = predictive.get("prep_tasks", [])
    outfit = predictive.get("outfit", {})

    # =========================
    # CARRY
    # =========================
    carry_items = unique(packing_list)

    # =========================
    # WEAR
    # =========================
    wear_items = unique(
        outfit.get("outfitKeywords", []) +
        outfit.get("footwearKeywords", []) +
        outfit.get("accessoryKeywords", [])
    )

    # =========================
    # PREP TONIGHT
    # =========================
    prep_tonight_items = unique([
        task for task in prep_tasks
        if any(k in task.lower() for k in [
            "check", "pack", "set", "review", "charge", "confirm", "decide"
        ])
    ])

    # =========================
    # DOCUMENTS
    # =========================
    document_items = unique([
        item for item in carry_items
        if any(k in item.lower() for k in [
            "id", "passport", "visa", "ticket", "reports", "insurance", "cv", "deck", "documents"
        ])
    ])

    # =========================
    # PAYMENT
    # =========================
    payment_items = []
    if event.get("group") == "finance":
        if event.get("amount"):
            payment_items.append(f"Amount: ₹{event['amount']}")
        else:
            payment_items.append("Amount ready")

        if event.get("dueDateISO"):
            payment_items.append(f"Due: {event['dueDateISO']}")
        else:
            payment_items.append("Check due date")

        if event.get("autoPayEnabled"):
            payment_items.append("Autopay enabled")
        else:
            payment_items.append("Payment method ready")

    # =========================
    # CHILD ITEMS
    # =========================
    child_items = []
    if event.get("group") in ["kids", "school"]:
        child_items = unique(
            carry_items +
            [t for t in prep_tasks if "child" in t.lower()]
        )

    return {
        "carry": section("Carry", carry_items),
        "wear": section("Wear", wear_items),
        "prepTonight": section("Prep tonight", prep_tonight_items),
        "documents": section("Documents", document_items),
        "payment": section("Payment", payment_items),
        "childItems": section("Child items", child_items)
    }