from app.analysis.deviations import find_deviations
from app.models import ExtractedRun, ExtractedStep, FieldValue, Protocol, Step


def _antibody_step(sensitivity: str) -> Protocol:
    return Protocol(
        id="p",
        name="Test protocol",
        steps=[
            Step(
                id="3",
                name="Antibody incubation",
                required_fields=["duration_min"],
                expected_values={"duration_min": 240},
                tolerance={"duration_min": 30},
                sensitivity=sensitivity,
            )
        ],
    )


def _run_with_duration(minutes: float) -> ExtractedRun:
    return ExtractedRun(
        steps=[
            ExtractedStep(
                step_id="3",
                fields={
                    "duration_min": FieldValue(value=minutes, source_phrase="only 2h on the ab")
                },
            )
        ],
        unassigned=[],
    )


def test_material_deviation_flagged_on_high_sensitivity_step() -> None:
    findings = find_deviations(_antibody_step("high"), _run_with_duration(120))

    assert len(findings) == 1
    assert findings[0].type == "deviation"
    assert findings[0].severity == "material"


def test_same_deviation_on_low_sensitivity_step_is_informational_not_material() -> None:
    findings = find_deviations(_antibody_step("low"), _run_with_duration(120))

    assert len(findings) == 1
    assert findings[0].severity == "informational"


def test_deviation_within_tolerance_produces_no_finding() -> None:
    assert find_deviations(_antibody_step("high"), _run_with_duration(230)) == []


def test_clean_run_produces_no_deviations() -> None:
    assert find_deviations(_antibody_step("high"), _run_with_duration(240)) == []
