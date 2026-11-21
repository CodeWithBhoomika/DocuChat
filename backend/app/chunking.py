"""Pure functions (no external services) so they are easy to test."""
import hashlib
import io

from pypdf import PdfReader


def extract_pages(data: bytes, max_pages: int = 200) -> list[tuple[int, str]]:
    """Return [(page_number, text), ...] for every page that has text."""
    reader = PdfReader(io.BytesIO(data))
    pages = []
    for number, page in enumerate(reader.pages[:max_pages], start=1):
        text = " ".join((page.extract_text() or "").split())  # collapse whitespace
        if text:
            pages.append((number, text))
    return pages


def chunk_text(text: str, size: int = 800, overlap: int = 150) -> list[str]:
    """Split text into overlapping chunks, preferring to cut at a sentence end.

    Overlap keeps a sentence that sits on a boundary from losing its context."""
    if size <= overlap:
        raise ValueError("size must be larger than overlap")
    chunks, start = [], 0
    while start < len(text):
        end = min(start + size, len(text))
        if end < len(text):
            cut = text.rfind(". ", start + size // 2, end)  # last sentence end in window
            if cut != -1:
                end = cut + 1
        chunk = text[start:end].strip()
        if chunk:
            chunks.append(chunk)
        if end >= len(text):
            break
        start = max(end - overlap, start + 1)
    return chunks


def build_chunks(filename: str, pages: list[tuple[int, str]], size: int, overlap: int) -> list[dict]:
    """Turn pages into records that keep their source file and page number
    (this metadata is what makes citations possible later)."""
    file_id = hashlib.sha256(filename.encode()).hexdigest()[:10]
    records = []
    for page_no, text in pages:
        for i, chunk in enumerate(chunk_text(text, size, overlap)):
            records.append({
                "id": f"{file_id}-p{page_no}-c{i}",
                "text": chunk,
                "file": filename,
                "page": page_no,
            })
    return records
