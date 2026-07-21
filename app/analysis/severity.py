from typing import Literal

CRITICAL_REAGENT_KEYWORDS = (
    "antibody",
    "ab",
    "enzyme",
    "serum",
    "matrigel",
    "ecm",
    "competent cells",
    "transfection reagent",
    "growth factor",
    "primary cells",
    "beads",
)


def reagent_gap_severity(reagent_name: str) -> Literal["critical", "low"]:
    name = reagent_name.lower()
    if any(keyword in name for keyword in CRITICAL_REAGENT_KEYWORDS):
        return "critical"
    return "low"
