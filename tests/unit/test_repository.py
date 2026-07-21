from pathlib import Path

from app.models import ExtractedRun, Run
from app.storage.repository import InMemoryRunRepository, ProtocolRepository

PROTOCOLS_DIR = Path(__file__).resolve().parents[2] / "data" / "protocols"


def test_save_then_get_returns_the_same_run() -> None:
    repo = InMemoryRunRepository()
    run = Run(
        id="r1", protocol_id="p", note_text="note", extracted=ExtractedRun(steps=[], unassigned=[])
    )

    repo.save(run)

    assert repo.get("r1") == run
    assert repo.get("missing") is None


def test_protocol_repository_loads_seeded_json() -> None:
    repo = ProtocolRepository(PROTOCOLS_DIR)

    protocol = repo.get("co_immunoprecipitation")

    assert protocol is not None
    assert protocol.name == "Co-Immunoprecipitation"
    assert len(repo.list()) == 2
