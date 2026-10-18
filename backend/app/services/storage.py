"""
Cloud Storage helpers (Build Prompt §10): private objects, downloads via short-lived signed URLs.

Everything here is a no-op returning ``None`` when no bucket / GCP project is configured, so local
development keeps working and callers fall back to streaming bytes directly.
"""
import asyncio
import logging
from datetime import timedelta
from typing import Optional

from app.config import settings

logger = logging.getLogger("assesscraft.storage")

SIGNED_URL_TTL_MINUTES = 15
_bucket = None


def is_configured() -> bool:
    return bool(settings.BUCKET and settings.GCP_PROJECT_ID)


def _get_bucket():
    global _bucket
    if _bucket is None and is_configured():
        try:
            from google.cloud import storage

            _bucket = storage.Client(project=settings.GCP_PROJECT_ID).bucket(settings.BUCKET)
        except Exception as e:
            logger.warning(f"Cloud Storage unavailable ({e}); continuing without GCS.")
    return _bucket


def _upload_sync(path: str, data: bytes, content_type: str) -> Optional[str]:
    bucket = _get_bucket()
    if bucket is None:
        return None
    blob = bucket.blob(path)
    blob.upload_from_string(data, content_type=content_type)  # objects stay private (uniform ACL)
    return f"gs://{bucket.name}/{path}"


def _sign_sync(path: str, filename: str, content_type: str) -> Optional[str]:
    bucket = _get_bucket()
    if bucket is None:
        return None
    import google.auth
    from google.auth.transport.requests import Request

    credentials, _ = google.auth.default()
    credentials.refresh(Request())
    return bucket.blob(path).generate_signed_url(
        version="v4",
        expiration=timedelta(minutes=SIGNED_URL_TTL_MINUTES),
        method="GET",
        service_account_email=getattr(credentials, "service_account_email", None),
        access_token=credentials.token,
        response_disposition=f'attachment; filename="{filename}"',
        response_type=content_type,
    )


async def upload_bytes(path: str, data: bytes, content_type: str = "application/octet-stream") -> Optional[str]:
    """Uploads to the private bucket; returns the gs:// URI, or None if storage is unavailable."""
    try:
        return await asyncio.to_thread(_upload_sync, path, data, content_type)
    except Exception as e:
        logger.warning(f"GCS upload of {path} failed ({e}).")
        return None


async def upload_and_sign(path: str, data: bytes, filename: str, content_type: str) -> Optional[str]:
    """Uploads ``data`` and returns a short-lived signed download URL, or None on any failure."""
    if await upload_bytes(path, data, content_type) is None:
        return None
    try:
        return await asyncio.to_thread(_sign_sync, path, filename, content_type)
    except Exception as e:
        logger.warning(f"Signing URL for {path} failed ({e}); falling back to direct download.")
        return None
