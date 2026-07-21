import json
import logging

from app.observability import JsonFormatter, log_run_event


def test_log_run_event_never_includes_note_content(caplog) -> None:
    logger = logging.getLogger("test-manuens")
    handler = logging.StreamHandler()
    handler.setFormatter(JsonFormatter())

    records: list[str] = []

    class _CapturingHandler(logging.Handler):
        def emit(self, record: logging.LogRecord) -> None:
            records.append(JsonFormatter().format(record))

    logger.addHandler(_CapturingHandler())
    logger.setLevel(logging.INFO)

    log_run_event(
        logger,
        protocol_id="co_immunoprecipitation",
        note_length=87,
        findings_count=3,
        latency_ms=12.4,
        extraction_status="ok",
    )

    assert len(records) == 1
    payload = json.loads(records[0])
    assert payload["note_length"] == 87
    assert payload["protocol_id"] == "co_immunoprecipitation"
    assert "note_text" not in payload
    assert "note" not in payload
