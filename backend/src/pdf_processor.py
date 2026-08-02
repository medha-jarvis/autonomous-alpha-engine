"""PDF processor — download, extract text, split into chunks."""

from __future__ import annotations

import logging
import os
import tempfile
import urllib.request
from dataclasses import dataclass, field
from typing import BinaryIO

import fitz  # PyMuPDF

logger = logging.getLogger(__name__)

BSE_PDF_BASE = "https://www.bseindia.com/xml-data/corpfiling/AttachLive/"


@dataclass
class ProcessedTranscript:
    """Result of processing a PDF transcript."""

    full_text: str
    prepared_remarks: str
    qa_section: str
    chunks: list[dict[str, str]] = field(default_factory=list)
    page_count: int = 0
    file_size_bytes: int = 0


def download_pdf(announcement: dict, dest_dir: str | None = None) -> bytes:
    """Download the PDF attachment from BSE servers.

    Returns the raw PDF bytes. Raises HTTPError on 404 (file removed).
    """
    pdf_url = announcement["pdf_url_bse"]
    req = urllib.request.Request(
        pdf_url,
        headers={
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            "Referer": "https://www.bseindia.com/",
            "Accept": "application/pdf,*/*",
        },
    )
    with urllib.request.urlopen(req, timeout=15) as resp:
        pdf_bytes = resp.read()

    logger.info(
        "Downloaded PDF for %s (%s): %d bytes",
        announcement["ticker"],
        announcement["news_id"][:8],
        len(pdf_bytes),
    )
    return pdf_bytes


def extract_text(pdf_bytes: bytes) -> ProcessedTranscript:
    """Extract text from PDF bytes using PyMuPDF.

    Also splits content into prepared remarks and Q&A sections
    heuristically.
    """
    doc = fitz.open(stream=pdf_bytes, filetype="pdf")
    full_text_parts: list[str] = []
    remarks_parts: list[str] = []
    qa_parts: list[str] = []

    in_qa = False
    qa_markers = [
        "question and answer",
        "q&a session",
        "questions and answers",
        "question & answer",
        "open forum",
        "question & answers",
        "moderator",
        "analyst:",
        "analyst :",
    ]

    for page in doc:
        text = page.get_text()
        full_text_parts.append(text)

        # Heuristic split: once we hit Q&A markers, switch mode
        if not in_qa:
            lower = text.lower()
            for marker in qa_markers:
                if marker in lower:
                    # Everything before this text is remarks,
                    # everything from here onward is Q&A
                    idx = lower.find(marker)
                    # Add this page's text before the marker to remarks
                    before = text[: idx + len(marker)]
                    after = text[idx + len(marker) :]
                    remarks_parts.append(before)
                    qa_parts.append(after)
                    in_qa = True
                    break

        if in_qa:
            qa_parts.append(text)
        else:
            remarks_parts.append(text)

    full_text = "\n".join(full_text_parts)
    prepared_remarks = "\n".join(remarks_parts) if remarks_parts else full_text
    qa_section = "\n".join(qa_parts) if qa_parts else ""

    # Generate chunks for Typesense (paragraph-sized)
    chunks = _chunk_text(full_text)

    result = ProcessedTranscript(
        full_text=full_text,
        prepared_remarks=prepared_remarks,
        qa_section=qa_section,
        chunks=chunks,
        page_count=len(doc),
        file_size_bytes=len(pdf_bytes),
    )
    doc.close()
    return result


def _chunk_text(text: str, max_chars: int = 3000) -> list[dict[str, str]]:
    """Split text into overlapping chunks for indexing."""
    paragraphs = text.split("\n\n")
    chunks: list[dict[str, str]] = []
    current = ""
    chunk_idx = 0

    for para in paragraphs:
        para = para.strip()
        if not para:
            continue
        if len(current) + len(para) > max_chars and current:
            chunks.append({
                "chunk_id": f"chunk_{chunk_idx:04d}",
                "content": current.strip(),
            })
            chunk_idx += 1
            current = para
        else:
            current += "\n\n" + para if current else para

    if current:
        chunks.append({
            "chunk_id": f"chunk_{chunk_idx:04d}",
            "content": current.strip(),
        })

    return chunks


def download_and_process(
    announcement: dict,
) -> tuple[bytes, ProcessedTranscript]:
    """Convenience: download PDF and extract text in one call."""
    pdf_bytes = download_pdf(announcement)
    transcript = extract_text(pdf_bytes)
    return pdf_bytes, transcript