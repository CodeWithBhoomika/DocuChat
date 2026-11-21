from app.chunking import build_chunks, chunk_text


def test_short_text_is_one_chunk():
    assert chunk_text("Hello world.", size=100, overlap=10) == ["Hello world."]


def test_long_text_is_split_with_overlap():
    text = " ".join(f"Sentence number {i}." for i in range(100))
    chunks = chunk_text(text, size=200, overlap=40)
    assert len(chunks) > 1
    assert all(len(c) <= 200 for c in chunks)
    # the end of one chunk reappears at the start of the next (overlap)
    assert chunks[0][-20:] in chunks[1]


def test_size_must_exceed_overlap():
    try:
        chunk_text("abc", size=10, overlap=10)
        assert False, "expected ValueError"
    except ValueError:
        pass


def test_chunks_keep_file_and_page_for_citations():
    records = build_chunks("notes.pdf", [(1, "First page."), (3, "Third page.")], 800, 150)
    assert [(r["file"], r["page"]) for r in records] == [("notes.pdf", 1), ("notes.pdf", 3)]
    assert len({r["id"] for r in records}) == 2  # ids are unique
