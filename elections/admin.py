from __future__ import annotations

import csv
from typing import Any, Dict, List

from django.contrib import admin, messages
from django.db import transaction
from django.http import HttpRequest, HttpResponse, HttpResponseRedirect
from django.template.response import TemplateResponse
from django.urls import path, reverse
from django.utils import timezone

from .models import Election, Post, Candidate, Vote, ElectionArchive
from accounts.permissions import has_admin_permission, is_superadmin

from .reports import compute_election_results, results_as_dict
from .participation import build_participation_rows, participation_as_dict
from accounts.models import User


@admin.register(Election)
class ElectionAdmin(admin.ModelAdmin):
    list_display = ('title', 'status', 'start_at', 'end_at', 'created_at')
    list_filter = ('status',)
    search_fields = ('title',)

    change_form_template = "admin/elections/election/change_form.html"

    def has_module_permission(self, request: HttpRequest) -> bool:
        # Manage elections OR view results reports.
        return (
            is_superadmin(request.user)
            or has_admin_permission(request.user, 'can_manage_elections')
            or has_admin_permission(request.user, 'can_view_results')
        )

    def has_view_permission(self, request: HttpRequest, obj=None) -> bool:
        return self.has_module_permission(request)

    def has_add_permission(self, request: HttpRequest) -> bool:
        return is_superadmin(request.user) or has_admin_permission(request.user, 'can_manage_elections')

    def has_change_permission(self, request: HttpRequest, obj=None) -> bool:
        return is_superadmin(request.user) or has_admin_permission(request.user, 'can_manage_elections')

    def has_delete_permission(self, request: HttpRequest, obj=None) -> bool:
        return is_superadmin(request.user)

    def get_urls(self):
        urls = super().get_urls()
        custom = [
            path(
                "<path:object_id>/reports/",
                self.admin_site.admin_view(self.reports_view),
                name="election_reports",
            ),
            path(
                "<path:object_id>/reports.csv",
                self.admin_site.admin_view(self.reports_csv),
                name="election_reports_csv",
            ),
            path(
                "<path:object_id>/participation/",
                self.admin_site.admin_view(self.participation_view),
                name="election_participation",
            ),
            path(
                "<path:object_id>/participation.csv",
                self.admin_site.admin_view(self.participation_csv),
                name="election_participation_csv",
            ),
            path(
                "<path:object_id>/tiebreak/create/",
                self.admin_site.admin_view(self.create_tiebreak_post),
                name="election_create_tiebreak",
            ),
            path(
                "<path:object_id>/archive/create/",
                self.admin_site.admin_view(self.create_archive),
                name="election_create_archive",
            ),
        ]
        return custom + urls

    def _can_view_reports(self, request: HttpRequest) -> bool:
        return is_superadmin(request.user) or has_admin_permission(request.user, "can_view_results") or has_admin_permission(request.user, "can_manage_elections")

    def reports_view(self, request: HttpRequest, object_id: str) -> HttpResponse:
        if not self._can_view_reports(request):
            return TemplateResponse(request, "admin/403.html", status=403)

        election = self.get_object(request, object_id)
        if not election:
            return TemplateResponse(request, "admin/403.html", status=404)

        post_results = compute_election_results(election)
        total_voters = User.objects.filter(role=User.Role.VOTER, is_active=True).count()
        total_votes_cast = Vote.objects.filter(post__election=election).count()
        can_create_tiebreak = (
            is_superadmin(request.user)
            or (
                has_admin_permission(request.user, "can_manage_posts")
                and has_admin_permission(request.user, "can_manage_candidates")
            )
        )

        ctx = {
            **self.admin_site.each_context(request),
            "title": f"Results: {election.title}",
            "election": election,
            "post_results": post_results,
            "total_voters": total_voters,
            "total_votes_cast": total_votes_cast,
            "can_create_tiebreak": can_create_tiebreak,
        }
        return TemplateResponse(request, "admin/elections/reports.html", ctx)

    def reports_csv(self, request: HttpRequest, object_id: str) -> HttpResponse:
        if not self._can_view_reports(request):
            return TemplateResponse(request, "admin/403.html", status=403)

        election = self.get_object(request, object_id)
        if not election:
            return TemplateResponse(request, "admin/403.html", status=404)

        resp = HttpResponse(content_type="text/csv")
        resp["Content-Disposition"] = f'attachment; filename="{election.title}-results.csv"'
        writer = csv.writer(resp)
        writer.writerow(["election", "post", "candidate", "votes", "total_votes", "is_tie"])
        for pr in compute_election_results(election):
            for cr in pr.candidate_results:
                writer.writerow([election.title, pr.post.title, cr.display_name, cr.votes, pr.total_votes, pr.is_tie])
            if not pr.candidate_results:
                writer.writerow([election.title, pr.post.title, "", 0, 0, False])
        return resp

    def participation_view(self, request: HttpRequest, object_id: str) -> HttpResponse:
        if not self._can_view_reports(request):
            return TemplateResponse(request, "admin/403.html", status=403)
        election = self.get_object(request, object_id)
        if not election:
            return TemplateResponse(request, "admin/403.html", status=404)

        posts = list(election.posts.filter(is_active=True).order_by("display_order", "id"))
        voters = list(User.objects.filter(role=User.Role.VOTER, is_active=True).order_by("username"))

        # Lightweight: render first N voters (pagination) to avoid huge pages.
        from django.core.paginator import Paginator

        page_size = int(request.GET.get("page_size", 50))
        paginator = Paginator(voters, page_size)
        page_obj = paginator.get_page(request.GET.get("page", 1))

        rows = build_participation_rows(election, list(page_obj.object_list), posts)
        ctx = {
            **self.admin_site.each_context(request),
            "title": f"Participation: {election.title}",
            "election": election,
            "posts": posts,
            "rows": rows,
            "page_obj": page_obj,
            "page_size": page_size,
        }
        return TemplateResponse(request, "admin/elections/participation.html", ctx)

    def participation_csv(self, request: HttpRequest, object_id: str) -> HttpResponse:
        if not self._can_view_reports(request):
            return TemplateResponse(request, "admin/403.html", status=403)
        election = self.get_object(request, object_id)
        if not election:
            return TemplateResponse(request, "admin/403.html", status=404)

        posts = list(election.posts.filter(is_active=True).order_by("display_order", "id"))
        voters = list(User.objects.filter(role=User.Role.VOTER, is_active=True).order_by("username"))
        rows = build_participation_rows(election, voters, posts)

        resp = HttpResponse(content_type="text/csv")
        resp["Content-Disposition"] = f'attachment; filename="{election.title}-participation.csv"'
        writer = csv.writer(resp)

        header = ["username", "first_name", "last_name"]
        for p in posts:
            header.extend([f"{p.title}__voted", f"{p.title}__cast_at"])
        writer.writerow(header)

        for r in rows:
            row = [r.user.username, r.user.first_name, r.user.last_name]
            for p in posts:
                cell = r.by_post[p.id]
                row.append("YES" if cell.voted else "NO")
                row.append(cell.cast_at or "")
            writer.writerow(row)
        return resp

    def create_tiebreak_post(self, request: HttpRequest, object_id: str) -> HttpResponse:
        # Requires ability to manage posts + candidates (since we create both).
        if not (
            is_superadmin(request.user)
            or (
                has_admin_permission(request.user, "can_manage_posts")
                and has_admin_permission(request.user, "can_manage_candidates")
            )
        ):
            return TemplateResponse(request, "admin/403.html", status=403)

        election = self.get_object(request, object_id)
        if not election:
            return TemplateResponse(request, "admin/403.html", status=404)

        if request.method != "POST":
            return TemplateResponse(request, "admin/403.html", status=405)

        parent_post_id = request.POST.get("parent_post_id")
        if not parent_post_id:
            messages.error(request, "Missing parent_post_id")
            return HttpResponse(status=400)

        parent_post = Post.objects.filter(id=parent_post_id, election=election).first()
        if not parent_post:
            messages.error(request, "Parent post not found")
            return HttpResponse(status=404)

        # Compute tie for the parent post
        pr = None
        for x in compute_election_results(election):
            if x.post.id == parent_post.id:
                pr = x
                break
        if not pr or not pr.is_tie:
            messages.error(request, "Selected post is not currently tied (no tie-break created).")
            return HttpResponseRedirect(reverse("admin:election_reports", args=[election.id]))

        tied_candidates = Candidate.objects.filter(id__in=pr.tied_candidate_ids, post=parent_post)
        if not tied_candidates.exists():
            messages.error(request, "Could not locate tied candidates.")
            return HttpResponseRedirect(reverse("admin:election_reports", args=[election.id]))

        # Determine next tie-break round number
        existing_rounds = parent_post.tiebreak_posts.count()
        round_no = existing_rounds + 1

        with transaction.atomic():
            tb_post = Post.objects.create(
                election=election,
                title=f"{parent_post.title} (Tie-break Round {round_no})",
                display_order=parent_post.display_order,
                is_active=True,
                parent_post=parent_post,
                is_tiebreak=True,
                status=Post.Status.INHERIT,
            )

            for c in tied_candidates:
                Candidate.objects.create(
                    post=tb_post,
                    user=c.user,
                    display_name=c.display_name,
                    bio=c.bio,
                    is_active=True,
                )

        messages.success(
            request,
            f"Tie-break post created: {tb_post.title}. Set it to OPEN (post status) when ready.",
        )
        return HttpResponseRedirect(reverse("admin:elections_post_change", args=[tb_post.id]))

    def create_archive(self, request: HttpRequest, object_id: str) -> HttpResponse:
        if not self._can_view_reports(request):
            return TemplateResponse(request, "admin/403.html", status=403)

        election = self.get_object(request, object_id)
        if not election:
            return TemplateResponse(request, "admin/403.html", status=404)

        if request.method != "POST":
            return TemplateResponse(request, "admin/403.html", status=405)

        payload: Dict[str, Any] = {
            "results": results_as_dict(election),
            "participation": participation_as_dict(election),
            "snapshot_at": timezone.now().isoformat(timespec="seconds"),
        }
        ElectionArchive.objects.create(
            election=election,
            created_by=request.user,
            note=request.POST.get("note", ""),
            data=payload,
        )
        messages.success(request, "Archive snapshot created.")
        return HttpResponseRedirect(reverse("admin:elections_election_change", args=[election.id]))


