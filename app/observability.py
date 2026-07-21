import json
import logging
import sys
import time
import uuid
from collections.abc import Awaitable, Callable
from contextvars import ContextVar

from starlette.requests import Request
from starlette.responses import Response

request_id_var: ContextVar[str] = ContextVar("request_id", default="-")


class JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        payload = {
            "level": record.levelname,
            "message": record.getMessage(),
            "logger": record.name,
            "request_id": request_id_var.get(),
        }
        extra = getattr(record, "fields", None)
        if extra:
            payload.update(extra)
        return json.dumps(payload)


def configure_logging(log_level: str) -> None:
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(JsonFormatter())
    root = logging.getLogger()
    root.handlers = [handler]
    root.setLevel(log_level)


async def request_id_middleware(
    request: Request, call_next: Callable[[Request], Awaitable[Response]]
) -> Response:
    incoming_id = request.headers.get("x-request-id")
    request_id = incoming_id or str(uuid.uuid4())
    token = request_id_var.set(request_id)
    start = time.monotonic()
    try:
        response = await call_next(request)
    finally:
        request_id_var.reset(token)
    response.headers["x-request-id"] = request_id
    response.headers["x-latency-ms"] = str(round((time.monotonic() - start) * 1000, 1))
    return response


def log_run_event(
    logger: logging.Logger,
    *,
    protocol_id: str,
    note_length: int,
    findings_count: int,
    latency_ms: float,
    extraction_status: str,
) -> None:
    """Never logs note content — bench notes are unpublished IP (TDD.md §15)."""
    logger.info(
        "run_analysed",
        extra={
            "fields": {
                "protocol_id": protocol_id,
                "note_length": note_length,
                "findings_count": findings_count,
                "latency_ms": latency_ms,
                "extraction_status": extraction_status,
            }
        },
    )
