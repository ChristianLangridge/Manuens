from app.analysis.ambiguities import find_ambiguities
from app.models import ExtractedRun, ExtractedStep, FieldValue, Protocol, Step, UnassignedFragment


def test_rpm_without_rotor_in_unassigned_fragment_is_ambiguous() -> None:
    protocol = Protocol(id="p", name="Test protocol", steps=[])
    run = ExtractedRun(
        steps=[],
        unassigned=[UnassignedFragment(text="spun 12k", reason="no step reference")],
    )

    findings = find_ambiguities(protocol, run)

    assert len(findings) == 1
    assert findings[0].type == "ambiguity"


def test_overnight_where_protocol_specifies_overnight_is_not_ambiguous() -> None:
    protocol = Protocol(
        id="p",
        name="Test protocol",
        steps=[
            Step(
                id="1",
                name="Lysis",
                required_fields=["temperature_c"],
                expected_values={"temperature_c": 4, "duration_desc": "overnight"},
                tolerance={},
                sensitivity="low",
            )
        ],
    )
    run = ExtractedRun(
        steps=[
            ExtractedStep(
                step_id="1",
                fields={
                    "temperature_c": FieldValue(value=4, source_phrase="4C ON"),
                },
            )
        ],
        unassigned=[],
    )

    assert find_ambiguities(protocol, run) == []


def test_overnight_without_protocol_expectation_is_ambiguous() -> None:
    protocol = Protocol(
        id="p",
        name="Test protocol",
        steps=[
            Step(
                id="3",
                name="Antibody incubation",
                required_fields=["duration_min"],
                expected_values={"duration_min": 240},
                tolerance={"duration_min": 30},
                sensitivity="high",
            )
        ],
    )
    run = ExtractedRun(
        steps=[
            ExtractedStep(
                step_id="3",
                fields={
                    "duration_min": FieldValue(value="overnight", source_phrase="left overnight"),
                },
            )
        ],
        unassigned=[],
    )

    findings = find_ambiguities(protocol, run)
    assert len(findings) == 1
    assert findings[0].type == "ambiguity"
