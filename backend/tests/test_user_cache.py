import asyncio

from app.services.firestore import FirestoreService


class _Doc:
    def __init__(self, store, key):
        self.store, self.key = store, key

    def get(self):
        self.store["reads"] += 1
        data = self.store["docs"].get(self.key)
        return type("Snap", (), {"exists": data is not None, "id": self.key, "to_dict": lambda _s: dict(data)})()

    def set(self, data):
        self.store["docs"][self.key] = dict(data)


class _FakeClient:
    def __init__(self):
        self.store = {"reads": 0, "docs": {}}

    def collection(self, name):
        return type("Col", (), {"document": lambda _s, doc_id: _Doc(self.store, (name, doc_id))})()


def test_user_record_is_cached_and_cleared_on_write():
    svc = FirestoreService.__new__(FirestoreService)
    svc._user_cache, svc._client = {}, _FakeClient()
    svc._client.store["docs"][("users", "u1")] = {"role": "lecturer"}

    async def run():
        first = await svc.get_user_record("u1")
        second = await svc.get_user_record("u1")
        assert first["role"] == second["role"] == "lecturer"
        assert svc._client.store["reads"] == 1  # second lookup served from cache
        second["role"] = "admin"  # callers get copies, never the cached dict
        assert (await svc.get_user_record("u1"))["role"] == "lecturer"

        await svc.set("users", "u1", {"role": "moderator", "disabled": True})
        third = await svc.get_user_record("u1")
        assert third["role"] == "moderator" and third["disabled"] is True
        assert svc._client.store["reads"] == 2

    asyncio.run(run())
