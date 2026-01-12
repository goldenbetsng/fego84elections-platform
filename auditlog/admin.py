from django.contrib import admin
from django.http import HttpRequest

from .models import AuditLog
from accounts.permissions import has_admin_permission, is_superadmin


@admin.register(AuditLog)
class AuditLogAdmin(admin.ModelAdmin):
    list_display = ('event_type', 'actor', 'created_at')
    list_filter = ('event_type', 'created_at')
    search_fields = ('event_type', 'actor__username')

    def has_module_permission(self, request: HttpRequest) -> bool:
        return is_superadmin(request.user) or has_admin_permission(request.user, 'can_view_audit')

    def has_view_permission(self, request: HttpRequest, obj=None) -> bool:
        return self.has_module_permission(request)

    def has_add_permission(self, request: HttpRequest) -> bool:
        return False

    def has_change_permission(self, request: HttpRequest, obj=None) -> bool:
        return False

    def has_delete_permission(self, request: HttpRequest, obj=None) -> bool:
        return is_superadmin(request.user)
