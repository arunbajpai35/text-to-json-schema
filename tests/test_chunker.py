import tiktoken

from utils.chunker import chunk_text

ENC = tiktoken.get_encoding("cl100k_base")


def _max_chunk_tokens(chunks):
    return max(len(ENC.encode(c)) for c in chunks)


def test_short_text_single_chunk():
    chunks = chunk_text("a\nb\nc", max_tokens=100)
    assert chunks == ["a\nb\nc"]


def test_packs_lines_until_limit():
    text = "\n".join(["line"] * 50)
    chunks = chunk_text(text, max_tokens=10)
    assert len(chunks) > 1


def test_oversize_line_is_split():
    big_line = "word " * 2000
    chunks = chunk_text(big_line, max_tokens=100)
    assert len(chunks) > 1
    assert _max_chunk_tokens(chunks) <= 100


def test_oversize_line_mixed_with_normal_lines():
    text = "short\n" + ("long " * 500) + "\nshort2"
    chunks = chunk_text(text, max_tokens=50)
    assert _max_chunk_tokens(chunks) <= 50
    joined = "".join(chunks)
    assert "short" in joined and "short2" in joined


def test_empty_input():
    assert chunk_text("", max_tokens=100) == [""]
