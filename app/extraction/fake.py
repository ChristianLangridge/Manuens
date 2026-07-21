from pathlib import Path

from app.models import ExtractedRun, ExtractedStep, FieldValue, Protocol, UnassignedFragment

_EXAMPLES_DIR = Path(__file__).resolve().parents[2] / "data" / "examples"

_COIP_FIXTURES_BY_FILENAME: dict[str, ExtractedRun] = {
    "bad_calibration.txt": ExtractedRun(
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
    ),
    "clean_run.txt": ExtractedRun(
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
    ),
    "moderate_chronological.txt": ExtractedRun(
        steps=[
            ExtractedStep(
                step_id="1",
                fields={"temperature_c": FieldValue(value=4, source_phrase="4C for 30 min")},
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
                    "duration_min": FieldValue(
                        value="overnight",
                        source_phrase=(
                            "left on the rotator at 4C overnight instead of the usual 4h"
                        ),
                    ),
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
    ),
}

_FIXTURES_BY_PROTOCOL: dict[str, dict[str, ExtractedRun]] = {
    "co_immunoprecipitation": _COIP_FIXTURES_BY_FILENAME,
}


def _matching_fixture(note_text: str, protocol_id: str) -> ExtractedRun | None:
    stripped = note_text.strip()
    for filename, fixture in _FIXTURES_BY_PROTOCOL.get(protocol_id, {}).items():
        example_path = _EXAMPLES_DIR / filename
        if example_path.read_text().strip() == stripped:
            return fixture
    return None


class FakeExtractor:
    """Deterministic extractor used by every test and by the demo when no LLM key is configured.

    Recognises the three seeded example notes verbatim; anything else lands entirely in
    ``unassigned`` rather than fabricating structure, per the "never guess" rule in TDD.md §8.
    """

    async def extract(self, note_text: str, protocol: Protocol) -> ExtractedRun:
        fixture = _matching_fixture(note_text, protocol.id)
        if fixture is not None:
            return fixture
        return ExtractedRun(
            steps=[],
            unassigned=[
                UnassignedFragment(
                    text=note_text,
                    reason="fake extractor: no live model configured, text not recognised",
                )
            ],
        )
