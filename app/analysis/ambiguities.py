import re
from typing import Literal

from app.models import ExtractedRun, Finding, Protocol, Step

_RPM_WITHOUT_ROTOR = re.compile(r"\b\d+\s*k\b|\brpm\b", re.IGNORECASE)
_HAS_ROTOR = re.compile(r"\brotor\b", re.IGNORECASE)
_ROOM_TEMP = re.compile(r"\bRT\b|\broom temperature\b", re.IGNORECASE)
_ROOM_TEMP_WITH_NUMBER = re.compile(r"\bRT\s*\(?\d")
_OVERNIGHT = re.compile(r"\bovernight\b|\bON\b")
_HAS_DURATION_NUMBER = re.compile(r"\d+\s*(h|hr|hrs|hours|min|minutes)\b", re.IGNORECASE)
_TEMP_NO_UNIT = re.compile(r"^\d+(\.\d+)?$")

_AMBIGUITY_RECOVERABILITY: Literal["perishable_today"] = "perishable_today"


def _step_expects_overnight(step: Step | None) -> bool:
    if step is None:
        return False
    return step.expected_values.get("duration_desc") == "overnight"


def _check_text(text: str, step: Step | None) -> str | None:
    if _RPM_WITHOUT_ROTOR.search(text) and not _HAS_ROTOR.search(text):
        return "centrifugation speed given without rotor/radius — unreproducible"
    if _ROOM_TEMP.search(text) and not _ROOM_TEMP_WITH_NUMBER.search(text):
        return "room temperature given without a number"
    if _OVERNIGHT.search(text) and not _HAS_DURATION_NUMBER.search(text):
        if not _step_expects_overnight(step):
            return "overnight given without hours"
    return None


def find_ambiguities(protocol: Protocol, run: ExtractedRun) -> list[Finding]:
    steps_by_id = {step.id: step for step in protocol.steps}
    findings: list[Finding] = []

    for extracted_step in run.steps:
        step = steps_by_id.get(extracted_step.step_id)
        for field_name, field_value in extracted_step.fields.items():
            if field_value is None:
                continue
            message = _check_text(field_value.source_phrase, step)
            if message is None:
                continue
            findings.append(
                Finding(
                    type="ambiguity",
                    severity="informational",
                    recoverability=_AMBIGUITY_RECOVERABILITY,
                    message=message,
                    step_id=extracted_step.step_id,
                    field=field_name,
                    source_phrase=field_value.source_phrase,
                )
            )

    for fragment in run.unassigned:
        message = _check_text(fragment.text, None)
        if message is None:
            continue
        findings.append(
            Finding(
                type="ambiguity",
                severity="informational",
                recoverability=_AMBIGUITY_RECOVERABILITY,
                message=message,
                step_id=None,
                field=None,
                source_phrase=fragment.text,
            )
        )

    return findings
