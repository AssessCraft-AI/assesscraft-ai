"""Regression tests for the audit's must-fix findings: blueprint trust, pool re-draft, strict embeddings, re-review."""
import pytest
from httpx import AsyncClient, ASGITransport

from app.agents.item_writer import run_item_writer_agent
from app.agents.reviewer import run_reviewer_agent
from app.config import settings
from app.main import app
from app.services.firestore import db
from app.tools import similarity
from seed.load_seed import seed_database

LECTURER = {"X-Demo-Role": "lecturer"}  # owns CS2040 and asm-demo


@pytest.fixture(autouse=True)
async def setup():
    await seed_database()


def client():
    return AsyncClient(transport=ASGITransport(app=app), base_url="http://test")


def _cell(**kw):
    return {"cloId": "CLO1", "topicId": "t1", "bloom": "apply", "qType": "mcq", "count": 50, "marksEach": 2, **kw}


async def _of(collection):
    return await db.query(collection, filters=[("assessmentId", "==", "asm-demo")])


async def test_blueprint_put_recomputes_validity_on_the_server():
    # 100 marks, but only CLO1: the browser's total-marks check would call this valid.
    body = {"assessmentId": "asm-demo", "cells": [_cell()], "valid": True, "violations": []}
    async with client() as c:
        resp = await c.put("/assessments/asm-demo/blueprint", headers=LECTURER, json=body)
        assert resp.status_code == 200
        assert resp.json()["valid"] is False
        assert any("CLO2" in v for v in resp.json()["violations"])

        too_big = {**body, "cells": [_cell(count=100000)]}
        assert (await c.put("/assessments/asm-demo/blueprint", headers=LECTURER, json=too_big)).status_code == 422


async def test_redraft_replaces_the_pool():
    first = {d["id"] for d in await _of("items")}
    assert first
    new = await run_item_writer_agent("asm-demo", run_id="run-demo")
    assert {d["id"] for d in await _of("items")} == {i.id for i in new}
    assert not await _of("versions") and not await _of("flags")


async def test_rerun_review_keeps_examiner_decisions():
    flags = await _of("flags")
    assert flags, "seed should raise at least one flag"
    kept = flags[0]
    await db.update("flags", kept["id"], {"resolution": "dismissed", "resolvedBy": "lecturer@demo"})

    await run_reviewer_agent("asm-demo", run_id="run-demo")

    again = [f for f in await _of("flags") if (f["itemId"], f["type"]) == (kept["itemId"], kept["type"])]
    assert again and again[0]["resolution"] == "dismissed"


def test_strict_mode_never_mixes_hash_embeddings(monkeypatch):
    class Broken:
        class models:
            @staticmethod
            def embed_content(**_):
                raise RuntimeError("429 quota")

    monkeypatch.setattr(similarity, "get_llm_client", lambda: Broken)
    monkeypatch.setattr(settings, "STRICT_MODE", True)
    with pytest.raises(RuntimeError, match="STRICT_MODE"):
        similarity.compute_embedding("What is BCNF?")
    with pytest.raises(RuntimeError, match="STRICT_MODE"):
        similarity.compute_embeddings(["a", "b"])
