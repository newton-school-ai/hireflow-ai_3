"""
Embedding Pipeline

Generates vector embeddings for job descriptions and user profile text
using a sentence-transformers model. Builds and persists a FAISS index
for fast semantic similarity search.
"""

import argparse
import json
import logging
import os
from typing import Any

import numpy as np

from src.config.database import SessionLocal
from src.config.settings import get_settings

logger = logging.getLogger(__name__)

# Lazy imports to speed up module load and enable test mocking
_model = None
_faiss = None


def _get_model():
    """Lazy-load the sentence-transformers model."""
    global _model
    if _model is None:
        from sentence_transformers import SentenceTransformer
        settings = get_settings()
        logger.info(f"Loading embedding model: {settings.embedding_model}")
        _model = SentenceTransformer(settings.embedding_model)
    return _model


def _get_faiss():
    """Lazy-load faiss."""
    global _faiss
    if _faiss is None:
        import faiss as faiss_lib
        _faiss = faiss_lib
    return _faiss


class EmbeddingPipeline:
    """
    Manages embedding generation and FAISS index operations.
    """

    def __init__(self, model=None):
        """
        Args:
            model: Optional pre-loaded SentenceTransformer model (used for testing).
        """
        self.settings = get_settings()
        self._model = model  # allow injection for tests
        self._index = None
        self._job_metadata: list[dict[str, Any]] = []

    def _model_instance(self):
        if self._model is not None:
            return self._model
        return _get_model()

    def embed_text(self, text: str) -> np.ndarray:
        """
        Embed a single string into a numpy vector.
        Handles empty/very short text gracefully by returning a zero vector.
        """
        if not text or not text.strip():
            # Return a zero vector of appropriate dimension
            model = self._model_instance()
            dim = model.get_sentence_embedding_dimension()
            return np.zeros(dim, dtype=np.float32)

        model = self._model_instance()
        vec = model.encode(text.strip(), convert_to_numpy=True)
        return vec.astype(np.float32)

    def embed_jobs_to_index(self) -> int:
        """
        Fetch all non-spam jobs from the database, embed their descriptions,
        build a FAISS index and save it to disk.

        Returns:
            Number of jobs embedded.
        """
        from src.models.job import Job

        db = SessionLocal()
        try:
            jobs = db.query(Job).filter(Job.is_spam == False).all()  # noqa: E712
            logger.info(f"Embedding {len(jobs)} non-spam jobs...")
            if not jobs:
                logger.warning("No non-spam jobs found in database.")
                return 0

            texts = []
            metadata = []
            for job in jobs:
                # Combine title + description for richer semantic content
                text = f"{job.title or ''} {job.description or ''}".strip()
                texts.append(text)
                metadata.append({
                    "id": job.id,
                    "role_title": job.title,
                    "company_name": job.company,
                    "location": job.location,
                    "url": job.url,
                    "listing_type": job.listing_type.value if job.listing_type else "job",
                })

            model = self._model_instance()
            embeddings = model.encode(texts, convert_to_numpy=True, show_progress_bar=True)
            embeddings = embeddings.astype(np.float32)

            # Build a flat L2 FAISS index
            faiss = _get_faiss()
            dim = embeddings.shape[1]
            index = faiss.IndexFlatIP(dim)  # Inner Product (cosine after normalisation)
            faiss.normalize_L2(embeddings)
            index.add(embeddings)

            # Persist index and metadata to disk
            self._save_index(index, metadata)
            self._index = index
            self._job_metadata = metadata

            logger.info(f"FAISS index built with {index.ntotal} vectors.")
            return len(jobs)
        finally:
            db.close()

    def _save_index(self, index, metadata: list[dict]) -> None:
        """Save FAISS index and job metadata JSON to the configured path."""
        faiss = _get_faiss()
        path = self.settings.faiss_index_path
        os.makedirs(path, exist_ok=True)
        faiss.write_index(index, os.path.join(path, "jobs.index"))
        with open(os.path.join(path, "jobs_metadata.json"), "w") as f:
            json.dump(metadata, f)
        logger.info(f"FAISS index saved to {path}/")

    def load_index(self) -> bool:
        """
        Load FAISS index and metadata from disk.

        Returns:
            True if loaded successfully, False if files not found.
        """
        faiss = _get_faiss()
        path = self.settings.faiss_index_path
        index_path = os.path.join(path, "jobs.index")
        meta_path = os.path.join(path, "jobs_metadata.json")

        if not os.path.exists(index_path) or not os.path.exists(meta_path):
            logger.warning(f"FAISS index not found at {path}/. Run --embed-jobs first.")
            return False

        self._index = faiss.read_index(index_path)
        with open(meta_path) as f:
            self._job_metadata = json.load(f)
        logger.info(f"Loaded FAISS index with {self._index.ntotal} vectors.")
        return True

    def search(self, text: str, top_k: int = 5) -> list[dict[str, Any]]:
        """
        Embed a query string and return the top-K most similar jobs.

        Args:
            text: Profile or query text to search with.
            top_k: Number of results to return.

        Returns:
            List of job metadata dicts with an added 'score' key.
        """
        if self._index is None:
            loaded = self.load_index()
            if not loaded:
                return []

        query_vec = self.embed_text(text)

        # Handle zero vector (empty input)
        if np.all(query_vec == 0):
            logger.warning("Empty query text — returning no results.")
            return []

        faiss = _get_faiss()
        query_vec = query_vec.reshape(1, -1).astype(np.float32)
        faiss.normalize_L2(query_vec)

        k = min(top_k, self._index.ntotal)
        scores, indices = self._index.search(query_vec, k)

        results = []
        for score, idx in zip(scores[0], indices[0]):
            if idx < 0:  # FAISS returns -1 for empty slots
                continue
            job = dict(self._job_metadata[idx])
            job["score"] = float(score)
            results.append(job)

        return results


def main():
    """CLI entry point."""
    parser = argparse.ArgumentParser(description="HireFlow Embedding Pipeline")
    parser.add_argument(
        "--embed-jobs",
        action="store_true",
        help="Embed all non-spam jobs and build FAISS index",
    )
    args = parser.parse_args()

    if args.embed_jobs:
        pipeline = EmbeddingPipeline()
        count = pipeline.embed_jobs_to_index()
        print(f"\nDone. Embedded {count} jobs into the FAISS index.")
        settings = get_settings()
        print(f"Index saved to: {settings.faiss_index_path}/")
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
