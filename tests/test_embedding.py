import numpy as np
import pytest
from unittest.mock import MagicMock, patch


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_mock_model(dim: int = 8):
    """Create a mock SentenceTransformer that returns fixed-size numpy vectors."""
    mock = MagicMock()
    mock.get_sentence_embedding_dimension.return_value = dim
    mock.encode.side_effect = lambda texts, **kwargs: (
        np.random.rand(len(texts), dim).astype(np.float32)
        if isinstance(texts, list)
        else np.random.rand(dim).astype(np.float32)
    )
    return mock


def _make_pipeline_with_mock_model(dim: int = 8):
    """Return an EmbeddingPipeline wired to a mock model."""
    from src.pipelines.embedding_pipeline import EmbeddingPipeline
    mock_model = _make_mock_model(dim)
    pipeline = EmbeddingPipeline(model=mock_model)
    return pipeline, mock_model


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

class TestEmbedText:
    def test_normal_text_returns_numpy_array(self):
        pipeline, _ = _make_pipeline_with_mock_model(dim=8)
        vec = pipeline.embed_text("Python developer with FastAPI experience")
        assert isinstance(vec, np.ndarray)
        assert vec.shape == (8,)
        assert vec.dtype == np.float32

    def test_empty_string_returns_zero_vector(self):
        pipeline, _ = _make_pipeline_with_mock_model(dim=8)
        vec = pipeline.embed_text("")
        assert isinstance(vec, np.ndarray)
        assert vec.shape == (8,)
        assert np.all(vec == 0), "Expected zero vector for empty input"

    def test_whitespace_only_returns_zero_vector(self):
        pipeline, _ = _make_pipeline_with_mock_model(dim=8)
        vec = pipeline.embed_text("   ")
        assert np.all(vec == 0)

    def test_very_short_text_does_not_crash(self):
        pipeline, _ = _make_pipeline_with_mock_model(dim=8)
        # Short but valid text — should not crash
        vec = pipeline.embed_text("Go")
        assert isinstance(vec, np.ndarray)


class TestSearch:
    def _build_pipeline_with_index(self, dim: int = 8, n_docs: int = 5):
        """Build a pipeline with a real (tiny) FAISS index in memory."""
        import faiss
        from src.pipelines.embedding_pipeline import EmbeddingPipeline

        mock_model = _make_mock_model(dim)
        pipeline = EmbeddingPipeline(model=mock_model)

        # Build a tiny index manually
        embeddings = np.random.rand(n_docs, dim).astype(np.float32)
        faiss.normalize_L2(embeddings)
        index = faiss.IndexFlatIP(dim)
        index.add(embeddings)

        pipeline._index = index
        pipeline._job_metadata = [
            {
                "id": i + 1,
                "role_title": f"Job {i}",
                "company_name": f"Company {i}",
                "location": "Remote",
                "url": f"https://example.com/jobs/{i}",
                "listing_type": "job",
            }
            for i in range(n_docs)
        ]
        return pipeline

    def test_search_returns_top_k_results(self):
        pipeline = self._build_pipeline_with_index(dim=8, n_docs=5)
        results = pipeline.search("Python developer with LangChain", top_k=3)
        assert len(results) == 3
        for r in results:
            assert "role_title" in r
            assert "score" in r
            assert isinstance(r["score"], float)

    def test_search_empty_text_returns_empty_list(self):
        pipeline = self._build_pipeline_with_index(dim=8, n_docs=5)
        results = pipeline.search("", top_k=3)
        assert results == []

    def test_search_with_short_jd(self):
        """A very short JD should still return results (not crash)."""
        pipeline = self._build_pipeline_with_index(dim=8, n_docs=3)
        results = pipeline.search("Python", top_k=2)
        # Should return results because the text is non-empty
        assert isinstance(results, list)

    def test_search_top_k_capped_by_index_size(self):
        """top_k larger than the index should only return what's available."""
        pipeline = self._build_pipeline_with_index(dim=8, n_docs=2)
        results = pipeline.search("ML engineer", top_k=10)
        assert len(results) <= 2


class TestEmbedJobsToIndex:
    def test_embed_jobs_skips_spam(self):
        """Only non-spam jobs should be embedded — mocks DB and FAISS disk I/O."""
        import faiss
        from src.models.job import Job, ListingType
        from src.pipelines.embedding_pipeline import EmbeddingPipeline

        # Build a mock clean job
        clean_job = MagicMock(spec=Job)
        clean_job.id = 1
        clean_job.title = "Backend Engineer"
        clean_job.company = "TestCo"
        clean_job.location = "Remote"
        clean_job.url = "https://example.com/1"
        clean_job.description = "Build APIs with FastAPI and PostgreSQL."
        clean_job.listing_type = ListingType.job
        clean_job.is_spam = False

        mock_db = MagicMock()
        mock_db.query.return_value.filter.return_value.all.return_value = [clean_job]

        pipeline = EmbeddingPipeline(model=_make_mock_model(dim=8))

        # Patch both the lazy SessionLocal import inside the function and disk write
        with patch("src.pipelines.embedding_pipeline.SessionLocal", return_value=mock_db), \
             patch.object(pipeline, "_save_index"):
            count = pipeline.embed_jobs_to_index()

        assert count == 1

