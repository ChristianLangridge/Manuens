from app.analysis.recoverability import field_recoverability
from app.analysis.severity import reagent_gap_severity
from app.models import ExtractedRun, ExtractedStep, Finding, Protocol, Step


def _reagent_name_for_lot_field(
    field_name: str, extracted_step: ExtractedStep, step: Step
) -> str | None:
    if field_name == "lot":
        reagent_key = "reagent"
    elif field_name.endswith("_lot"):
        reagent_key = field_name.removesuffix("_lot")
    else:
        return None

    reagent_field = extracted_step.fields.get(reagent_key)
    if reagent_field is not None:
        return str(reagent_field.value)
    expected = step.expected_values.get(reagent_key)
    return str(expected) if expected is not None else reagent_key


def find_gaps(protocol: Protocol, run: ExtractedRun) -> list[Finding]:
    steps_by_id = {step.id: step for step in protocol.steps}
    findings: list[Finding] = []

    for extracted_step in run.steps:
        step = steps_by_id.get(extracted_step.step_id)
        if step is None:
            continue

        for field_name in step.required_fields:
            if extracted_step.fields.get(field_name) is not None:
                continue

            reagent_name = _reagent_name_for_lot_field(field_name, extracted_step, step)
            severity = reagent_gap_severity(reagent_name) if reagent_name else "low"

            findings.append(
                Finding(
                    type="gap",
                    severity=severity,
                    recoverability=field_recoverability(field_name),
                    message=f"{step.name}: missing {field_name.replace('_', ' ')}",
                    step_id=step.id,
                    field=field_name,
                )
            )

    return findings
