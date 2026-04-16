from __future__ import annotations

import io
import logging

logger = logging.getLogger(__name__)

try:
    import pytesseract
    from PIL import Image

    _OCR_AVAILABLE = True
except ImportError:  # pragma: no cover
    _OCR_AVAILABLE = False
    logger.warning("pytesseract / Pillow not available; OCR disabled")


class OCRService:
    """Runs Tesseract OCR on rendered page images."""

    async def extract_text(self, png_bytes: bytes) -> str:
        """Return extracted text from a PNG image using Tesseract."""
        if not _OCR_AVAILABLE:
            return ""
        try:
            image = Image.open(io.BytesIO(png_bytes))
            text: str = pytesseract.image_to_string(image, config="--psm 6 --oem 3")
            return text.strip()
        except Exception:
            logger.exception("OCR text extraction failed")
            return ""

    async def confidence(self, png_bytes: bytes) -> float:
        """Return average word-level confidence (0.0–1.0) for the image."""
        if not _OCR_AVAILABLE:
            return 0.0
        try:
            image = Image.open(io.BytesIO(png_bytes))
            data: dict = pytesseract.image_to_data(
                image,
                output_type=pytesseract.Output.DICT,
                config="--psm 6 --oem 3",
            )
            confs = [int(c) for c in data.get("conf", []) if int(c) != -1]
            if not confs:
                return 0.0
            return min(1.0, sum(confs) / len(confs) / 100.0)
        except Exception:
            logger.exception("OCR confidence estimation failed")
            return 0.0
