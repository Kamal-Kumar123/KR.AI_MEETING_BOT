def chunk_text(text: str, chunk_size: int = 500, overlap: int = 100) -> list[str]:
    text = text.strip()
    if not text:
        return []
    if len(text) <= chunk_size:
        return [text]

    chunks = []
    start = 0
    while start < len(text):
        end = start + chunk_size
        chunk = text[start:end].strip()
        if chunk:
            chunks.append(chunk)
        if end >= len(text):
            break
        start = max(end - overlap, start + 1)
    return chunks


def chunk_transcript(transcript: str, chunk_size: int = 500, overlap: int = 100) -> list[str]:
    lines = [line.strip() for line in transcript.splitlines() if line.strip()]
    if not lines:
        return []

    speaker_lines = [line for line in lines if ":" in line[:40]]
    if len(speaker_lines) >= 2:
        chunks = []
        current = ""
        for line in lines:
            candidate = f"{current}\n{line}".strip() if current else line
            if len(candidate) <= chunk_size:
                current = candidate
            else:
                if current:
                    chunks.append(current)
                current = line
        if current:
            chunks.append(current)
        return chunks

    return chunk_text(transcript, chunk_size=chunk_size, overlap=overlap)
