import os

# Tests never touch paid or real cloud services, even when .env holds real keys:
# in-memory store, offline agent fallbacks, no LLM, Search, Document AI, Storage, Agent Engine or Firebase key.
for _var in ("GCP_PROJECT_ID", "LLM_API_KEY", "SEARCH_DATASTORE_ID", "DOCAI_PROCESSOR_ID", "BUCKET",
             "AGENT_ENGINE_ID", "FIREBASE_CREDENTIALS", "GOOGLE_APPLICATION_CREDENTIALS"):
    os.environ[_var] = ""
os.environ["LLM_BACKEND"] = "openrouter"  # with an empty key: the LLM is "not configured"

import pytest

from app.config import settings
from app.tools.similarity import llm_configured

assert not llm_configured(), "Tests must not reach the real LLM API"


@pytest.fixture(autouse=True, scope="session")
def _enable_demo_auth_for_tests():
    """Tests use the X-Demo-* headers; demo auth is OFF by default in app config."""
    original = settings.ENABLE_DEMO_AUTH
    settings.ENABLE_DEMO_AUTH = True
    yield
    settings.ENABLE_DEMO_AUTH = original
