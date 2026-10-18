import math
import hashlib
import logging
from typing import List, Dict, Any, Optional, Tuple
import numpy as np

from app.config import settings

logger = logging.getLogger("assesscraft.similarity")

_llm_client = None
# 90s timeout, 3 attempts with backoff on transient errors (429/5xx).
_HTTP_OPTS = {"timeout": 90_000, "retry_options": {"attempts": 3}}
# text-embedding-004 was retired 2026-01-14. 768 dims keeps vectors the same shape as the local fallback.
EMBED_MODEL = "gemini-embedding-001"
_EMBED_CONFIG = {"output_dimensionality": 768}


def llm_configured() -> bool:
    """True when the settings contain enough to attempt a real LLM connection."""
    if settings.LLM_BACKEND == "openrouter":
        return bool(settings.LLM_API_KEY)
    return bool(settings.GCP_PROJECT_ID)


class _OpenRouterModels:
    """Answers the google-genai `client.models` calls the agents make, via OpenRouter's OpenAI-compatible API."""
    URL = "https://openrouter.ai/api/v1"
    # Same embedding model as the Gemini backends, so vectors already stored stay comparable.
    EMBED_MODEL = "google/gemini-embedding-001"

    def __init__(self, api_key: str):
        import httpx
        self._http = httpx.Client(base_url=self.URL, timeout=90, headers={"Authorization": f"Bearer {api_key}", "X-Title": settings.APP_NAME})

    def _post(self, path: str, body: Dict[str, Any]) -> Dict[str, Any]:
        import time
        for attempt in range(3):
            r = self._http.post(path, json=body)
            if r.status_code != 429 and r.status_code < 500 or attempt == 2:
                break
            time.sleep(2 ** attempt)
        r.raise_for_status()
        data = r.json()
        if "error" in data:
            raise RuntimeError(f"OpenRouter error: {data['error']}")
        return data

    def generate_content(self, model: str, contents: str, config: Optional[Dict[str, Any]] = None):
        from types import SimpleNamespace
        config = config or {}
        body: Dict[str, Any] = {"model": model, "messages": [{"role": "user", "content": contents}]}
        if "thinking_config" in config:
            body["reasoning"] = {"enabled": config["thinking_config"].get("thinking_budget") != 0}
        if "temperature" in config:
            body["temperature"] = config["temperature"]
        if "max_output_tokens" in config:
            body["max_tokens"] = config["max_output_tokens"]
        schema = config.get("response_schema")
        if schema is not None:
            body["response_format"] = {"type": "json_schema", "json_schema": {"name": schema.__name__, "schema": schema.model_json_schema()}}
        elif config.get("response_mime_type") == "application/json":
            body["response_format"] = {"type": "json_object"}
        data = self._post("/chat/completions", body)
        return SimpleNamespace(text=data["choices"][0]["message"].get("content") or "")

    def embed_content(self, model: str, contents, config: Optional[Dict[str, Any]] = None):
        from types import SimpleNamespace
        body = {"model": self.EMBED_MODEL, "input": contents, "dimensions": (config or {}).get("output_dimensionality", 768)}
        data = self._post("/embeddings", body)
        rows = sorted(data["data"], key=lambda d: d["index"])
        return SimpleNamespace(embeddings=[SimpleNamespace(values=d["embedding"]) for d in rows])


def get_llm_client():
    """Returns an LLM client (google-genai, or an OpenRouter adapter with the same interface) for the configured backend, or None when not configured."""
    global _llm_client
    if _llm_client is None and llm_configured():
        try:
            if settings.LLM_BACKEND == "openrouter":
                from types import SimpleNamespace
                _llm_client = SimpleNamespace(models=_OpenRouterModels(settings.LLM_API_KEY))
                return _llm_client
            from google import genai
            _llm_client = genai.Client(
                vertexai=True,
                project=settings.GCP_PROJECT_ID,
                location=settings.GCP_REGION,
                http_options=_HTTP_OPTS,
            )
        except Exception as e:
            logger.warning(f"Could not initialize LLM client ({settings.LLM_BACKEND}): {e}. Using local embedding fallback.")
            _llm_client = None
    return _llm_client


