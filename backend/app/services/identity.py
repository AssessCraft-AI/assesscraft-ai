"""
Firebase Authentication account management for the admin dashboard.

Creating or changing sign-in accounts needs Firebase Admin credentials (a service account key via
GOOGLE_APPLICATION_CREDENTIALS, or ADC on Cloud Run). Without them every call raises
IdentityUnavailable and the admin API decides whether a local-only record is acceptable.
"""
import asyncio
from typing import List, Optional

from firebase_admin import auth as firebase_auth


class IdentityUnavailable(Exception):
    """Firebase Admin could not be reached (usually: no credentials on this machine)."""


class EmailAlreadyExists(Exception):
    pass


async def _call(fn, *args, **kwargs):
    try:
        return await asyncio.to_thread(fn, *args, **kwargs)
    except firebase_auth.EmailAlreadyExistsError as e:
        raise EmailAlreadyExists(str(e)) from e
    except (ValueError, firebase_auth.UserNotFoundError):
        raise
    except Exception as e:  # credentials / network / project errors
        raise IdentityUnavailable(str(e)) from e


def _role_claims(roles: List[str]) -> dict:
    # `role` (the primary) stays for tokens read by older builds.
    return {"role": roles[0], "roles": roles}


async def create_account(email: str, password: str, display_name: str, roles: List[str]) -> str:
    """Creates the Firebase sign-in account with its role claims and returns the uid."""
    user = await _call(
        firebase_auth.create_user,
        email=email,
        password=password,
        display_name=display_name,
        email_verified=True,
    )
    await _call(firebase_auth.set_custom_user_claims, user.uid, _role_claims(roles))
    return user.uid


async def update_account(
    uid: str,
    *,
    roles: Optional[List[str]] = None,
    display_name: Optional[str] = None,
    disabled: Optional[bool] = None,
    password: Optional[str] = None,
) -> None:
    changes = {}
    if display_name is not None:
        changes["display_name"] = display_name
    if disabled is not None:
        changes["disabled"] = disabled
    if password is not None:
        changes["password"] = password
    if changes:
        await _call(firebase_auth.update_user, uid, **changes)
    if roles:
        await _call(firebase_auth.set_custom_user_claims, uid, _role_claims(roles))
    if disabled:
        # Sign the user out everywhere: existing ID tokens stop refreshing.
        await _call(firebase_auth.revoke_refresh_tokens, uid)
