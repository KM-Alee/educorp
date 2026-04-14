from __future__ import annotations

import io

import pdfplumber
import srt
import webvtt
from docx import Document
from pptx import Presentation


class ExtractionService:
    """Text extraction helpers for course assets."""

    def extract_text(self, asset_type: str, data: bytes) -> str:
        if asset_type in {"txt", "md"}:
            return data.decode("utf-8", errors="replace")
        if asset_type == "pdf":
            return self._extract_pdf(data)
        if asset_type == "docx":
            return self._extract_docx(data)
        if asset_type == "pptx":
            return self._extract_pptx(data)
        if asset_type == "vtt":
            return self._extract_vtt(data)
        if asset_type == "srt":
            return self._extract_srt(data)
        return data.decode("utf-8", errors="replace")

    @staticmethod
    def _extract_pdf(data: bytes) -> str:
        with pdfplumber.open(io.BytesIO(data)) as pdf:
            pages = [page.extract_text() or "" for page in pdf.pages]
        return "\n".join(pages)

    @staticmethod
    def _extract_docx(data: bytes) -> str:
        doc = Document(io.BytesIO(data))
        return "\n".join([para.text for para in doc.paragraphs])

    @staticmethod
    def _extract_pptx(data: bytes) -> str:
        presentation = Presentation(io.BytesIO(data))
        lines: list[str] = []
        for slide in presentation.slides:
            for shape in slide.shapes:
                if hasattr(shape, "text"):
                    text = shape.text.strip()
                    if text:
                        lines.append(text)
        return "\n".join(lines)

    @staticmethod
    def _extract_vtt(data: bytes) -> str:
        text = data.decode("utf-8", errors="replace")
        try:
            captions = webvtt.read_buffer(io.StringIO(text))
            return "\n".join([cap.text for cap in captions])
        except Exception:
            return text

    @staticmethod
    def _extract_srt(data: bytes) -> str:
        text = data.decode("utf-8", errors="replace")
        try:
            subtitles = list(srt.parse(text))
            return "\n".join([sub.content for sub in subtitles])
        except Exception:
            return text
