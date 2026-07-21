from app.analysis.gaps import find_gaps
from app.models import ExtractedRun, ExtractedStep, FieldValue, Protocol, Step


def _protocol_with_bead_step() -> Protocol:
    return Protocol(
        id="p",
        name="Test protocol",
        steps=[
            Step(
                id="2",
                name="Bead incubation",
                required_fields=["reagent", "lot"],
                expected_values={"reagent": "protein G beads"},
                tolerance={},
                sensitivity="high",
            )
        ],
    )


def test_missing_critical_reagent_lot_is_critical_and_perishable_now() -> None:
    protocol = _protocol_with_bead_step()
    run = ExtractedRun(
        steps=[
            ExtractedStep(
                step_id="2",
                fields={
                    "reagent": FieldValue(
                        value="protein G beads", source_phrase="the new lot of protein G beads"
                    ),
                    "lot": None,
                },
            )
        ],
        unassigned=[],
    )

    findings = find_gaps(protocol, run)

    assert len(findings) == 1
    assert findings[0].type == "gap"
    assert findings[0].severity == "critical"
    assert findings[0].recoverability == "perishable_now"


def test_missing_buffer_lot_is_low_severity() -> None:
    protocol = Protocol(
        id="p",
        name="Test protocol",
        steps=[
            Step(
                id="4",
                name="Wash",
                required_fields=["buffer", "buffer_lot"],
                expected_values={},
                tolerance={},
                sensitivity="low",
            )
        ],
    )
    run = ExtractedRun(
        steps=[
            ExtractedStep(
                step_id="4",
                fields={
                    "buffer": FieldValue(value="PBS-T", source_phrase="washed with PBS-T"),
                    "buffer_lot": None,
                },
            )
        ],
        unassigned=[],
    )

    findings = find_gaps(protocol, run)

    assert len(findings) == 1
    assert findings[0].severity == "low"


def test_clean_run_produces_no_gaps() -> None:
    protocol = _protocol_with_bead_step()
    run = ExtractedRun(
        steps=[
            ExtractedStep(
                step_id="2",
                fields={
                    "reagent": FieldValue(value="protein G beads", source_phrase="protein G beads"),
                    "lot": FieldValue(value="PG-2201", source_phrase="lot PG-2201"),
                },
            )
        ],
        unassigned=[],
    )

    assert find_gaps(protocol, run) == []