def check_llm() -> Dict[str, Any]:
    """Makes one tiny live generate + embed call. Used by /health/deep, startup (STRICT_MODE) and scripts."""
    client = get_llm_client()
    result: Dict[str, Any] = {"backend": settings.LLM_BACKEND, "model": settings.LLM_MODEL, "ok": False}
    if not client:
        result["error"] = "LLM client not configured"
        return result
    try:
        resp = client.models.generate_content(
            model=settings.LLM_MODEL,
            contents="Reply with the single word: ok",
            config={"thinking_config": {"thinking_budget": 0}, "max_output_tokens": 5},
        )
        result["generate"] = bool((resp.text or "").strip())
        emb = client.models.embed_content(model=EMBED_MODEL, contents="ok", config=_EMBED_CONFIG)
        result["embed"] = bool(getattr(emb, "embeddings", None))
        result["ok"] = result["generate"] and result["embed"]
    except Exception as e:
        result["error"] = f"{type(e).__name__}: {e}"
    return result


def require_llm_or_fallback(what: str) -> None:
    """Called where an agent is about to substitute canned content for an LLM result."""
    if settings.STRICT_MODE:
        raise RuntimeError(f"{what}: LLM unavailable and STRICT_MODE forbids fallback content")


def _stable_bucket(token: str, dim: int) -> int:
    """Process-independent hash (Python's built-in hash() is salted per process)."""
    return int.from_bytes(hashlib.md5(token.encode("utf-8")).digest()[:8], "big") % dim


def compute_embedding(text: str) -> List[float]:
    """
    Computes text embedding vector using Vertex AI gemini-embedding-001 or local fallback.
    """
    client = get_llm_client()
    if client:
        try:
            response = client.models.embed_content(
                model=EMBED_MODEL,
                contents=text,
                config=_EMBED_CONFIG,
            )
            if hasattr(response, "embeddings") and response.embeddings:
                return response.embeddings[0].values
        except Exception as e:
            logger.warning(f"Vertex AI embedding failed ({e}). Falling back to deterministic embedding.")
        # Hash vectors and Gemini vectors are different spaces: mixing them silently zeroes every duplicate check.
        require_llm_or_fallback("Embedding")

    # Local deterministic semantic representation (768 dimensions)
    dim = 768
    vector = np.zeros(dim, dtype=np.float32)
    clean_text = text.lower().strip()
    words = [w.strip("?:.,!()") for w in clean_text.split() if len(w.strip("?:.,!()")) > 1]
    if not words:
        return vector.tolist()

    for idx, word in enumerate(words):
        vector[_stable_bucket(word, dim)] += 1.0
        # Bi-gram hashing
        if idx > 0:
            vector[_stable_bucket(f"{words[idx-1]}_{word}", dim)] += 1.5

    norm = np.linalg.norm(vector)
    if norm > 0:
        vector = vector / norm
    return vector.tolist()


def compute_embeddings(texts: List[str]) -> List[List[float]]:
    """Batch embedding: one API call for all texts; per-text fallback on failure."""
    client = get_llm_client()
    if client and texts:
        try:
            response = client.models.embed_content(model=EMBED_MODEL, contents=texts, config=_EMBED_CONFIG)
            if response.embeddings and len(response.embeddings) == len(texts):
                return [e.values for e in response.embeddings]
        except Exception as e:
            logger.warning(f"Batch embedding failed ({e}). Falling back to per-text embedding.")
    return [compute_embedding(t) for t in texts]


def cosine_similarity(v1: List[float], v2: List[float]) -> float:
    """Computes cosine similarity between two float vectors."""
    a = np.array(v1, dtype=np.float32)
    b = np.array(v2, dtype=np.float32)
    norm_a = np.linalg.norm(a)
    norm_b = np.linalg.norm(b)
    if norm_a == 0 or norm_b == 0:
        return 0.0
    return float(np.dot(a, b) / (norm_a * norm_b))


def find_similar_items(
    target_text: str,
    target_embedding: Optional[List[float]],
    candidates: List[Dict[str, Any]],
    threshold: Optional[float] = None,
) -> List[Tuple[Dict[str, Any], float]]:
    """
    Scans candidates against target_text and target_embedding.
    Returns list of (candidate, score) pairs where score >= threshold.
    """
    threshold = settings.DUPLICATE_THRESHOLD if threshold is None else threshold
    emb = target_embedding or compute_embedding(target_text)
    matches = []

    for item in candidates:
        cand_emb = item.get("embedding")
        if not cand_emb:
            cand_text = item.get("text") or item.get("stem") or ""
            cand_emb = compute_embedding(cand_text)

        sim = cosine_similarity(emb, cand_emb)
        if sim >= threshold:
            matches.append((item, round(sim, 4)))

    matches.sort(key=lambda x: x[1], reverse=True)
    return matches
