from django.db import models


class ContentBlock(models.Model):
    """Admin-editable content blocks used on public pages.

    Keys we use in templates:
    - home_banner
    - home_scroll
    - home_intro
    - footer
    - about
    """

    key = models.CharField(max_length=50, unique=True)
    title = models.CharField(max_length=200, blank=True, default='')
    body = models.TextField(blank=True, default='')
    is_active = models.BooleanField(default=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self) -> str:
        return self.key
