from typing import Optional, Dict, Any
from app.services.firestore import db
from app.models import AuditEntry, generate_id, current_time_iso


async def log_audit(
    actor_uid: str,
    action: str,
    entity: str,
    entity_id: str,
    before: Optional[Dict[str, Any]] = None,
    after: Optional[Dict[str, Any]] = None,
) -> AuditEntry:
    entry = AuditEntry(
        id=generate_id(),
        actorUid=actor_uid,
        action=action,
        entity=entity,
        entityId=entity_id,
        before=before,
        after=after,
        at=current_time_iso(),
    )
    await db.set("audit", entry.id, entry.model_dump())
    return entry
