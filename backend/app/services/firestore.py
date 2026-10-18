from typing import Dict, Any, List, Optional
import os
import asyncio
import time
import json
from google.cloud import firestore
from app.config import settings

# In-memory store fallback for offline / mock / test mode
_IN_MEMORY_STORE: Dict[str, Dict[str, Dict[str, Any]]] = {
    "users": {},
    "courses": {},
    "documents": {},
    "pastItems": {},
    "assessments": {},
    "blueprints": {},
    "items": {},
    "flags": {},
    "versions": {},
    "equivalenceReports": {},
    "moderation": {},
    "runs": {},
    "audit": {},
    "notifications": {},
}

# Seconds a users/{uid} record is reused for auth. Writes through this service clear it at once; other
# Cloud Run instances (or scripts writing Firestore directly) can see a role or disabled change this late.
USER_CACHE_TTL = 60


class FirestoreService:
    def __init__(self):
        self._client: Optional[firestore.Client] = None
        self._user_cache: Dict[str, tuple] = {}
        self._init_client()

    def _init_client(self):
        if settings.GCP_PROJECT_ID:
            try:
                self._client = firestore.Client(project=settings.GCP_PROJECT_ID)
            except Exception as e:
                print(f"[FirestoreService] Could not initialize cloud firestore client ({e}). Using in-memory fallback.")
                self._client = None
        else:
            self._client = None

    @property
    def is_cloud(self) -> bool:
        return self._client is not None

    # Cloud errors propagate: falling back to the (empty) in-memory store hid failed writes and
    # made a users/{uid} read error look like "no record", skipping the disabled-account check.
    async def get(self, collection: str, doc_id: str) -> Optional[Dict[str, Any]]:
        if self._client:
            doc = await asyncio.to_thread(self._client.collection(collection).document(doc_id).get)
            if not doc.exists:
                return None
            data = doc.to_dict()
            data["id"] = doc.id
            return data
        return _IN_MEMORY_STORE.get(collection, {}).get(doc_id)

    async def get_user_record(self, uid: str) -> Optional[Dict[str, Any]]:
        """users/{uid} for auth, cached briefly: every API request needs it, and each fetch is a billed read."""
        if not self._client:
            return await self.get("users", uid)
        hit = self._user_cache.get(uid)
        if hit and hit[0] > time.monotonic():
            return dict(hit[1]) if hit[1] else None
        record = await self.get("users", uid)
        self._user_cache[uid] = (time.monotonic() + USER_CACHE_TTL, record)
        return dict(record) if record else None

    def _forget(self, collection: str, doc_id: str) -> None:
        if collection == "users":
            self._user_cache.pop(doc_id, None)

    async def set(self, collection: str, doc_id: str, data: Dict[str, Any]) -> Dict[str, Any]:
        data["id"] = doc_id
        if self._client:
            await asyncio.to_thread(self._client.collection(collection).document(doc_id).set, data)
            self._forget(collection, doc_id)
            return data
        # In-memory store only when offline; mirroring every cloud write grew the instance's RAM without bound.
        _IN_MEMORY_STORE.setdefault(collection, {})[doc_id] = data
        return data

    async def update(self, collection: str, doc_id: str, updates: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Writes only the given fields, so concurrent updates to other fields are not lost."""
        existing = await self.get(collection, doc_id)
        if not existing:
            return None
        if self._client:
            await asyncio.to_thread(self._client.collection(collection).document(doc_id).update, updates)
            self._forget(collection, doc_id)
        existing.update(updates)
        if not self._client:
            _IN_MEMORY_STORE.setdefault(collection, {})[doc_id] = existing
        return existing

    async def append(self, collection: str, doc_id: str, field: str, value: Any) -> None:
        """Atomically appends to a list field (no read-modify-write, so parallel appends all land)."""
        if self._client:
            ref = self._client.collection(collection).document(doc_id)
            await asyncio.to_thread(ref.update, {field: firestore.ArrayUnion([value])})
            self._forget(collection, doc_id)
            return
        _IN_MEMORY_STORE[collection][doc_id].setdefault(field, []).append(value)

    async def delete(self, collection: str, doc_id: str) -> bool:
        if self._client:
            await asyncio.to_thread(self._client.collection(collection).document(doc_id).delete)
            self._forget(collection, doc_id)
            return True
        return _IN_MEMORY_STORE.get(collection, {}).pop(doc_id, None) is not None

    async def query(
        self,
        collection: str,
        filters: Optional[List[tuple]] = None,
        order_by: Optional[str] = None,
        limit: Optional[int] = None,
    ) -> List[Dict[str, Any]]:
        """
        Query documents in a collection.
        filters: list of (field, op, value) e.g. [("courseId", "==", "CS2040")]
        """
        if self._client:
            ref = self._client.collection(collection)
            for field, op, val in filters or []:
                ref = ref.where(field, op, val)
            if order_by:
                ref = ref.order_by(order_by)
            if limit:
                ref = ref.limit(limit)

            def _run():
                return [{**d.to_dict(), "id": d.id} for d in ref.stream()]

            return await asyncio.to_thread(_run)

        # In-memory query evaluation
        items = list(_IN_MEMORY_STORE.get(collection, {}).values())
        for field, op, val in filters or []:
            if op in ("==", "="):
                items = [it for it in items if it.get(field) == val]
            elif op == "in":
                items = [it for it in items if it.get(field) in val]
            else:
                raise ValueError(f"In-memory store does not support the '{op}' filter")
        if limit:
            items = items[:limit]
        return items

    # Defensive alias
    list = query


db = FirestoreService()
