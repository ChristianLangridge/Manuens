import json
from pathlib import Path

from app.analysis.engine import analyse_run
from app.models import ExtractedRun, ExtractedStep, FieldValue, Protocol, UnassignedFragment

PROTOCOLS_DIR = Path(__file__).resolve().parents[2] / "data" / "protocols"


def _load_coip_protocol() -> Protocol:
    data = json.loads((PROTOCOLS_DIR / "co_immunoprecipitation.json").read_text())
    return Protocol.model_validate(data)


def test_calibration_note_produces_exactly_four_expected_findings() -> None:
    """ "ran the IP, 4C ON, used the new lot of protein G beads, only 2h on the ab
    bc I was late, spun 12k" — see TDD.md §16.
    """
    protocol = _load_coip_protocol()
    run = ExtractedRun(
        steps=[
            ExtractedStep(
                step_id="1",
                fields={"temperature_c": FieldValue(value=4, source_phrase="4C ON")},
            ),
            ExtractedStep(
                step_id="2",
                fields={
                    "reagent": FieldValue(
                        value="protein G beads",
                        source_phrase="the new lot of protein G beads",
                    ),
                    "lot": None,
                },
            ),
            ExtractedStep(
                step_id="3",
                fields={"duration_min": FieldValue(value=120, source_phrase="only 2h on the ab")},
            ),
        ],
        unassigned=[UnassignedFragment(text="spun 12k", reason="no step reference")],
    )

    result = analyse_run(protocol, run)

    by_type = {"deviation": 0, "gap": 0, "ambiguity": 0}
    for finding in result.findings:
        by_type[finding.type] += 1

    assert by_type == {"deviation": 1, "gap": 1, "ambiguity": 1}

    gap = next(f for f in result.findings if f.type == "gap")
    assert gap.severity == "critical"
    assert gap.recoverability == "perishable_now"

    deviation = next(f for f in result.findings if f.type == "deviation")
    assert deviation.severity == "material"

    assert result.clean_step_ids == ["1"]


def test_fully_clean_run_produces_zero_findings() -> None:
    protocol = _load_coip_protocol()
    run = ExtractedRun(
        steps=[
            ExtractedStep(
                step_id="1", fields={"temperature_c": FieldValue(value=4, source_phrase="4C")}
            ),
            ExtractedStep(
                step_id="2",
                fields={
                    "reagent": FieldValue(value="protein G beads", source_phrase="protein G beads"),
                    "lot": FieldValue(value="PG-2201", source_phrase="lot PG-2201"),
                },
            ),
            ExtractedStep(
                step_id="3",
                fields={
                    "antibody": FieldValue(value="anti-FLAG M2", source_phrase="anti-FLAG M2"),
                    "antibody_lot": FieldValue(value="AB-551", source_phrase="lot AB-551"),
                    "duration_min": FieldValue(value=240, source_phrase="240 min"),
                    "temperature_c": FieldValue(value=4, source_phrase="4C"),
                },
            ),
            ExtractedStep(
                step_id="4",
                fields={
                    "buffer": FieldValue(value="PBS-T", source_phrase="PBS-T"),
                    "buffer_lot": FieldValue(value="W-99", source_phrase="lot W-99"),
                },
            ),
            ExtractedStep(
                step_id="5",
                fields={
                    "duration_min": FieldValue(value=10, source_phrase="10 min"),
                    "temperature_c": FieldValue(value=95, source_phrase="95C"),
                },
            ),
        ],
        unassigned=[],
    )

    result = analyse_run(protocol, run)

    assert result.findings == []
    assert set(result.clean_step_ids) == {"1", "2", "3", "4", "5"}
