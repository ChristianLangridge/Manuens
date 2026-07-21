import json
from pathlib import Path
from typing import Protocol as TypingProtocol

from app.models import Protocol, Run


class RunRepository(TypingProtocol):
    def get(self, run_id: str) -> Run | None: ...
    def save(self, run: Run) -> None: ...


class InMemoryRunRepository:
    """Deliberate scope decision (TDD.md §2): state resets on restart. This interface is the
    seam — swapping in Postgres later is a one-file change.
    """

    def __init__(self) -> None:
        self._runs: dict[str, Run] = {}

    def get(self, run_id: str) -> Run | None:
        return self._runs.get(run_id)

    def save(self, run: Run) -> None:
        self._runs[run.id] = run


class ProtocolRepository:
    def __init__(self, protocols_dir: Path) -> None:
        self._protocols: dict[str, Protocol] = {}
        for path in sorted(protocols_dir.glob("*.json")):
            data = json.loads(path.read_text())
            protocol = Protocol.model_validate(data)
            self._protocols[protocol.id] = protocol

    def get(self, protocol_id: str) -> Protocol | None:
        return self._protocols.get(protocol_id)

    def list(self) -> list[Protocol]:
        return list(self._protocols.values())
