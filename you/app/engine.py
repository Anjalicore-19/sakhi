"""Deterministic brain: which question next, who is eligible, what goes on her Pocket Pass.
Add a new scheme = add a JSON file. Add a new language = add a block in phrases.json."""
import json
from pathlib import Path

DATA = Path(__file__).parent / "data"
SCHEME = json.loads((DATA / "schemes" / "pmmvy.json").read_text(encoding="utf-8"))
PHRASES = json.loads((DATA / "phrases.json").read_text(encoding="utf-8"))

QUESTION_ORDER = ["is_pregnant_or_new_mother", "living_children", "has_own_bank_account"]


def safe_lang(lang: str) -> str:
    return lang if lang in PHRASES else "hi"


def say(lang: str, key: str) -> str:
    return PHRASES[lang][key]


def ask(lang: str, key: str) -> str:
    return PHRASES[lang]["ask"][key]


def merge(old: dict, new: dict) -> dict:
    merged = dict(old)
    for k, v in new.items():
        if v is not None:
            merged[k] = v
    return merged


def next_question(facts: dict):
    for key in QUESTION_ORDER:
        if facts.get(key) is None:
            return key
    return None


def decide(facts: dict) -> str:
    if facts.get("is_pregnant_or_new_mother") is False:
        return "not_eligible"
    kids = facts.get("living_children") or 0
    if kids == 0:
        return "eligible"
    if kids == 1:
        return "if_girl"          # 2nd child: benefit only if a girl is born
    return "not_eligible"


def final(facts: dict, lang: str) -> dict:
    p = PHRASES[lang]
    outcome = decide(facts)
    speech, docs, amount = [p["outcome"][outcome]], [], None
    need_account = facts.get("has_own_bank_account") is False

    if outcome != "not_eligible":
        amount = SCHEME["benefit_first_child"] if outcome == "eligible" else SCHEME["benefit_second_child_girl"]
        if need_account:
            speech.append(p["bank_missing"])
        docs = [{"id": d["id"], "emoji": d["emoji"], "label": p["docs"][d["id"]]} for d in SCHEME["documents"]]
        speech += [p["docs_intro"]] + [d["label"] for d in docs] + [p["where"], p["done"]]

    return {
        "speech": speech, "asked": None, "facts": facts,
        "card": {"outcome": outcome, "amount": amount, "docs": docs,
                 "helpline": SCHEME["helpline"], "need_account": need_account},
    }