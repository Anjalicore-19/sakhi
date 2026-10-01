from app import engine


def test_first_child_is_eligible():
    assert engine.decide({"is_pregnant_or_new_mother": True, "living_children": 0}) == "eligible"


def test_second_child_only_if_girl():
    assert engine.decide({"is_pregnant_or_new_mother": True, "living_children": 1}) == "if_girl"


def test_three_children_not_eligible():
    assert engine.decide({"is_pregnant_or_new_mother": True, "living_children": 3}) == "not_eligible"


def test_merge_keeps_old_and_ignores_none():
    assert engine.merge({"a": 1}, {"a": None, "b": 2}) == {"a": 1, "b": 2}


def test_question_order_and_done():
    assert engine.next_question({}) == "is_pregnant_or_new_mother"
    full = {"is_pregnant_or_new_mother": True, "living_children": 0, "has_own_bank_account": False}
    assert engine.next_question(full) is None
    card = engine.final(full, "ta")["card"]
    assert card["need_account"] and card["amount"] == 5000 and len(card["docs"]) == 3