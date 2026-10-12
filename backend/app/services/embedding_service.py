"""
Embedding service using sentence-transformers (all-MiniLM-L6-v2).
Produces 384-dimensional vectors for semantic similarity matching.
"""
from __future__ import annotations

import structlog
from functools import lru_cache
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from sentence_transformers import SentenceTransformer

logger = structlog.get_logger()


@lru_cache(maxsize=1)
def _load_model() -> "SentenceTransformer":
    from sentence_transformers import SentenceTransformer
    from app.config import settings

    logger.info("Loading embedding model", model=settings.EMBEDDING_MODEL)
    model = SentenceTransformer(settings.EMBEDDING_MODEL)
    logger.info("Embedding model loaded")
    return model


class EmbeddingService:
    """Singleton wrapper around a sentence-transformer model."""

    def __init__(self):
        self._model = None

    @property
    def model(self) -> "SentenceTransformer":
        if self._model is None:
            self._model = _load_model()
        return self._model

    def embed(self, text: str) -> list[float]:
        """Return a 384-dim embedding for the given text."""
        vector = self.model.encode(text, convert_to_numpy=True)
        return vector.tolist()  # type: ignore[return-value]

    def embed_batch(self, texts: list[str]) -> list[list[float]]:
        """Return embeddings for a batch of texts."""
        vectors = self.model.encode(texts, convert_to_numpy=True, batch_size=32)
        return [v.tolist() for v in vectors]

    def embed_resume(self, parsed_data: dict) -> dict[str, list[float]]:
        """Generate three vectors for a parsed resume."""
        experience_text = " ".join(
            f"{e.get('title', '')} at {e.get('company', '')}: {e.get('description', '')} "
            + " ".join(e.get("achievements", []))
            for e in parsed_data.get("experience", [])
        )
        skills_text = " ".join(parsed_data.get("all_skills", []))
        full_text = f"{skills_text}\n{experience_text}"

        return {
            "experience_vector": self.embed(experience_text),
            "skills_vector": self.embed(skills_text),
            "full_profile_vector": self.embed(full_text),
        }

    def embed_jd(self, parsed_jd: dict) -> dict[str, list[float]]:
        """Generate vectors for a parsed job description."""
        requirements_text = " ".join(
            s.get("skill", "") for s in parsed_jd.get("required_skills", [])
        )
        full_text = f"{requirements_text}\n{parsed_jd.get('job_description_full', '')}"
        return {
            "requirements_vector": self.embed(requirements_text),
            "full_jd_vector": self.embed(full_text),
        }


embedding_service = EmbeddingService()
