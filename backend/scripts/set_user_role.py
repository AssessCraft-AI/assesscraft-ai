"""
Assign AssessCraft roles to a Firebase user (custom claims + users/{uid} record).

Usage:
    python scripts/set_user_role.py <email> <role[,role...]> [--create --password <pw> --name "<Display Name>"]

Roles: admin, lecturer, moderator. A user can hold several, e.g. "lecturer,moderator".

Requires credentials for the Firebase project (FIREBASE_PROJECT_ID) and the app's Firestore (GCP_PROJECT_ID);
either defaults to the other when only one is set.
The user must sign out and back in (or refresh their ID token) for a new claim to take effect.
"""
import argparse
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import firebase_admin
from firebase_admin import auth as firebase_auth
from google.cloud import firestore

from app.config import settings
from app.models import normalize_roles

VALID_ROLES = ("admin", "lecturer", "moderator")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("email")
    parser.add_argument("roles", help="Comma-separated roles, e.g. lecturer,moderator")
    parser.add_argument("--create", action="store_true", help="Create the user if it does not exist")
    parser.add_argument("--password", help="Initial password (with --create)")
    parser.add_argument("--name", help="Display name (with --create)")
    args = parser.parse_args()
    requested = [r.strip() for r in args.roles.split(",") if r.strip()]
    unknown = [r for r in requested if r not in VALID_ROLES]
    if unknown or not requested:
        print(f"ERROR: roles must be from {', '.join(VALID_ROLES)} (got: {args.roles}).", file=sys.stderr)
        return 1
    roles = normalize_roles(requested)

    # Sign-in accounts live in the Firebase project; the users/{uid} record in the app's Firestore (GCP project).
    firebase_project = settings.FIREBASE_PROJECT_ID or settings.GCP_PROJECT_ID
    firestore_project = settings.GCP_PROJECT_ID or settings.FIREBASE_PROJECT_ID
    if not firebase_project:
        print("ERROR: set FIREBASE_PROJECT_ID and/or GCP_PROJECT_ID.", file=sys.stderr)
        return 1
    firebase_admin.initialize_app(options={"projectId": firebase_project})

    try:
        user = firebase_auth.get_user_by_email(args.email)
    except firebase_auth.UserNotFoundError:
        if not args.create:
            print(f"ERROR: no Firebase user {args.email}. Re-run with --create --password <pw>.", file=sys.stderr)
            return 1
        if not args.password:
            print("ERROR: --create needs --password.", file=sys.stderr)
            return 1
        user = firebase_auth.create_user(
            email=args.email, password=args.password, display_name=args.name, email_verified=True
        )
        print(f"Created Firebase user {args.email} ({user.uid})")

    firebase_auth.set_custom_user_claims(user.uid, {"role": roles[0], "roles": roles})
    firestore.Client(project=firestore_project).collection("users").document(user.uid).set(
        {
            "uid": user.uid,
            "email": args.email,
            "displayName": user.display_name or args.name or args.email.split("@")[0],
            "role": roles[0],
            "roles": roles,
        },
        merge=True,
    )
    print(f"{args.email} ({user.uid}) now has roles {', '.join(roles)}. They must sign in again to pick them up.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
