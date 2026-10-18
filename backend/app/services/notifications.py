from typing import Optional

from app.models import Notification
from app.services.firestore import db


async def notify(
    recipient_uid: Optional[str],
    type: str,
    title: str,
    message: str,
    assessment_id: Optional[str] = None,
    actor_name: Optional[str] = None,
) -> Optional[Notification]:
    """Stores an in-app notification for one user. A missing recipient is a no-op."""
    if not recipient_uid:
        return None
    note = Notification(
        recipientUid=recipient_uid,
        type=type,
        title=title,
        message=message,
        assessmentId=assessment_id,
        actorName=actor_name,
    )
    await db.set("notifications", note.id, note.model_dump())
    return note
