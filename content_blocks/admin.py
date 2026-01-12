from django.contrib import admin
from django.http import HttpRequest
from .models import ContentBlock
from accounts.permissions import has_admin_permission, is_superadmin


@admin.register(ContentBlock)
class ContentBlockAdmin(admin.ModelAdmin):
    list_display = ('key', 'title', 'is_active', 'updated_at')
    list_filter = ('is_active',)
    search_fields = ('key', 'title', 'body')

    def has_module_permission(self, request: HttpRequest) -> bool:
        return is_superadmin(request.user) or has_admin_permission(request.user, 'can_manage_content')

    def has_view_permission(self, request: HttpRequest, obj=None) -> bool:
        return self.has_module_permission(request)

    def has_add_permission(self, request: HttpRequest) -> bool:
        return self.has_module_permission(request)

    def has_change_permission(self, request: HttpRequest, obj=None) -> bool:
        return self.has_module_permission(request)

    def has_delete_permission(self, request: HttpRequest, obj=None) -> bool:
        return is_superadmin(request.user)
