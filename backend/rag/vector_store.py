import os

import chromadb

COLLECTION_NAME = "meeting_memory"


class VectorStore:
    def __init__(self, persist_directory: str | None = None):
        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        self.persist_directory = persist_directory or os.path.join(base_dir, "chroma_data")
        os.makedirs(self.persist_directory, exist_ok=True)

        self.client = chromadb.PersistentClient(path=self.persist_directory)
        self.collection = self.client.get_or_create_collection(
            name=COLLECTION_NAME,
            metadata={"hnsw:space": "cosine"},
        )

    def add_documents(
        self,
        ids: list[str],
        documents: list[str],
        embeddings: list[list[float]],
        metadatas: list[dict],
    ) -> None:
        if not ids:
            return
        self.collection.add(
            ids=ids,
            documents=documents,
            embeddings=embeddings,
            metadatas=metadatas,
        )

    def query(
        self,
        query_embedding: list[float],
        top_k: int = 5,
        where: dict | None = None,
    ) -> dict:
        kwargs = {
            "query_embeddings": [query_embedding],
            "n_results": top_k,
            "include": ["documents", "metadatas", "distances"],
        }
        if where:
            kwargs["where"] = where
        return self.collection.query(**kwargs)

    def meeting_exists(self, meeting_id: str) -> bool:
        result = self.collection.get(where={"meeting_id": meeting_id}, include=[])
        return bool(result.get("ids"))

    def count(self) -> int:
        return self.collection.count()

    def count_for_series(self, series_id: str | None = None) -> int:
        if not series_id:
            return self.count()
        result = self.collection.get(where={"series_id": series_id}, include=[])
        return len(result.get("ids", []))

    def list_meeting_ids(self, series_id: str | None = None) -> list[str]:
        kwargs = {"include": ["metadatas"]}
        if series_id:
            kwargs["where"] = {"series_id": series_id}
        result = self.collection.get(**kwargs)
        meeting_ids = set()
        for metadata in result.get("metadatas", []):
            if metadata and metadata.get("meeting_id"):
                meeting_ids.add(metadata["meeting_id"])
        return sorted(meeting_ids)

    def list_series_ids(self) -> list[str]:
        result = self.collection.get(include=["metadatas"])
        series_ids = set()
        for metadata in result.get("metadatas", []):
            if metadata and metadata.get("series_id"):
                series_ids.add(metadata["series_id"])
        return sorted(series_ids)
