from app.services.document_processor import chunk_text, extract_text


def test_chunk_text_basic():
    text = "word " * 500
    chunks = chunk_text(text, chunk_size=200, overlap=50)
    assert len(chunks) > 1
    assert all(len(c) <= 200 for c in chunks)


def test_chunk_text_empty():
    assert chunk_text("   ", chunk_size=200, overlap=50) == []


def test_extract_text_plain():
    assert extract_text("notes.txt", b"hello there") == "hello there"
