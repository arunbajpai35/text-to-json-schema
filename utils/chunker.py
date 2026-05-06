# utils/chunker.py
import tiktoken


def chunk_text(text, max_tokens=4000, encoding_name="cl100k_base"):
    encoding = tiktoken.get_encoding(encoding_name)
    chunks = []
    current_chunk = []
    current_tokens = 0

    def flush():
        nonlocal current_chunk, current_tokens
        if current_chunk:
            chunks.append("\n".join(current_chunk))
            current_chunk = []
            current_tokens = 0

    for line in text.split("\n"):
        tokens = encoding.encode(line)
        token_count = len(tokens)

        if token_count > max_tokens:
            flush()
            for i in range(0, token_count, max_tokens):
                chunks.append(encoding.decode(tokens[i : i + max_tokens]))
            continue

        if current_tokens + token_count > max_tokens:
            flush()

        current_chunk.append(line)
        current_tokens += token_count

    flush()
    return chunks
