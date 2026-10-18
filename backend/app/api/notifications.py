import asyncio
from typing import List

from fastapi import APIRouter, Depends, HTTPException

from app.auth import get_current_user
from app.models import Notification, User
from app.services.firestore import db

router = APIRouter(prefix="/notifications", tags=["notifications"])


@router.get("", response_model=List[Notification])
async def list_notifications(limit: int = 30, current_user: User = Depends(get_current_user)):
    docs = await db.query("notifications", filters=[("recipientUid", "==", current_user.uid)])
    docs.sort(key=lambda d: d.get("createdAt", ""), reverse=True)
    return [Notification(**d) for d in docs[:limit]]


@router.post("/{notification_id}/read", response_model=Notification)
async def mark_read(notification_id: str, current_user: User = Depends(get_current_user)):
    doc = await db.get("notifications", notification_id)
    if not doc or doc.get("recipientUid") != current_user.uid:
        raise HTTPException(status_code=404, detail="Notification not found")
    doc["read"] = True
    saved = await db.set("notifications", notification_id, doc)
    return Notification(**saved)


@router.post("/read-all")
async def mark_all_read(current_user: User = Depends(get_current_user)):
    docs = await db.query("notifications", filters=[("recipientUid", "==", current_user.uid)])
    unread = [d for d in docs if not d.get("read")]
    await asyncio.gather(*[db.update("notifications", d["id"], {"read": True}) for d in unread])
    return {"marked": len(unread)}
