
def grade(item: dict, choice_id: str):
    """
    Pure function. Returns (correct: bool, tags: list[str], chosen_text: str)
    """
    choices = {c["id"]: c for c in item["choices"]}
    chosen = choices.get(choice_id)
    if not chosen:
        return False, ["invalid_choice"], ""
    tags = chosen.get("tags_on_select", [])
    correct = "correct" in tags
    return correct, tags, chosen.get("text","")