@admin.register(Post)
class PostAdmin(admin.ModelAdmin):
    list_display = ('title', 'election', 'display_order', 'is_active', 'status', 'start_at', 'end_at', 'is_tiebreak', 'parent_post')
    list_filter = ('election', 'is_active', 'is_tiebreak')
    search_fields = ('title',)

    def has_module_permission(self, request: HttpRequest) -> bool:
        return is_superadmin(request.user) or has_admin_permission(request.user, 'can_manage_posts')

    def has_view_permission(self, request: HttpRequest, obj=None) -> bool:
        return self.has_module_permission(request)

    def has_add_permission(self, request: HttpRequest) -> bool:
        return self.has_module_permission(request)

    def has_change_permission(self, request: HttpRequest, obj=None) -> bool:
        return self.has_module_permission(request)

    def has_delete_permission(self, request: HttpRequest, obj=None) -> bool:
        return is_superadmin(request.user)


@admin.register(Candidate)
class CandidateAdmin(admin.ModelAdmin):
    list_display = ('display_name', 'post', 'is_active', 'user')
    list_filter = ('is_active', 'post__election')
    search_fields = ('display_name',)

    def has_module_permission(self, request: HttpRequest) -> bool:
        return is_superadmin(request.user) or has_admin_permission(request.user, 'can_manage_candidates')

    def has_view_permission(self, request: HttpRequest, obj=None) -> bool:
        return self.has_module_permission(request)

    def has_add_permission(self, request: HttpRequest) -> bool:
        return self.has_module_permission(request)

    def has_change_permission(self, request: HttpRequest, obj=None) -> bool:
        return self.has_module_permission(request)

    def has_delete_permission(self, request: HttpRequest, obj=None) -> bool:
        return is_superadmin(request.user)


