
def grade(item: dict, choice_id: str):
    """
    Pure function. Returns (correct: bool, tags: list[str], chosen_text: str, score: float)
    
    Now supports partial credit if the item has a rubric with partial_credit definitions.
    """
    choices = {c["id"]: c for c in item["choices"]}
    chosen = choices.get(choice_id)
    if not chosen:
        return False, ["invalid_choice"], "", 0.0
    
    tags = chosen.get("tags_on_select", [])
    is_correct = "correct" in tags
    
    # Default: full credit (1.0) if correct, no credit (0.0) if wrong
    score = 1.0 if is_correct else 0.0
    
    # Check if item has rubric with partial credit rules
    if not is_correct and "rubric" in item:
        rubric = item["rubric"]
        partial_credit = rubric.get("partial_credit", [])
        
        # Check each partial credit rule against the tags
        for rule in partial_credit:
            # Match tags against the rule's condition
            # Simple matching: if all tags in rule are in chosen tags, apply partial credit
            when_text = rule.get("when", "").lower()
            
            # Heuristic matching: check if any tag matches the "when" condition
            for tag in tags:
                if tag.lower() in when_text or when_text in tag.lower():
                    score = rule.get("points", 0.5)
                    break
    
    return is_correct, tags, chosen.get("text", ""), score
