# utils/chunker.py
import tiktoken

def chunk_text(text, max_tokens=4000, encoding_name="cl100k_base"):
    encoding = tiktoken.get_encoding(encoding_name)
    lines = text.split("\n")
    chunks = []
    current_chunk = []
    current_tokens = 0

    for line in lines:
        tokens = encoding.encode(line)
        token_count = len(tokens)

        if current_tokens + token_count > max_tokens:
            chunks.append("\n".join(current_chunk))
            current_chunk = [line]
            current_tokens = token_count
        else:
            current_chunk.append(line)
            current_tokens += token_count

    if current_chunk:
        chunks.append("\n".join(current_chunk))

    return chunks
