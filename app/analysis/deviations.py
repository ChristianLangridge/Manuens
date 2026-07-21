from app.analysis.recoverability import field_recoverability
from app.analysis.severity import deviation_severity
from app.models import ExtractedRun, Finding, Protocol


def find_deviations(protocol: Protocol, run: ExtractedRun) -> list[Finding]:
    steps_by_id = {step.id: step for step in protocol.steps}
    findings: list[Finding] = []

    for extracted_step in run.steps:
        step = steps_by_id.get(extracted_step.step_id)
        if step is None:
            continue

        for field_name, expected in step.expected_values.items():
            if not isinstance(expected, int | float):
                continue
            field_value = extracted_step.fields.get(field_name)
            if field_value is None or not isinstance(field_value.value, int | float):
                continue

            severity = deviation_severity(
                sensitivity=step.sensitivity,
                expected=expected,
                actual=field_value.value,
                tolerance=step.tolerance.get(field_name, 0),
            )
            if severity is None:
                continue

            findings.append(
                Finding(
                    type="deviation",
                    severity=severity,
                    recoverability=field_recoverability(field_name),
                    message=(
                        f"{step.name}: {field_name.replace('_', ' ')} was "
                        f"{field_value.value}, protocol expects {expected}"
                    ),
                    step_id=step.id,
                    field=field_name,
                    source_phrase=field_value.source_phrase,
                )
            )

    return findings
