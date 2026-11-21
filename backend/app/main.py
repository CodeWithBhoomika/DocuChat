import re
import time
from collections import defaultdict, deque

from fastapi import FastAPI, File, Form, HTTPException, Request, UploadFile
from fastapi.concurrency import run_in_threadpool
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

from . import llm
from .chunking import build_chunks, extract_pages
from .config import settings

SESSION_RE = re.compile(r"^[a-zA-Z0-9-]{16,64}$")

prod = settings.ENV == "production"
app = FastAPI(title="DocuChat API", docs_url=None if prod else "/docs",
              redoc_url=None, openapi_url=None if prod else "/openapi.json")

# Only the listed frontend origins may call the API from a browser
app.add_middleware(CORSMiddleware, allow_origins=settings.ALLOWED_ORIGINS,
                   allow_methods=["GET", "POST", "DELETE"], allow_headers=["Content-Type"])

_store = None


def get_store():
    """Created on first use so the app (and tests) start fast."""
    global _store
    if _store is None:
        from .store import VectorStore
        _store = VectorStore()
    return _store


# ---- simple per-IP rate limit (protects the Groq quota) ----
_hits: dict[str, deque] = defaultdict(deque)


@app.middleware("http")
async def rate_limit(request: Request, call_next):
    if request.url.path.startswith("/api/"):
        ip = request.client.host if request.client else "unknown"
        now, window = time.time(), _hits[ip]
        while window and now - window[0] > 60:
            window.popleft()
        if len(window) >= settings.RATE_LIMIT_PER_MIN:
            return JSONResponse({"detail": "Too many requests. Try again in a minute."}, status_code=429)
        window.append(now)
    return await call_next(request)


def valid_session(session_id: str) -> str:
    if not SESSION_RE.match(session_id):
        raise HTTPException(400, "Invalid session id.")
    return session_id


class AskRequest(BaseModel):
    session_id: str
    question: str = Field(min_length=2, max_length=1000)


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/api/upload")
async def upload(session_id: str = Form(...), files: list[UploadFile] = File(...)):
    valid_session(session_id)
    if len(files) > settings.MAX_FILES_PER_UPLOAD:
        raise HTTPException(400, f"Upload at most {settings.MAX_FILES_PER_UPLOAD} files at a time.")
    limit = settings.MAX_FILE_MB * 1024 * 1024
    added = []
    for f in files:
        data = await f.read(limit + 1)
        if len(data) > limit:
            raise HTTPException(413, f"{f.filename} is larger than {settings.MAX_FILE_MB} MB.")
        if not data.startswith(b"%PDF"):          # check real content, not only the extension
            raise HTTPException(400, f"{f.filename} is not a PDF file.")
        try:
            pages = await run_in_threadpool(extract_pages, data, settings.MAX_PAGES_PER_FILE)
        except Exception:
            raise HTTPException(400, f"{f.filename} could not be read. Is it damaged or password protected?")
        if not pages:
            raise HTTPException(422, f"{f.filename} has no selectable text (scanned PDFs are not supported).")
        name = re.sub(r"[^\w .()-]", "_", f.filename or "document.pdf")[:100]
        records = build_chunks(name, pages, settings.CHUNK_SIZE, settings.CHUNK_OVERLAP)
        await run_in_threadpool(get_store().add, session_id, records)
        added.append({"name": name, "pages": pages[-1][0], "chunks": len(records)})
    return {"added": added}


@app.post("/api/ask")
async def ask(body: AskRequest):
    valid_session(body.session_id)
    hits = llm.filter_hits(await run_in_threadpool(
        get_store().query, body.session_id, body.question, settings.TOP_K))
    try:
        text = await run_in_threadpool(llm.answer, body.question, hits)
    except Exception:
        raise HTTPException(502, "The AI service is unavailable. Please try again.")
    sources = [{"id": i, "file": h["file"], "page": h["page"], "snippet": h["text"][:300]}
               for i, h in enumerate(hits, start=1)]
    return {"answer": text, "sources": sources}


@app.get("/api/documents")
async def documents(session_id: str):
    valid_session(session_id)
    return {"documents": await run_in_threadpool(get_store().documents, session_id)}


@app.delete("/api/session/{session_id}")
async def clear(session_id: str):
    valid_session(session_id)
    await run_in_threadpool(get_store().delete_session, session_id)
    return {"cleared": True}
