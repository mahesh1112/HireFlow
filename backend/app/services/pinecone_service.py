"""
Pinecone vector database integration.
Stores resume embeddings and enables semantic search against JD requirements.
"""
from __future__ import annotations

import structlog
from typing import Any
from functools import lru_cache

logger = structlog.get_logger()


@lru_cache(maxsize=1)
def _get_pinecone_index():
    from pinecone import Pinecone, ServerlessSpec
    from app.config import settings

    if not settings.PINECONE_API_KEY:
        logger.warning("Pinecone API key not configured — vector search disabled")
        return None

    pc = Pinecone(api_key=settings.PINECONE_API_KEY)

    # Create index if it doesn't exist
    existing = [idx.name for idx in pc.list_indexes()]
    if settings.PINECONE_INDEX_NAME not in existing:
        logger.info("Creating Pinecone index", name=settings.PINECONE_INDEX_NAME)
        pc.create_index(
            name=settings.PINECONE_INDEX_NAME,
            dimension=settings.EMBEDDING_DIM,
            metric="cosine",
            spec=ServerlessSpec(cloud="aws", region=settings.PINECONE_ENVIRONMENT),
        )

    return pc.Index(settings.PINECONE_INDEX_NAME)


class PineconeService:
    """Manages resume embeddings in Pinecone for semantic JD matching."""

    @property
    def index(self):
        return _get_pinecone_index()

    def upsert_resume(
        self,
        resume_id: str,
        vectors: dict[str, list[float]],
        metadata: dict[str, Any],
    ) -> str | None:
        """Store three vectors per resume. Returns the primary vector ID."""
        if not self.index:
            return None

        # Use the full_profile_vector as the primary searchable vector
        vector_id = f"resume_{resume_id}"
        self.index.upsert(
            vectors=[
                {
                    "id": vector_id,
                    "values": vectors["full_profile_vector"],
                    "metadata": {
                        **metadata,
                        "resume_id": resume_id,
                        "vector_type": "full_profile",
                    },
                },
                {
                    "id": f"{vector_id}_skills",
                    "values": vectors["skills_vector"],
                    "metadata": {
                        **metadata,
                        "resume_id": resume_id,
                        "vector_type": "skills",
                    },
                },
                {
                    "id": f"{vector_id}_exp",
                    "values": vectors["experience_vector"],
                    "metadata": {
                        **metadata,
                        "resume_id": resume_id,
                        "vector_type": "experience",
                    },
                },
            ]
        )
        return vector_id

    def search_by_jd(
        self,
        jd_vectors: dict[str, list[float]],
        top_k: int = 100,
        filters: dict | None = None,
    ) -> list[dict[str, Any]]:
        """
        Hybrid search: combine full-profile and skills similarity.
        Returns list of {resume_id, score, metadata}.
        """
        if not self.index:
            return []

        query_filter = filters or {}

        # Full-profile search
        profile_results = self.index.query(
            vector=jd_vectors["full_jd_vector"],
            top_k=top_k,
            filter={**query_filter, "vector_type": "full_profile"},
            include_metadata=True,
        )

        # Skills-focused search
        skills_results = self.index.query(
            vector=jd_vectors["requirements_vector"],
            top_k=top_k,
            filter={**query_filter, "vector_type": "skills"},
            include_metadata=True,
        )

        # Merge and average scores
        scores: dict[str, float] = {}
        metadata_map: dict[str, dict] = {}

        for match in profile_results.get("matches", []):
            rid = match["metadata"]["resume_id"]
            scores[rid] = match["score"] * 0.5
            metadata_map[rid] = match["metadata"]

        for match in skills_results.get("matches", []):
            rid = match["metadata"]["resume_id"]
            scores[rid] = scores.get(rid, 0) + match["score"] * 0.5
            if rid not in metadata_map:
                metadata_map[rid] = match["metadata"]

        ranked = sorted(scores.items(), key=lambda x: x[1], reverse=True)
        return [
            {"resume_id": rid, "similarity_score": score, "metadata": metadata_map[rid]}
            for rid, score in ranked
        ]

    def delete_resume(self, resume_id: str) -> None:
        if not self.index:
            return
        vector_id = f"resume_{resume_id}"
        self.index.delete(ids=[vector_id, f"{vector_id}_skills", f"{vector_id}_exp"])

    def get_index_stats(self) -> dict:
        if not self.index:
            return {"total_vector_count": 0}
        return self.index.describe_index_stats()


pinecone_service = PineconeService()
