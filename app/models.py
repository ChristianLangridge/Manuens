from typing import Literal

from pydantic import BaseModel


class Step(BaseModel):
    id: str
    name: str
    required_fields: list[str]
    expected_values: dict[str, str | float]
    tolerance: dict[str, float]
    sensitivity: Literal["high", "low"]


class Protocol(BaseModel):
    id: str
    name: str
    steps: list[Step]


class FieldValue(BaseModel):
    value: str | float
    source_phrase: str


class ExtractedStep(BaseModel):
    step_id: str
    fields: dict[str, FieldValue | None]


class UnassignedFragment(BaseModel):
    text: str
    reason: str


class ExtractedRun(BaseModel):
    steps: list[ExtractedStep]
    unassigned: list[UnassignedFragment]


class Finding(BaseModel):
    type: Literal["deviation", "gap", "ambiguity"]
    severity: Literal["critical", "low", "material", "informational"]
    recoverability: Literal["perishable_now", "perishable_today", "stable"]
    message: str
    step_id: str | None
    field: str | None
    source_phrase: str | None = None
