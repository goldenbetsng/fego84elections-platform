from __future__ import annotations

import os
import tempfile

from django import forms
from django.contrib import admin, messages
from django.contrib.auth.admin import UserAdmin
from django.http import HttpRequest, HttpResponse
from django.template.response import TemplateResponse
from django.urls import path

from auditlog.models import AuditLog

from .models import AdminPermission, User, VoterProfile
from .ods_import import import_voters_from_ods
from .permissions import has_admin_permission, is_superadmin


class AdminPermissionInline(admin.StackedInline):
    model = AdminPermission
    can_delete = False
    extra = 0
    verbose_name_plural = "Admin Permissions"


class VoterProfileInline(admin.StackedInline):
    model = VoterProfile
    can_delete = False
    extra = 0
    verbose_name_plural = "Voter Profile"


class ODSImportForm(forms.Form):
    ods_file = forms.FileField(help_text="Upload voter register (.ods)")
    sheet_name = forms.CharField(required=False, help_text="Optional sheet name (leave blank for first sheet)")


@admin.register(User)
class CustomUserAdmin(UserAdmin):
    """User admin with role-aware and permission-aware access.

    - SUPERADMIN: full access
    - ADMIN: can manage VOTER users only if can_manage_voters=True
    """

    fieldsets = UserAdmin.fieldsets + (
        ("FEGO Roles", {"fields": ("role",)}),
    )
    list_display = (
        "username",
        "email",
        "first_name",
        "last_name",
        "role",
        "is_active",
        "is_staff",
    )
    list_filter = ("role", "is_active", "is_staff")
    inlines = [VoterProfileInline, AdminPermissionInline]
    change_list_template = "admin/accounts/user/change_list.html"

    def get_queryset(self, request: HttpRequest):
        qs = super().get_queryset(request)
        if is_superadmin(request.user):
            return qs
        # Admin members only see voters
        if request.user.role == User.Role.ADMIN and has_admin_permission(request.user, "can_manage_voters"):
            return qs.filter(role=User.Role.VOTER)
        return qs.none()

    def has_module_permission(self, request: HttpRequest) -> bool:
        return is_superadmin(request.user) or (
            request.user.role == User.Role.ADMIN and has_admin_permission(request.user, "can_manage_voters")
        )

    def has_view_permission(self, request: HttpRequest, obj=None) -> bool:
        if is_superadmin(request.user):
            return True
        return request.user.role == User.Role.ADMIN and has_admin_permission(request.user, "can_manage_voters")

    def has_add_permission(self, request: HttpRequest) -> bool:
        if is_superadmin(request.user):
            return True
        return request.user.role == User.Role.ADMIN and has_admin_permission(request.user, "can_manage_voters")

    def has_change_permission(self, request: HttpRequest, obj=None) -> bool:
        if is_superadmin(request.user):
            return True
        return request.user.role == User.Role.ADMIN and has_admin_permission(request.user, "can_manage_voters")

    def has_delete_permission(self, request: HttpRequest, obj=None) -> bool:
        # Conservative: only superadmin deletes users
        return is_superadmin(request.user)

    def get_readonly_fields(self, request: HttpRequest, obj=None):
        ro = list(super().get_readonly_fields(request, obj))
        if not is_superadmin(request.user):
            # Admin members cannot elevate roles or toggle staff/superuser
            ro += ["role", "is_staff", "is_superuser", "user_permissions", "groups"]
        return ro

    def save_model(self, request: HttpRequest, obj: User, form, change: bool) -> None:
        # Prevent non-superadmin role changes even if posted
        if not is_superadmin(request.user) and obj.pk:
            prior = User.objects.filter(pk=obj.pk).first()
            if prior and prior.role != obj.role:
                obj.role = prior.role
        super().save_model(request, obj, form, change)

    # --- Voter Register Import (Sprint D) ---
    def get_urls(self):
        urls = super().get_urls()
        custom = [
            path(
                "voter-import/",
                self.admin_site.admin_view(self.voter_import_view),
                name="voter_import",
            ),
        ]
        return custom + urls

    def voter_import_view(self, request: HttpRequest) -> HttpResponse:
        if not (is_superadmin(request.user) or has_admin_permission(request.user, "can_manage_voters")):
            self.message_user(request, "You do not have permission to import voters.", level=messages.ERROR)
            return TemplateResponse(request, "admin/403.html", status=403)

        context = dict(
            self.admin_site.each_context(request),
            title="Import Voter Register (.ods)",
        )

        if request.method == "POST":
            form = ODSImportForm(request.POST, request.FILES)
            if form.is_valid():
                ods = form.cleaned_data["ods_file"]
                sheet_name = form.cleaned_data.get("sheet_name") or None
                # Write to temp file for pyexcel
                with tempfile.NamedTemporaryFile(delete=False, suffix=".ods") as tmp:
                    for chunk in ods.chunks():
                        tmp.write(chunk)
                    tmp_path = tmp.name
                try:
                    summary = import_voters_from_ods(tmp_path, sheet_name=sheet_name)
                    AuditLog.objects.create(
                        event_type="VOTER_IMPORT",
                        actor=request.user,
                        metadata={
                            "created": summary.created,
                            "updated": summary.updated,
                            "skipped": summary.skipped,
                            "errors": summary.errors,
                        },
                    )

                    if summary.errors:
                        messages.warning(
                            request,
                            f"Import completed with {summary.errors} error(s). Created={summary.created}, Updated={summary.updated}, Skipped={summary.skipped}.",
                        )
                    else:
                        messages.success(
                            request,
                            f"Import successful. Created={summary.created}, Updated={summary.updated}, Skipped={summary.skipped}.",
                        )
                    context["summary"] = summary
                    context["form"] = form
                    return TemplateResponse(request, "admin/voter_import.html", context)
                finally:
                    try:
                        os.unlink(tmp_path)
                    except Exception:
                        pass
        else:
            form = ODSImportForm()

        context["form"] = form
        return TemplateResponse(request, "admin/voter_import.html", context)


