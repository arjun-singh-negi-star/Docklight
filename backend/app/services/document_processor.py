"""Extracts plain text from an uploaded file (pdf, docx, csv, html, txt/md) and chunks it."""
import csv
import io

from bs4 import BeautifulSoup
from docx import Document as DocxDocument
from pypdf import PdfReader


def extract_text(filename: str, file_bytes: bytes) -> str:
    lower = filename.lower()

    if lower.endswith(".pdf"):
        reader = PdfReader(io.BytesIO(file_bytes))
        return "\n".join(page.extract_text() or "" for page in reader.pages)

    if lower.endswith(".docx"):
        doc = DocxDocument(io.BytesIO(file_bytes))
        return "\n".join(p.text for p in doc.paragraphs)

    if lower.endswith(".csv"):
        text = file_bytes.decode("utf-8", errors="ignore")
        rows = csv.reader(io.StringIO(text))
        return "\n".join(", ".join(row) for row in rows)

    if lower.endswith(".html") or lower.endswith(".htm"):
        soup = BeautifulSoup(file_bytes.decode("utf-8", errors="ignore"), "html.parser")
        return soup.get_text(separator="\n")

    # .txt, .md, and anything else unrecognized: treat as plain text.
    return file_bytes.decode("utf-8", errors="ignore")


def chunk_text(text: str, chunk_size: int, overlap: int) -> list[str]:
    text = " ".join(text.split())
    if not text:
        return []
    chunks = []
    start = 0
    step = max(chunk_size - overlap, 1)
    while start < len(text):
        chunks.append(text[start : start + chunk_size])
        start += step
    return chunks
