import json
import os
from datetime import datetime

from .chunker import chunk_transcript
from .embeddings import embed_query, embed_texts
from .vector_store import VectorStore

_rag_service = None
LEGACY_SERIES_ID = "legacy-unscoped"


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
        if self.store.meeting_exists(meeting_id):
            return 0

        timestamp = timestamp or datetime.now().isoformat()
        series_id = series_id or LEGACY_SERIES_ID
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
    ) -> tuple[str, list[str]]:
        if not use_rag or not series_id:
            return "", []

        hits = self.retrieve(transcript[:1000], top_k=top_k, series_id=series_id)
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

    def answer_question(self, question: str, top_k: int = 5, series_id: str | None = None) -> dict:
        hits = self.retrieve(question, top_k=top_k, series_id=series_id)
        if not hits:
            return {
                "question": question,
                "answer": "No meeting history found for this series yet.",
                "sources": [],
                "series_id": series_id,
            }

        context = "\n\n".join(
            f"Source ({hit['metadata'].get('chunk_type', 'unknown')}): {hit['text']}" for hit in hits
        )
        return {
            "question": question,
            "context": context,
            "sources": hits,
            "series_id": series_id,
        }

    def migrate_from_json_history(self, history_file: str) -> int:
        if not os.path.exists(history_file):
            return 0

        with open(history_file, "r", encoding="utf-8") as file:
            try:
                history = json.load(file)
            except json.JSONDecodeError:
                return 0

        indexed_chunks = 0
        for index, item in enumerate(history):
            meeting_id = item.get("timestamp") or f"legacy_meeting_{index}"
            transcript = item.get("transcript") or item.get("summary") or ""
            summary = item.get("summary") or ""
            action_items = item.get("action_items") or []
            indexed_chunks += self.index_meeting(
                meeting_id=meeting_id,
                transcript=transcript,
                summary=summary,
                action_items=action_items,
                timestamp=item.get("timestamp"),
                mode=item.get("mode", "standalone"),
                series_id=item.get("series_id", LEGACY_SERIES_ID),
            )
        return indexed_chunks

    def get_stats(self, series_id: str | None = None) -> dict:
        return {
            "total_chunks": self.store.count_for_series(series_id),
            "series_ids": self.store.list_series_ids(),
            "meeting_ids": self.store.list_meeting_ids(series_id),
            "filtered_series_id": series_id,
        }


def get_rag_service() -> MeetingRAGService:
    global _rag_service
    if _rag_service is None:
        _rag_service = MeetingRAGService()
    return _rag_service