@admin.register(VoterProfile)
class VoterProfileAdmin(admin.ModelAdmin):
    list_display = ("user", "membership_no", "is_candidate")
    search_fields = ("user__username", "membership_no")

    def has_module_permission(self, request: HttpRequest) -> bool:
        return is_superadmin(request.user) or has_admin_permission(request.user, "can_manage_voters")

    def has_view_permission(self, request: HttpRequest, obj=None) -> bool:
        return self.has_module_permission(request)

    def has_add_permission(self, request: HttpRequest) -> bool:
        return self.has_module_permission(request)

    def has_change_permission(self, request: HttpRequest, obj=None) -> bool:
        return self.has_module_permission(request)

    def has_delete_permission(self, request: HttpRequest, obj=None) -> bool:
        return is_superadmin(request.user)


@admin.register(AdminPermission)
class AdminPermissionAdmin(admin.ModelAdmin):
    list_display = (
        "user",
        "can_manage_elections",
        "can_manage_posts",
        "can_manage_candidates",
        "can_manage_voters",
        "can_manage_content",
        "can_view_audit",
        "can_view_results",
    )
    list_filter = (
        "can_manage_elections",
        "can_manage_posts",
        "can_manage_candidates",
        "can_manage_voters",
        "can_manage_content",
        "can_view_audit",
        "can_view_results",
    )
    search_fields = ("user__username",)

    def has_module_permission(self, request: HttpRequest) -> bool:
        # Only Super Admin can manage permissions
        return is_superadmin(request.user)

    def has_view_permission(self, request: HttpRequest, obj=None) -> bool:
        return is_superadmin(request.user)

    def has_add_permission(self, request: HttpRequest) -> bool:
        return is_superadmin(request.user)

    def has_change_permission(self, request: HttpRequest, obj=None) -> bool:
        return is_superadmin(request.user)

    def has_delete_permission(self, request: HttpRequest, obj=None) -> bool:
        return is_superadmin(request.user)
