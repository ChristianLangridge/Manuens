import json
from pathlib import Path

import pytest
from pydantic import ValidationError

from app.extraction.fake import FakeExtractor
from app.extraction.llm import LLMExtractor, parse_extraction_json
from app.models import Protocol

PROTOCOLS_DIR = Path(__file__).resolve().parents[2] / "data" / "protocols"
EXAMPLES_DIR = Path(__file__).resolve().parents[2] / "data" / "examples"


def _load_coip_protocol() -> Protocol:
    data = json.loads((PROTOCOLS_DIR / "co_immunoprecipitation.json").read_text())
    return Protocol.model_validate(data)


def test_valid_extraction_json_parses_to_extracted_run() -> None:
    raw = json.dumps({"steps": [], "unassigned": []})
    run = parse_extraction_json(raw)
    assert run.steps == []
    assert run.unassigned == []


def test_malformed_json_raises() -> None:
    with pytest.raises(json.JSONDecodeError):
        parse_extraction_json("not json")


def test_json_not_matching_schema_raises_validation_error() -> None:
    with pytest.raises(ValidationError):
        parse_extraction_json(json.dumps({"steps": "not-a-list"}))


@pytest.mark.anyio
async def test_llm_extractor_degrades_to_unassigned_after_failed_retry() -> None:
    class _AlwaysBadClient:
        async def _call_model(self, prompt: str) -> str:
            return "not valid json"

    extractor = LLMExtractor.__new__(LLMExtractor)
    extractor._call_model = _AlwaysBadClient()._call_model  # type: ignore[method-assign]

    protocol = _load_coip_protocol()
    run = await extractor.extract("some note", protocol)

    assert run.steps == []
    assert len(run.unassigned) == 1
    assert "degraded" in run.unassigned[0].reason


@pytest.mark.anyio
async def test_fake_extractor_recognises_calibration_example() -> None:
    protocol = _load_coip_protocol()
    note = (EXAMPLES_DIR / "bad_calibration.txt").read_text()

    run = await FakeExtractor().extract(note, protocol)

    assert len(run.steps) == 3
    assert len(run.unassigned) == 1


@pytest.mark.anyio
async def test_fake_extractor_puts_unrecognised_text_entirely_in_unassigned() -> None:
    protocol = _load_coip_protocol()

    run = await FakeExtractor().extract(
        "some freeform text nobody prepared a fixture for", protocol
    )

    assert run.steps == []
    assert len(run.unassigned) == 1


@pytest.fixture
def anyio_backend() -> str:
    return "asyncio"
