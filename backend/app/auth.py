import logging
from typing import Optional, List
from fastapi import Header, HTTPException, status, Depends
import firebase_admin
from firebase_admin import auth as firebase_auth, credentials as firebase_credentials

from app.config import settings
from app.services.firestore import db
from app.models import User, UserRole, roles_of

logger = logging.getLogger("assesscraft.auth")

# Initialize Firebase Admin app if not already initialized
try:
    if not firebase_admin._apps:
        firebase_project = settings.FIREBASE_PROJECT_ID or settings.GCP_PROJECT_ID
        cred = (
            firebase_credentials.Certificate(settings.FIREBASE_CREDENTIALS)
            if settings.FIREBASE_CREDENTIALS
            else None
        )
        options = {"projectId": firebase_project} if firebase_project else None
        firebase_admin.initialize_app(cred, options)
except Exception:
    # In local testing without GCP project, Firebase Admin will handle demo tokens
    pass

# Built-in demo accounts for competition judging and seamless local testing
DEMO_USERS = {
    "admin@demo": User(
        uid="demo-admin-uid",
        email="admin@demo",
        displayName="Alex Morgan (Administrator)",
        role="admin",
        institution="AssessCraft Academic Institute",
    ),
    "lecturer@demo": User(
        uid="demo-lecturer-uid",
        email="lecturer@demo",
        displayName="Dr. Samantha Chen (Lecturer)",
        role="lecturer",
        institution="AssessCraft Academic Institute",
    ),
    "moderator@demo": User(
        uid="demo-moderator-uid",
        email="moderator@demo",
        displayName="Prof. David Vance (External Moderator)",
        role="moderator",
        institution="Quality Assurance Board",
    ),
}


VALID_ROLES = ("admin", "lecturer", "moderator")


async def _user_from_firebase_claims(decoded: dict) -> User:
    """
    Builds the app User from a verified Firebase ID token.
    Roles come from the admin-managed Firestore users/{uid} record, else the `roles`/`role` custom claim,
    else DEFAULT_ROLE (empty by default: no role, no access). They are never derived from the email address.
    """
    email = decoded.get("email") or ""
    uid = decoded.get("uid") or decoded.get("user_id") or decoded.get("sub")
    if not uid:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token has no subject")

    allowed = [d.strip().lower() for d in settings.ALLOWED_EMAIL_DOMAINS.split(",") if d.strip()]
    if allowed:
        domain = email.rsplit("@", 1)[-1].lower() if "@" in email else ""
        if domain not in allowed or not decoded.get("email_verified"):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Sign-in is restricted to verified accounts from approved institutional domains",
            )

    # The users/{uid} record is the admin-managed source of truth (role, assignment, disabled flag).
    record = await db.get_user_record(uid)
    if record and record.get("disabled"):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="This account has been disabled by an administrator")
    roles = [r for r in roles_of(record) if r in VALID_ROLES]
    if not roles:
        roles = [r for r in roles_of({"roles": decoded.get("roles"), "role": decoded.get("role")}) if r in VALID_ROLES]
    if not roles and settings.DEFAULT_ROLE in VALID_ROLES:
        roles = [settings.DEFAULT_ROLE]
    if not roles:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="No role is assigned to this account yet. Ask an administrator for access.",
        )

    extra = {"institution": record["institution"]} if record and record.get("institution") else {}
    return User(
        uid=uid,
        email=email or "unknown",
        displayName=(record or {}).get("displayName") or decoded.get("name") or (email.split("@")[0] if email else uid),
        roles=roles,
        **extra,
    )


async def get_current_user(
    authorization: Optional[str] = Header(None),
    x_demo_user: Optional[str] = Header(None),
    x_demo_role: Optional[str] = Header(None),
) -> User:
    """
    Extracts and validates the current user.
    Supports Firebase ID tokens and competition demo accounts.
    """
    demo_enabled = settings.ENABLE_DEMO_AUTH

    # 1. Demo user switcher (headers) - only when demo auth is explicitly enabled
    if demo_enabled and x_demo_user and x_demo_user in DEMO_USERS:
        return DEMO_USERS[x_demo_user]

    if demo_enabled and x_demo_role:
        role_map = {
            "admin": DEMO_USERS["admin@demo"],
            "lecturer": DEMO_USERS["lecturer@demo"],
            "moderator": DEMO_USERS["moderator@demo"],
        }
        if x_demo_role in role_map:
            return role_map[x_demo_role]

    token: Optional[str] = None
    if authorization and authorization.startswith("Bearer "):
        token = authorization.split("Bearer ", 1)[1].strip()

    # Demo token shortcuts - only when demo auth is explicitly enabled
    if demo_enabled:
        if token in ("demo-admin-token", "admin"):
            return DEMO_USERS["admin@demo"]
        if token in ("demo-lecturer-token", "lecturer"):
            return DEMO_USERS["lecturer@demo"]
        if token in ("demo-moderator-token", "moderator"):
            return DEMO_USERS["moderator@demo"]

    # 2. Verify with Firebase Admin if a bearer token is present
    if token:
        try:
            # Tolerate small clock drift: a server clock a second behind Google's rejects every fresh token as "used too early".
            decoded_token = firebase_auth.verify_id_token(token, clock_skew_seconds=10)
        except Exception as exc:
            logger.warning("Firebase ID token rejected: %s: %s", type(exc).__name__, exc)
            decoded_token = None
        if decoded_token is not None:
            return await _user_from_firebase_claims(decoded_token)
        # Never fall back to a demo persona for a bad token, even with demo auth on: the caller
        # would silently act as the demo lecturer while their UI shows a different user.
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired Firebase authentication token",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # 3. Fallback for demo / unauthenticated evaluation
    if settings.ENABLE_DEMO_AUTH:
        return DEMO_USERS["lecturer@demo"]

    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Authentication required",
        headers={"WWW-Authenticate": "Bearer"},
    )


def require_role(allowed_roles: List[UserRole]):
    """
    Dependency factory to enforce role-based access control.
    """
    async def role_checker(user: User = Depends(get_current_user)) -> User:
        if not user.has_role(*allowed_roles):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Forbidden: Action requires one of {allowed_roles} roles. Current roles: {user.roles}",
            )
        return user
    return role_checker
