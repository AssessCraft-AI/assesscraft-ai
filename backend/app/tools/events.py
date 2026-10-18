from typing import Optional, Dict, Any
import json
import asyncio
from google.cloud import bigquery
from app.config import settings
from app.models import generate_id, current_time_iso

# In-memory buffer for local testing & analytics fallback
_EVENTS_BUFFER: list[dict] = []

_bq_client: Optional[bigquery.Client] = None


def get_bq_client() -> Optional[bigquery.Client]:
    global _bq_client
    if _bq_client is None and settings.GCP_PROJECT_ID:
        try:
            _bq_client = bigquery.Client(project=settings.GCP_PROJECT_ID)
        except Exception as e:
            print(f"[BigQueryEvents] Client initialization skipped ({e})")
            _bq_client = None
    return _bq_client


async def log_event(
    event_type: str,
    user_role: Optional[str] = None,
    assessment_id: Optional[str] = None,
    stage: Optional[str] = None,
    flag_type: Optional[str] = None,
    resolution: Optional[str] = None,
    duration_ms: Optional[int] = None,
    meta: Optional[Dict[str, Any]] = None,
):
    """
    Emits a structured telemetry event to BigQuery and in-memory buffer.
    Fire-and-forget: does not block the caller or raise errors if offline.
    """
    event = {
        "event_id": generate_id(),
        "ts": current_time_iso(),
        "user_role": user_role or "system",
        "assessment_id": assessment_id,
        "stage": stage,
        "event_type": event_type,
        "flag_type": flag_type,
        "resolution": resolution,
        "duration_ms": duration_ms,
        "meta": meta or {},
    }

    _EVENTS_BUFFER.append(event)
    del _EVENTS_BUFFER[:-1000]  # cap: BigQuery holds the full history; this only feeds the analytics page

    # Fire-and-forget write to BigQuery if client is available
    client = get_bq_client()
    if client and settings.GCP_PROJECT_ID:
        table_id = f"{settings.GCP_PROJECT_ID}.{settings.BQ_DATASET}.events"
        bq_row = {
            "event_id": event["event_id"],
            "ts": event["ts"],
            "user_role": event["user_role"],
            "assessment_id": event["assessment_id"],
            "stage": event["stage"],
            "event_type": event["event_type"],
            "flag_type": event["flag_type"],
            "resolution": event["resolution"],
            "duration_ms": event["duration_ms"],
            "meta": json.dumps(event["meta"]),
        }

        def _insert():
            try:
                client.insert_rows_json(table_id, [bq_row])
            except Exception as e:
                print(f"[BigQueryEvents] Failed to insert row into BigQuery: {e}")

        asyncio.get_event_loop().run_in_executor(None, _insert)


def get_all_events() -> list[dict]:
    return list(_EVENTS_BUFFER)
