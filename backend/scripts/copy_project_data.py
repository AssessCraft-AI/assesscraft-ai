"""
One-time copy of Firestore data and Firebase Auth users from one project to another.
Doc IDs and user UIDs are kept, so users/{uid} roles still match their accounts.
The source project is only read. Without --apply nothing is written (dry run).
--wipe first deletes ALL Firestore docs (and, unless --skip-auth, ALL Auth users) in the destination.

    python scripts/copy_project_data.py \
        --src-key assesscraft-c5473-firebase-adminsdk-fbsvc-320f2da3fd.json \
        --dest-project assesscraft-test-1012 \
        --hash-key <base64_signer_key> --salt-separator <base64_salt_separator> \
        --rounds 8 --mem-cost 14 [--wipe] [--apply]

Destination access uses Application Default Credentials (gcloud auth application-default login).
The scrypt values come from the SOURCE Firebase console: Authentication > Users > (menu) > Password hash parameters.
"""
import argparse
import base64

import firebase_admin
from firebase_admin import auth, credentials, firestore


def b64(value: str) -> bytes:
    """Accepts standard or URL-safe base64, with or without padding."""
    value = value.replace("-", "+").replace("_", "/")
    return base64.b64decode(value + "=" * (-len(value) % 4))


def copy_docs(src_db, dest_db, writer) -> int:
    """writer is a BulkWriter (it splits by the 10 MB request limit; items carry embeddings) or None for a dry run."""
    # shortcut: top-level collections only (the app writes no subcollections); listing them per doc costs a read each.
    count = 0
    for col in src_db.collections():
        for doc in col.stream():
            if writer:
                writer.set(dest_db.collection(col.id).document(doc.id), doc.to_dict())
            count += 1
    return count


def wipe_docs(db, apply: bool) -> int:
    count = 0
    for col in db.collections():
        for doc in col.stream():
            count += 1
            if apply:
                doc.reference.delete()
    return count


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--src-key", required=True, help="service account key JSON for the source project")
    p.add_argument("--dest-project", required=True)
    p.add_argument("--hash-key")
    p.add_argument("--salt-separator")
    p.add_argument("--rounds", type=int)
    p.add_argument("--mem-cost", type=int)
    p.add_argument("--skip-auth", action="store_true")
    p.add_argument("--wipe", action="store_true", help="delete existing destination data first")
    p.add_argument("--apply", action="store_true", help="write to the destination (default: dry run)")
    a = p.parse_args()

    src_app = firebase_admin.initialize_app(credentials.Certificate(a.src_key), name="src")
    dest_app = firebase_admin.initialize_app(credentials.ApplicationDefault(), {"projectId": a.dest_project}, name="dest")
    src_db, dest_db = firestore.client(src_app), firestore.client(dest_app)
    if src_app.project_id == a.dest_project:
        raise SystemExit("Source and destination are the same project")

    mode = "COPYING" if a.apply else "DRY RUN"
    print(f"{mode}: {src_app.project_id} -> {a.dest_project}")
    if a.wipe:
        print(f"Wipe Firestore: {wipe_docs(dest_db, a.apply)} destination docs {'deleted' if a.apply else 'would be deleted'}")
    writer = dest_db.bulk_writer() if a.apply else None
    n = copy_docs(src_db, dest_db, writer)
    if writer:
        writer.close()  # flushes and waits for every write
    print(f"Firestore: {n} docs {'written' if a.apply else 'would be written'}")

    if a.skip_auth:
        return
    users = list(auth.list_users(app=src_app).iterate_all())
    hashed = [u for u in users if u.password_hash]
    if hashed and None in (a.hash_key, a.salt_separator, a.rounds, a.mem_cost):
        raise SystemExit(f"{len(hashed)} users have passwords: pass --hash-key, --salt-separator, --rounds and --mem-cost "
                         "(source Firebase console > Authentication > Users > Password hash parameters), or --skip-auth")
    records = [
        auth.ImportUserRecord(
            uid=u.uid, email=u.email, email_verified=u.email_verified, display_name=u.display_name,
            phone_number=u.phone_number, photo_url=u.photo_url, disabled=u.disabled,
            custom_claims=u.custom_claims,
            password_hash=b64(u.password_hash) if u.password_hash else None,
            password_salt=b64(u.password_salt) if u.password_salt else None,
        )
        for u in users
    ]
    if a.wipe:
        old = [u.uid for u in auth.list_users(app=dest_app).iterate_all()]
        print(f"Wipe Auth: {len(old)} destination users {'deleted' if a.apply else 'would be deleted'}")
        if a.apply:
            for i in range(0, len(old), 1000):
                auth.delete_users(old[i:i + 1000], app=dest_app)
    print(f"Auth: {len(records)} users {'importing' if a.apply else 'would be imported'}")
    if not a.apply:
        return
    hash_alg = auth.UserImportHash.scrypt(
        key=b64(a.hash_key), salt_separator=b64(a.salt_separator), rounds=a.rounds, memory_cost=a.mem_cost
    ) if hashed else None
    for i in range(0, len(records), 1000):  # import_users takes at most 1000 per call
        result = auth.import_users(records[i:i + 1000], hash_alg=hash_alg, app=dest_app)
        for err in result.errors:
            print(f"  user {records[i + err.index].email}: {err.reason}")
        print(f"  imported {result.success_count}, failed {result.failure_count}")


if __name__ == "__main__":
    main()
