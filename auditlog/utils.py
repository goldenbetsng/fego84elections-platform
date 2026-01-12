from __future__ import annotations

from typing import Any

from .models import AuditLog


def log_event(*, actor=None, event_type: str, metadata: dict[str, Any] | None = None) -> None:
    AuditLog.objects.create(
        actor=actor,
        event_type=event_type,
        metadata=metadata or {},
    )
