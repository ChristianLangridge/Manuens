from typing import Literal

Recoverability = Literal["perishable_now", "perishable_today", "stable"]

_PERISHABLE_NOW_KEYWORDS = ("lot", "tube", "plate", "reagent", "position")
_PERISHABLE_TODAY_KEYWORDS = ("rpm", "duration", "time", "temperature", "operator", "rotor")


def field_recoverability(field_name: str) -> Recoverability:
    name = field_name.lower()
    if any(keyword in name for keyword in _PERISHABLE_NOW_KEYWORDS):
        return "perishable_now"
    if any(keyword in name for keyword in _PERISHABLE_TODAY_KEYWORDS):
        return "perishable_today"
    return "stable"
