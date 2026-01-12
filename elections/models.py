from __future__ import annotations

from django.conf import settings
from django.db import models
from django.utils import timezone


class Election(models.Model):
    class Status(models.TextChoices):
        DRAFT = 'DRAFT', 'Draft'
        OPEN = 'OPEN', 'Open'
        CLOSED = 'CLOSED', 'Closed'

    title = models.CharField(max_length=200)
    start_at = models.DateTimeField(null=True, blank=True)
    end_at = models.DateTimeField(null=True, blank=True)
    status = models.CharField(max_length=10, choices=Status.choices, default=Status.DRAFT)
    created_at = models.DateTimeField(auto_now_add=True)

    def is_open_now(self) -> bool:
        if self.status != self.Status.OPEN:
            return False
        now = timezone.now()
        if self.start_at and now < self.start_at:
            return False
        if self.end_at and now > self.end_at:
            return False
        return True

    def __str__(self) -> str:
        return self.title


class Post(models.Model):
    class Status(models.TextChoices):
        INHERIT = 'INHERIT', 'Inherit election window'
        OPEN = 'OPEN', 'Open'
        CLOSED = 'CLOSED', 'Closed'

    election = models.ForeignKey(Election, on_delete=models.CASCADE, related_name='posts')
    title = models.CharField(max_length=200)
    display_order = models.PositiveIntegerField(default=0)
    is_active = models.BooleanField(default=True)

    # Sprint E: allow tie-break voting without reopening the whole election.
    # Default behaviour is to inherit election status/window.
    status = models.CharField(max_length=10, choices=Status.choices, default=Status.INHERIT)
    start_at = models.DateTimeField(null=True, blank=True)
    end_at = models.DateTimeField(null=True, blank=True)

    # Tie-break support: create a new Post as a child of the original
    parent_post = models.ForeignKey('self', null=True, blank=True, on_delete=models.SET_NULL, related_name='tiebreak_posts')
    is_tiebreak = models.BooleanField(default=False)

    class Meta:
        ordering = ['display_order', 'id']

    def is_open_now(self) -> bool:
        """Return True if voting is currently open for this post.

        - INHERIT: uses the parent election window
        - OPEN: uses post start/end if set (independent of election status)
        - CLOSED: always closed
        """
        if not self.is_active:
            return False
        if self.status == self.Status.CLOSED:
            return False

        now = timezone.now()
        if self.status == self.Status.OPEN:
            if self.start_at and now < self.start_at:
                return False
            if self.end_at and now > self.end_at:
                return False
            return True

        # INHERIT
        return self.election.is_open_now()

    def __str__(self) -> str:
        return f"{self.election.title} - {self.title}"


class Candidate(models.Model):
    post = models.ForeignKey(Post, on_delete=models.CASCADE, related_name='candidates')
    # Link to a user if the candidate is also a system user (enables vote restriction)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name='candidate_entries')
    display_name = models.CharField(max_length=200)
    bio = models.TextField(blank=True, default='')
    is_active = models.BooleanField(default=True)

    class Meta:
        unique_together = [('post', 'display_name')]

    def __str__(self) -> str:
        return f"{self.display_name} ({self.post.title})"


class Vote(models.Model):
    voter = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='votes')
    post = models.ForeignKey(Post, on_delete=models.CASCADE, related_name='votes')
    candidate = models.ForeignKey(Candidate, on_delete=models.PROTECT, related_name='votes')
    cast_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=['voter', 'post'], name='unique_vote_per_voter_per_post')
        ]

    def __str__(self) -> str:
        return f"Vote({self.voter.username} -> {self.candidate.display_name} @ {self.post.title})"


class ElectionArchive(models.Model):
    """Snapshot of an election's results and participation (no ballot selections per voter)."""

    election = models.ForeignKey(Election, on_delete=models.CASCADE, related_name='archives')
    created_at = models.DateTimeField(auto_now_add=True)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL)
    note = models.CharField(max_length=255, blank=True, default='')

    # JSON payload containing aggregated results + participation summary.
    data = models.JSONField(default=dict)

    class Meta:
        ordering = ['-created_at', '-id']

    def __str__(self) -> str:
        return f"Archive({self.election.title} @ {self.created_at:%Y-%m-%d %H:%M})"
