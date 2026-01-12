from __future__ import annotations

from datetime import timedelta
from django.conf import settings
from django.contrib import auth
from django.utils import timezone


class InactivityLogoutMiddleware:
    """Logs out authenticated users after N seconds of inactivity.

    We record last_activity in the session on each request.
    If now-last_activity > SESSION_INACTIVITY_SECONDS, we force logout.
    """

    def __init__(self, get_response):
        self.get_response = get_response
        self.timeout = getattr(settings, 'SESSION_INACTIVITY_SECONDS', 1800)

    def __call__(self, request):
        if request.user.is_authenticated:
            last = request.session.get('last_activity')
            now = timezone.now()
            if last:
                last_dt = timezone.datetime.fromisoformat(last)
                if now - last_dt > timedelta(seconds=self.timeout):
                    auth.logout(request)
                    request.session.flush()
                    # Continue to response (views will redirect if needed)
            request.session['last_activity'] = now.isoformat()
        return self.get_response(request)
