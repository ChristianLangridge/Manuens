import asyncio
import html
import re
import uuid
from pathlib import Path

from fastapi import FastAPI, Form, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from app.analysis.engine import analyse_run
from app.config import settings
from app.extraction.base import ExtractorProtocol
from app.extraction.fake import FakeExtractor
from app.models import ExtractedRun, ExtractedStep, FieldValue, Protocol, Run, UnassignedFragment
from app.storage.repository import InMemoryRunRepository, ProtocolRepository

_EXTRACTION_TIMEOUT_SECONDS = 20

BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR.parent / "data"

app = FastAPI(title="Manuens")
app.mount("/static", StaticFiles(directory=BASE_DIR / "static"), name="static")
templates = Jinja2Templates(directory=BASE_DIR / "templates")

protocol_repo = ProtocolRepository(DATA_DIR / "protocols")
run_repo = InMemoryRunRepository()


def get_extractor() -> ExtractorProtocol:
    if settings.extractor == "llm":
        from app.extraction.llm import LLMExtractor

        return LLMExtractor()
    return FakeExtractor()


_EXAMPLE_FILES = [
    ("bad_calibration.txt", "Genuinely bad (the one to demo)"),
    ("moderate_chronological.txt", "Moderately messy"),
    ("clean_run.txt", "Clean run"),
]


def _load_examples() -> list[dict[str, str]]:
    examples_dir = DATA_DIR / "examples"
    return [
        {"label": label, "text": (examples_dir / filename).read_text().strip()}
        for filename, label in _EXAMPLE_FILES
    ]


def _highlight_note(note_text: str, run: Run) -> str:
    phrases = set()
    for step in run.extracted.steps:
        for field_value in step.fields.values():
            if field_value is not None:
                phrases.add(field_value.source_phrase)
    for fragment in run.extracted.unassigned:
        phrases.add(fragment.text)

    escaped = html.escape(note_text)
    for phrase in sorted(phrases, key=len, reverse=True):
        escaped_phrase = html.escape(phrase)
        if escaped_phrase and escaped_phrase in escaped:
            escaped = escaped.replace(escaped_phrase, f"<mark>{escaped_phrase}</mark>", 1)
    return escaped


def _run_context(request: Request, run: Run) -> dict:
    protocol = protocol_repo.get(run.protocol_id)
    assert protocol is not None
    result = analyse_run(protocol, run.extracted)
    extracted_by_step = {step.step_id: step for step in run.extracted.steps}
    return {
        "request": request,
        "run": run,
        "protocol": protocol,
        "extracted": run.extracted,
        "extracted_by_step": extracted_by_step,
        "findings": result.findings,
    }


@app.get("/healthz")
def healthz() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/readyz")
def readyz() -> dict[str, str]:
    settings.validate_ready()
    return {"status": "ready"}


@app.get("/", response_class=HTMLResponse)
def index(request: Request) -> HTMLResponse:
    return templates.TemplateResponse(
        request,
        "index.html",
        {"protocols": protocol_repo.list(), "examples": _load_examples()},
    )


async def _extract_or_degrade(
    extractor: ExtractorProtocol, note_text: str, protocol: Protocol
) -> tuple[ExtractedRun, bool]:
    """Never lets a slow or failing model take the app down (TDD.md §9)."""
    try:
        extracted = await asyncio.wait_for(
            extractor.extract(note_text, protocol), timeout=_EXTRACTION_TIMEOUT_SECONDS
        )
        return extracted, True
    except Exception:
        degraded = ExtractedRun(
            steps=[],
            unassigned=[UnassignedFragment(text=note_text, reason="extraction unavailable, retry")],
        )
        return degraded, False


@app.post("/runs", response_class=HTMLResponse)
async def create_run(
    request: Request, protocol_id: str = Form(...), note_text: str = Form(...)
) -> HTMLResponse:
    note_text = note_text[:20000]
    protocol = protocol_repo.get(protocol_id)
    if protocol is None:
        return HTMLResponse("Unknown protocol", status_code=400)

    extractor = get_extractor()
    extracted, extraction_ok = await _extract_or_degrade(extractor, note_text, protocol)

    run = Run(
        id=str(uuid.uuid4()), protocol_id=protocol_id, note_text=note_text, extracted=extracted
    )
    run_repo.save(run)

    context = _run_context(request, run)
    context["highlighted_note"] = _highlight_note(note_text, run)
    context["extraction_ok"] = extraction_ok
    return templates.TemplateResponse(request, "run.html", context)


@app.post("/runs/{run_id}/answer", response_class=HTMLResponse)
def answer_gap(
    request: Request,
    run_id: str,
    step_id: str = Form(...),
    field: str = Form(...),
    answer: str = Form(...),
) -> HTMLResponse:
    run = run_repo.get(run_id)
    if run is None:
        return HTMLResponse("Run not found", status_code=404)

    extracted_step = next((s for s in run.extracted.steps if s.step_id == step_id), None)
    if extracted_step is None:
        extracted_step = ExtractedStep(step_id=step_id, fields={})
        run.extracted.steps.append(extracted_step)

    value: str | float = float(answer) if re.fullmatch(r"-?\d+(\.\d+)?", answer) else answer
    extracted_step.fields[field] = FieldValue(value=value, source_phrase=answer)
    run_repo.save(run)

    context = _run_context(request, run)
    return templates.TemplateResponse(request, "partials/_analysis.html", context)
