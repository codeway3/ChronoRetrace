
import pytest
from fastapi_cache import FastAPICache
from fastapi_cache.backends.inmemory import InMemoryBackend

@pytest.fixture(autouse=True, scope="session")
def init_cache():
    """
    Fixture to initialize the cache with an in-memory backend for all tests.
    """
    FastAPICache.init(backend=InMemoryBackend(), prefix="fastapi-cache-test")
