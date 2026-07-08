from datetime import datetime

from .chunker import chunk_transcript
from .embeddings import embed_query, embed_texts
from .vector_store import VectorStore

_rag_service = None


class MeetingRAGService:
    def __init__(self, vector_store: VectorStore | None = None):
        self.store = vector_store or VectorStore()

    def index_meeting(
        self,
        meeting_id: str,
        transcript: str,
        summary: str,
        action_items: list,
        timestamp: str | None = None,
        mode: str = "standalone",
        series_id: str | None = None,
    ) -> int:
        # Re-index: remove old chunks for this meeting first.
        self.store.delete_meeting(meeting_id)

        timestamp = timestamp or datetime.utcnow().isoformat()
        series_id = series_id or meeting_id
        documents = []
        ids = []
        metadatas = []

        base_metadata = {
            "meeting_id": meeting_id,
            "timestamp": timestamp,
            "mode": mode,
            "series_id": series_id,
        }

        for index, chunk in enumerate(chunk_transcript(transcript)):
            documents.append(chunk)
            ids.append(f"{meeting_id}__transcript__{index}")
            metadatas.append({**base_metadata, "chunk_type": "transcript", "chunk_index": index})

        if summary.strip():
            documents.append(summary.strip())
            ids.append(f"{meeting_id}__summary")
            metadatas.append({**base_metadata, "chunk_type": "summary", "chunk_index": -1})

        for index, item in enumerate(action_items or []):
            if not isinstance(item, dict):
                continue
            task = item.get("task", "")
            owner = item.get("owner", "")
            deadline = item.get("deadline", "")
            text = f"Action item: {task}. Owner: {owner}. Deadline: {deadline}."
            documents.append(text)
            ids.append(f"{meeting_id}__action__{index}")
            metadatas.append(
                {
                    **base_metadata,
                    "chunk_type": "action_item",
                    "chunk_index": index,
                    "owner": owner,
                    "deadline": deadline,
                }
            )

        if not documents:
            return 0

        embeddings = embed_texts(documents)
        self.store.add_documents(ids=ids, documents=documents, embeddings=embeddings, metadatas=metadatas)
        return len(documents)

    def retrieve(self, query: str, top_k: int = 5, series_id: str | None = None) -> list[dict]:
        if self.store.count() == 0:
            return []

        where = {"series_id": series_id} if series_id else None
        result = self.store.query(query_embedding=embed_query(query), top_k=top_k, where=where)
        documents = result.get("documents", [[]])[0]
        metadatas = result.get("metadatas", [[]])[0]
        distances = result.get("distances", [[]])[0]

        hits = []
        for document, metadata, distance in zip(documents, metadatas, distances):
            hits.append(
                {
                    "text": document,
                    "metadata": metadata or {},
                    "score": round(1 - distance, 4),
                }
            )
        return hits

    def get_context_for_transcript(
        self,
        transcript: str,
        series_id: str | None = None,
        use_rag: bool = False,
        top_k: int = 5,
        exclude_meeting_id: str | None = None,
    ) -> tuple[str, list[str]]:
        if not use_rag or not series_id:
            return "", []

        hits = self.retrieve(transcript[:1000], top_k=top_k, series_id=series_id)
        if exclude_meeting_id:
            hits = [h for h in hits if h["metadata"].get("meeting_id") != exclude_meeting_id]
        if not hits:
            return "", []

        context_lines = [f"Relevant context from previous meetings in series '{series_id}':"]
        summaries = []

        for hit in hits:
            metadata = hit["metadata"]
            chunk_type = metadata.get("chunk_type", "transcript")
            timestamp = metadata.get("timestamp", "unknown time")
            line = f"[{chunk_type} | {timestamp}] {hit['text']}"
            context_lines.append(line)
            if chunk_type == "summary":
                summaries.append(hit["text"])

        return "\n".join(context_lines), summaries


def get_rag_service() -> MeetingRAGService:
    global _rag_service
    if _rag_service is None:
        _rag_service = MeetingRAGService()
    return _rag_service
