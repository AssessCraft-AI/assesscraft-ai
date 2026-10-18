"""
Live LLM connectivity check for the configured backend (LLM_BACKEND=openrouter|vertex).
Exits non-zero on failure so it can gate a deploy or CI job.

    GCP_PROJECT_ID=my-proj python scripts/check_llm.py
    LLM_API_KEY=... python scripts/check_llm.py
"""
import json
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.tools.similarity import check_llm

result = check_llm()
print(json.dumps(result, indent=2))
sys.exit(0 if result["ok"] else 1)
