import pytest


@pytest.fixture(autouse=True)
def _clear_default_retriever_cache() -> None:
    """Reset the process-lifetime retriever cache between tests.

    app/rag/retrieval.py's _cached_default_retriever persists for the whole
    process by design (production never rebuilds it mid-request), but that
    would leak a stale retriever across tests that exercise the default
    (env-resolved) knowledge_dir/storage_dir/collection_name path with
    different monkeypatched env vars.
    """

    from app.rag.retrieval import _cached_default_retriever

    yield
    _cached_default_retriever.cache_clear()
