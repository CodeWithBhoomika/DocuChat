"""API tests with the vector store and Groq replaced by fakes (no network needed)."""
import io

import pytest
from fastapi.testclient import TestClient

from app import llm, main

SESSION = "a" * 32


class FakeStore:
    def __init__(self):
        self.records = []

    def add(self, session_id, records):
        self.records += records

    def query(self, session_id, question, k):
        return [{"text": r["text"], "file": r["file"], "page": r["page"], "distance": 0.2}
                for r in self.records][:k]

    def documents(self, session_id):
        return []

    def delete_session(self, session_id):
        self.records = []


@pytest.fixture
def client(monkeypatch):
    store = FakeStore()
    monkeypatch.setattr(main, "get_store", lambda: store)
    monkeypatch.setattr(llm, "answer", lambda q, hits: "Fake answer [1].")
    main._hits.clear()
    return TestClient(main.app)


def test_health(client):
    assert client.get("/health").json() == {"status": "ok"}


def test_rejects_bad_session_id(client):
    r = client.post("/api/ask", json={"session_id": "short", "question": "hi there"})
    assert r.status_code == 400


def test_rejects_non_pdf(client):
    files = {"files": ("fake.pdf", io.BytesIO(b"not a pdf"), "application/pdf")}
    r = client.post("/api/upload", data={"session_id": SESSION}, files=files)
    assert r.status_code == 400


def test_upload_then_ask_returns_answer_with_sources(client):
    from pypdf import PdfWriter
    buf = io.BytesIO()
    writer = PdfWriter()
    writer.add_blank_page(width=200, height=200)
    writer.write(buf)
    files = {"files": ("blank.pdf", io.BytesIO(buf.getvalue()), "application/pdf")}
    # a blank page has no text, so the API must explain why it cannot be used
    r = client.post("/api/upload", data={"session_id": SESSION}, files=files)
    assert r.status_code == 422


def test_ask_uses_retrieved_sources(client, monkeypatch):
    main.get_store().records.append({"text": "Python is a language.", "file": "a.pdf", "page": 2})
    r = client.post("/api/ask", json={"session_id": SESSION, "question": "What is Python?"})
    body = r.json()
    assert r.status_code == 200
    assert body["answer"] == "Fake answer [1]."
    assert body["sources"][0]["file"] == "a.pdf" and body["sources"][0]["page"] == 2


def test_rate_limit(client, monkeypatch):
    monkeypatch.setattr(main.settings, "RATE_LIMIT_PER_MIN", 2)
    codes = [client.get("/api/documents", params={"session_id": SESSION}).status_code for _ in range(3)]
    assert codes[-1] == 429


def test_prompt_contains_numbered_passages_and_rules():
    hits = [{"text": "Alpha text", "file": "a.pdf", "page": 1, "distance": 0.1}]
    msgs = llm.build_messages("Q?", hits)
    assert "[1] (file: a.pdf, page 1)" in msgs[1]["content"]
    assert "ONLY" in msgs[0]["content"]
