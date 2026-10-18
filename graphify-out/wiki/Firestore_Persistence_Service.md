# Firestore Persistence Service

> 11 nodes · cohesion 0.29

## Key Concepts

- **FirestoreService** (9 connections) — `backend/app/services/firestore.py`
- **.update()** (4 connections) — `backend/app/services/firestore.py`
- **Any** (4 connections)
- **.get()** (3 connections) — `backend/app/services/firestore.py`
- **.query()** (3 connections) — `backend/app/services/firestore.py`
- **.set()** (3 connections) — `backend/app/services/firestore.py`
- **.__init__()** (2 connections) — `backend/app/services/firestore.py`
- **._init_client()** (2 connections) — `backend/app/services/firestore.py`
- **.delete()** (1 connections) — `backend/app/services/firestore.py`
- **.is_cloud()** (1 connections) — `backend/app/services/firestore.py`
- **Query documents in a collection. filters: list of (field, op, value) e.g.…** (1 connections) — `backend/app/services/firestore.py`

## Relationships

- [Backend API & Analytics](Backend_API_&_Analytics.md) (1 shared connections)

## Source Files

- `backend/app/services/firestore.py`

## Audit Trail

- EXTRACTED: 17 (100%)
- INFERRED: 0 (0%)
- AMBIGUOUS: 0 (0%)

---

*Part of the graphify knowledge wiki. See [index](index.md) to navigate.*