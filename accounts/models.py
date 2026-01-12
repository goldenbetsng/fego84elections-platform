from django.contrib.auth.models import AbstractUser
from django.db import models
from django.db.models.signals import post_save
from django.dispatch import receiver


class User(AbstractUser):
    class Role(models.TextChoices):
        SUPERADMIN = 'SUPERADMIN', 'Super Admin'
        ADMIN = 'ADMIN', 'Admin'
        VOTER = 'VOTER', 'Voter'

    role = models.CharField(max_length=20, choices=Role.choices, default=Role.VOTER)

    def save(self, *args, **kwargs):
        """Keep Django's is_staff/is_superuser consistent with FEGO roles.

        - SUPERADMIN => is_staff=True, is_superuser=True
        - ADMIN      => is_staff=True, is_superuser=False
        - VOTER      => is_staff=False, is_superuser=False
        """
        if self.role == self.Role.SUPERADMIN:
            self.is_staff = True
            self.is_superuser = True
        elif self.role == self.Role.ADMIN:
            self.is_staff = True
            self.is_superuser = False
        else:
            self.is_staff = False
            self.is_superuser = False
        super().save(*args, **kwargs)

    def is_admin_like(self) -> bool:
        return self.role in {self.Role.ADMIN, self.Role.SUPERADMIN}


class VoterProfile(models.Model):
    """Optional per-voter metadata loaded from the register upload."""
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='voter_profile')
    membership_no = models.CharField(max_length=64, blank=True, default='')
    is_candidate = models.BooleanField(default=False)

    def __str__(self) -> str:
        return f"VoterProfile({self.user.username})"


class AdminPermission(models.Model):
    """Fine-grained controls for Admin Members.

    Super Admins have full access regardless of these flags.
    """

    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='admin_permissions')

    can_manage_elections = models.BooleanField(default=False)
    can_manage_posts = models.BooleanField(default=False)
    can_manage_candidates = models.BooleanField(default=False)
    can_manage_voters = models.BooleanField(default=False)
    can_manage_content = models.BooleanField(default=False)
    can_view_audit = models.BooleanField(default=False)
    # Sprint E: allow viewing aggregate results + participation reports
    can_view_results = models.BooleanField(default=False)

    notes = models.CharField(max_length=255, blank=True, default='')

    def __str__(self) -> str:
        return f"AdminPermission({self.user.username})"


@receiver(post_save, sender=User)
def ensure_profiles(sender, instance: User, created: bool, **kwargs):
    """Create required related records for new users."""
    # Ensure voter profile for voters
    if instance.role == User.Role.VOTER:
        VoterProfile.objects.get_or_create(user=instance)

    # Ensure permissions record for admin members
    if instance.role == User.Role.ADMIN:
        AdminPermission.objects.get_or_create(user=instance)
