from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Tuple

from django.contrib.auth import get_user_model
from django.db import transaction

from pyexcel_ods3 import get_data

from .models import VoterProfile


User = get_user_model()


@dataclass
class ImportRowResult:
    row_index: int
    username: str
    action: str  # created|updated|skipped|error
    message: str = ""


@dataclass
class ImportSummary:
    created: int
    updated: int
    skipped: int
    errors: int
    results: List[ImportRowResult]


def _norm_header(h: Any) -> str:
    return str(h or "").strip().lower().replace(" ", "_")


def _boolish(v: Any, default: bool = True) -> bool:
    if v is None or v == "":
        return default
    if isinstance(v, bool):
        return v
    s = str(v).strip().lower()
    if s in {"1", "y", "yes", "true", "t"}:
        return True
    if s in {"0", "n", "no", "false", "f"}:
        return False
    return default


def import_voters_from_ods(
    ods_file_path: str,
    sheet_name: str | None = None,
    *,
    default_active: bool = True,
    default_is_candidate: bool = False,
) -> ImportSummary:
    """Import voters from an .ods file.

    Expected headers (case-insensitive, spaces ok):
    - username (required)
    - first_name
    - last_name
    - email
    - membership_no
    - active
    - password (optional; if missing for new user, unusable password is set)
    - is_candidate (optional)
    """

    data = get_data(ods_file_path)
    if not data:
        return ImportSummary(0, 0, 0, 1, [ImportRowResult(0, "", "error", "ODS appears empty")])

    # Choose sheet
    if sheet_name and sheet_name in data:
        rows = data[sheet_name]
    else:
        # first sheet
        first_sheet = next(iter(data.keys()))
        rows = data[first_sheet]

    if not rows or len(rows) < 2:
        return ImportSummary(0, 0, 0, 1, [ImportRowResult(0, "", "error", "No data rows found")])

    header = [_norm_header(h) for h in rows[0]]
    idx = {name: i for i, name in enumerate(header) if name}

    if "username" not in idx:
        return ImportSummary(0, 0, 0, 1, [ImportRowResult(0, "", "error", "Missing required 'username' column")])

    results: List[ImportRowResult] = []
    created = updated = skipped = errors = 0

    @transaction.atomic
    def _process():
        nonlocal created, updated, skipped, errors
        for r_i, row in enumerate(rows[1:], start=2):
            # row index: spreadsheet line number (1-based)
            try:
                username = str(row[idx["username"]] or "").strip()
                if not username:
                    skipped += 1
                    results.append(ImportRowResult(r_i, "", "skipped", "Blank username"))
                    continue

                first_name = str(row[idx.get("first_name", -1)] or "").strip() if "first_name" in idx else ""
                last_name = str(row[idx.get("last_name", -1)] or "").strip() if "last_name" in idx else ""
                email = str(row[idx.get("email", -1)] or "").strip() if "email" in idx else ""
                membership_no = str(row[idx.get("membership_no", -1)] or "").strip() if "membership_no" in idx else ""
                active = _boolish(row[idx.get("active", -1)], default_active) if "active" in idx else default_active
                password = str(row[idx.get("password", -1)] or "").strip() if "password" in idx else ""
                is_candidate = _boolish(row[idx.get("is_candidate", -1)], default_is_candidate) if "is_candidate" in idx else default_is_candidate

                user_obj, was_created = User.objects.get_or_create(username=username, defaults={
                    "first_name": first_name,
                    "last_name": last_name,
                    "email": email,
                    "is_active": active,
                    "role": User.Role.VOTER,
                })

                # Ensure role is VOTER for imported voters
                changed = False
                if user_obj.role != User.Role.VOTER:
                    user_obj.role = User.Role.VOTER
                    changed = True
                if user_obj.first_name != first_name and first_name:
                    user_obj.first_name = first_name
                    changed = True
                if user_obj.last_name != last_name and last_name:
                    user_obj.last_name = last_name
                    changed = True
                if user_obj.email != email and email:
                    user_obj.email = email
                    changed = True
                if user_obj.is_active != active:
                    user_obj.is_active = active
                    changed = True

                if password:
                    user_obj.set_password(password)
                    changed = True
                elif was_created:
                    # Force admin to set password later (more secure than blank)
                    user_obj.set_unusable_password()
                    changed = True

                if changed:
                    user_obj.save()

                vp, _ = VoterProfile.objects.get_or_create(user=user_obj)
                if membership_no and vp.membership_no != membership_no:
                    vp.membership_no = membership_no
                vp.is_candidate = bool(is_candidate)
                vp.save()

                if was_created:
                    created += 1
                    results.append(ImportRowResult(r_i, username, "created", ""))
                else:
                    updated += 1
                    results.append(ImportRowResult(r_i, username, "updated", ""))

            except Exception as e:
                errors += 1
                results.append(ImportRowResult(r_i, username if 'username' in locals() else "", "error", str(e)))

    _process()

    return ImportSummary(created, updated, skipped, errors, results)
