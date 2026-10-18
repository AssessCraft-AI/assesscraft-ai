import os
from pathlib import Path
from typing import List
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )

    APP_NAME: str = "assesscraft"
    GCP_PROJECT_ID: str = ""
    GCP_REGION: str = "asia-southeast1"
    DOCAI_REGION: str = "us"
    # LLM connection: "openrouter" (OpenRouter, uses LLM_API_KEY) or "vertex" (Vertex AI, uses
    # ADC / the Cloud Run service account).
    LLM_BACKEND: str = "openrouter"
    LLM_API_KEY: str = ""
    LLM_MODEL: str = "google/gemini-3.1-flash-lite"
    REVIEWER_MODEL: str = "google/gemini-3.1-flash-lite"
    VERTEX_SEARCH_LOC: str = "global"
    SEARCH_DATASTORE_ID: str = ""  # empty = local Firestore search; set once a Vertex AI Search datastore exists
    DOCAI_PROCESSOR_ID: str = ""
    BUCKET: str = ""
    BQ_DATASET: str = "assesscraft"
    AGENT_RUNTIME: str = "local"  # "local" | "agent_engine"
    AGENT_ENGINE_ID: str = ""
    FIREBASE_PROJECT_ID: str = ""
    # Service account key JSON (relative to backend/ or absolute). Empty = ADC (Cloud Run).
    FIREBASE_CREDENTIALS: str = ""
    # Demo accounts / header bypass. OFF by default; enable only for local dev and tests.
    ENABLE_DEMO_AUTH: bool = False
    # Optional comma-separated allow-list of email domains for Firebase sign-in (empty = any).
    ALLOWED_EMAIL_DOMAINS: str = ""
    # Role given to a Firebase user that has no role claim / users/{uid} record. Never elevated by email.
    # Empty = such users are refused, so an open Firebase sign-up does not hand out lecturer access.
    DEFAULT_ROLE: str = ""
    # Run the demo seed (including a full agent pipeline) on startup. Local convenience only.
    SEED_ON_STARTUP: bool = True
    # Production guard: no silent fallbacks. Startup fails unless the LLM and Firestore are really
    # connected, agents raise instead of substituting canned content, and offline heuristics are off.
    STRICT_MODE: bool = False
    # Reviewer: when the LLM is unavailable, fall back to a clearly-labelled offline heuristic.
    OFFLINE_HEURISTICS: bool = True
    # Cosine similarity at/above which two items are near-duplicates (Build Prompt §5.4).
    DUPLICATE_THRESHOLD: float = 0.88
    # Jaccard word overlap at/above which a Vertex AI Search past-paper hit is a lexical duplicate.
    LEXICAL_DUPLICATE_THRESHOLD: float = 0.6
    CORS_ORIGINS: List[str] = ["*"]


settings = Settings()
if settings.FIREBASE_CREDENTIALS:
    _cred = Path(settings.FIREBASE_CREDENTIALS)
    if not _cred.is_absolute():
        _cred = Path(__file__).resolve().parent.parent / _cred
    settings.FIREBASE_CREDENTIALS = str(_cred)
    # Lets every Google client (Firestore, Storage, ...) pick up the same key via ADC.
    os.environ.setdefault("GOOGLE_APPLICATION_CREDENTIALS", settings.FIREBASE_CREDENTIALS)
if settings.STRICT_MODE:
    settings.OFFLINE_HEURISTICS = False
