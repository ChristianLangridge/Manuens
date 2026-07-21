import asyncio
import json

from anthropic import AsyncAnthropic
from pydantic import ValidationError

from app.models import ExtractedRun, Protocol, UnassignedFragment

_TIMEOUT_SECONDS = 20
_MODEL = "claude-sonnet-5"


def parse_extraction_json(raw: str) -> ExtractedRun:
    """Raises ValidationError/json.JSONDecodeError on malformed model output."""
    return ExtractedRun.model_validate(json.loads(raw))


def _build_prompt(note_text: str, protocol: Protocol) -> str:
    schema = protocol.model_dump_json()
    return (
        "Map the following bench note onto the protocol's step schema. "
        "Return strict JSON matching the ExtractedRun shape: "
        '{"steps": [{"step_id": "...", "fields": {"<field>": {"value": ..., '
        '"source_phrase": "..."} | null}}], "unassigned": [{"text": "...", "reason": "..."}]}. '
        "Never guess a step assignment — put anything you cannot confidently place in "
        "'unassigned'. Only extract; do not judge severity or completeness.\n\n"
        f"Protocol schema:\n{schema}\n\nNote:\n{note_text}"
    )


class LLMExtractor:
    """Real extractor. Not exercised by CI or by default in this build (no API key configured) —
    the interface exists so swapping the live model in is a config change, per TDD.md §15.
    """

    def __init__(self, client: AsyncAnthropic | None = None) -> None:
        self._client = client or AsyncAnthropic()

    async def _call_model(self, prompt: str) -> str:
        response = await self._client.messages.create(
            model=_MODEL,
            max_tokens=2048,
            messages=[{"role": "user", "content": prompt}],
        )
        return response.content[0].text  # type: ignore[union-attr]

    async def extract(self, note_text: str, protocol: Protocol) -> ExtractedRun:
        prompt = _build_prompt(note_text, protocol)
        try:
            raw = await asyncio.wait_for(self._call_model(prompt), timeout=_TIMEOUT_SECONDS)
            return parse_extraction_json(raw)
        except (ValidationError, json.JSONDecodeError, TimeoutError) as first_error:
            retry_prompt = (
                f"{prompt}\n\nYour previous response was invalid: {first_error}. "
                "Return valid JSON only, matching the schema exactly."
            )
            try:
                raw = await asyncio.wait_for(
                    self._call_model(retry_prompt), timeout=_TIMEOUT_SECONDS
                )
                return parse_extraction_json(raw)
            except Exception:
                return ExtractedRun(
                    steps=[],
                    unassigned=[
                        UnassignedFragment(
                            text=note_text,
                            reason="extraction failed after retry, degraded to unassigned",
                        )
                    ],
                )
