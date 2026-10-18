import os
import io
import logging
from typing import Optional, Tuple
import pdfplumber
import docx

from app.config import settings

logger = logging.getLogger("assesscraft.parsing")


def parse_pdf_plumber(file_bytes: bytes) -> Tuple[str, bool]:
    """
    Parses digital PDF content using pdfplumber.
    Returns (extracted_text, needs_ocr).
    needs_ocr is True if any page has fewer than 50 extractable characters.
    """
    text_parts = []
    needs_ocr = False

    with pdfplumber.open(io.BytesIO(file_bytes)) as pdf:
        for page_idx, page in enumerate(pdf.pages):
            page_text = page.extract_text() or ""
            text_parts.append(page_text)
            # If a page contains virtually no text, it is likely a scan
            if len(page_text.strip()) < 50:
                logger.info(f"Page {page_idx + 1} has only {len(page_text.strip())} chars; flagging for Document AI OCR.")
                needs_ocr = True

    combined_text = "\n\n".join(text_parts).strip()
    return combined_text, needs_ocr


def parse_docx(file_bytes: bytes) -> str:
    """Parses Word .docx documents."""
    doc = docx.Document(io.BytesIO(file_bytes))
    full_text = []
    for para in doc.paragraphs:
        if para.text.strip():
            full_text.append(para.text.strip())
    for table in doc.tables:
        for row in table.rows:
            row_text = " | ".join(cell.text.strip() for cell in row.cells if cell.text.strip())
            if row_text:
                full_text.append(row_text)
    return "\n".join(full_text)


def parse_pptx(file_bytes: bytes) -> str:
    """Parses PowerPoint .pptx slides: every text box and table, plus speaker notes, slide by slide."""
    from pptx import Presentation

    deck = Presentation(io.BytesIO(file_bytes))
    out = []
    for number, slide in enumerate(deck.slides, start=1):
        lines = []
        for shape in slide.shapes:
            if shape.has_text_frame and shape.text_frame.text.strip():
                lines.append(shape.text_frame.text.strip())
            if getattr(shape, "has_table", False) and shape.has_table:
                for row in shape.table.rows:
                    row_text = " | ".join(c.text.strip() for c in row.cells if c.text.strip())
                    if row_text:
                        lines.append(row_text)
        if slide.has_notes_slide and slide.notes_slide.notes_text_frame.text.strip():
            lines.append("Notes: " + slide.notes_slide.notes_text_frame.text.strip())
        if lines:
            out.append(f"--- Slide {number} ---\n" + "\n".join(lines))
    return "\n\n".join(out)


def parse_with_document_ai_ocr(file_bytes: bytes) -> Optional[str]:
    """
    Fallback OCR processor using Google Cloud Document AI for scanned documents.
    Uses general processor in DOCAI_REGION ('us' or 'eu').
    """
    if not settings.DOCAI_PROCESSOR_ID or not settings.GCP_PROJECT_ID:
        logger.info("Document AI processor ID or GCP_PROJECT_ID not configured; skipping cloud OCR.")
        return None

    try:
        from google.cloud import documentai_v1 as documentai

        client_options = {}
        if settings.DOCAI_REGION in ("us", "eu"):
            client_options["api_endpoint"] = f"{settings.DOCAI_REGION}-documentai.googleapis.com"

        client = documentai.DocumentProcessorServiceClient(client_options=client_options)
        name = client.processor_path(settings.GCP_PROJECT_ID, settings.DOCAI_REGION, settings.DOCAI_PROCESSOR_ID)

        raw_document = documentai.RawDocument(
            content=file_bytes,
            mime_type="application/pdf"
        )
        request = documentai.ProcessRequest(name=name, raw_document=raw_document)
        result = client.process_document(request=request)
        return result.document.text
    except Exception as e:
        logger.error(f"Document AI OCR execution error: {e}")
        return None


def extract_document_text(file_bytes: bytes, filename: str) -> str:
    """
    Primary extraction entrypoint:
    1. For text/markdown, directly decodes UTF-8.
    2. For docx, uses python-docx.
    3. For PDF, uses pdfplumber; if < 50 chars/page, falls back to Document AI OCR.
    """
    ext = os.path.splitext(filename.lower())[1]

    if ext in (".md", ".txt", ".csv", ".json"):
        return file_bytes.decode("utf-8", errors="replace")

    if ext == ".docx":
        return parse_docx(file_bytes)

    if ext == ".pptx":
        return parse_pptx(file_bytes)

    if ext == ".pdf":
        text, needs_ocr = parse_pdf_plumber(file_bytes)
        if needs_ocr:
            ocr_text = parse_with_document_ai_ocr(file_bytes)
            if ocr_text and len(ocr_text.strip()) > len(text.strip()):
                return ocr_text
        return text

    # Fallback attempt
    try:
        return file_bytes.decode("utf-8", errors="replace")
    except Exception:
        return f"[Binary file {filename} could not be text-parsed]"
