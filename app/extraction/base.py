from typing import Protocol as TypingProtocol

from app.models import ExtractedRun
from app.models import Protocol as ProtocolModel


class ExtractorProtocol(TypingProtocol):
    async def extract(self, note_text: str, protocol: ProtocolModel) -> ExtractedRun: ...