@admin.register(Vote)
class VoteAdmin(admin.ModelAdmin):
    list_display = ('voter', 'post', 'candidate', 'cast_at')
    list_filter = ('post__election',)
    search_fields = ('voter__username', 'candidate__display_name')

    def has_module_permission(self, request: HttpRequest) -> bool:
        # Vote table reveals individual selections; keep superadmin-only.
        return is_superadmin(request.user)

    def has_view_permission(self, request: HttpRequest, obj=None) -> bool:
        return is_superadmin(request.user)

    def has_add_permission(self, request: HttpRequest) -> bool:
        return False

    def has_change_permission(self, request: HttpRequest, obj=None) -> bool:
        return False

    def has_delete_permission(self, request: HttpRequest, obj=None) -> bool:
        return False


@admin.register(ElectionArchive)
class ElectionArchiveAdmin(admin.ModelAdmin):
    list_display = ("election", "created_at", "created_by", "note")
    list_filter = ("election",)
    search_fields = ("election__title", "note", "created_by__username")
    readonly_fields = ("election", "created_at", "created_by", "note", "data")

    def has_module_permission(self, request: HttpRequest) -> bool:
        return is_superadmin(request.user) or has_admin_permission(request.user, "can_view_results")

    def has_view_permission(self, request: HttpRequest, obj=None) -> bool:
        return self.has_module_permission(request)

    def has_add_permission(self, request: HttpRequest) -> bool:
        return False

    def has_change_permission(self, request: HttpRequest, obj=None) -> bool:
        return False

    def has_delete_permission(self, request: HttpRequest, obj=None) -> bool:
        return is_superadmin(request.user)
