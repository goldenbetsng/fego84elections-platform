from __future__ import annotations

from typing import Literal

from .models import AdminPermission, User


AdminPermKey = Literal[
    "can_manage_elections",
    "can_manage_posts",
    "can_manage_candidates",
    "can_manage_voters",
    "can_manage_content",
    "can_view_audit",
    "can_view_results",
]


def has_admin_permission(user: User, key: AdminPermKey) -> bool:
    """Return True if user is allowed for the requested admin capability."""
    if not user.is_authenticated:
        return False
    if user.role == User.Role.SUPERADMIN:
        return True
    if user.role != User.Role.ADMIN:
        return False

    try:
        perms: AdminPermission = user.admin_permissions  # type: ignore[attr-defined]
    except Exception:
        return False
    return bool(getattr(perms, key, False))


def is_superadmin(user: User) -> bool:
    return bool(user.is_authenticated and user.role == User.Role.SUPERADMIN)
