from django.test import TestCase
from django.utils import timezone
from django.db import IntegrityError

from accounts.models import User
from .models import Election, Post, Candidate, Vote


class VotingRulesTests(TestCase):
    def setUp(self):
        self.voter = User.objects.create_user(username='v1', password='pass123', role=User.Role.VOTER)
        self.election = Election.objects.create(title='Test Election', status=Election.Status.OPEN, start_at=timezone.now() - timezone.timedelta(hours=1), end_at=timezone.now() + timezone.timedelta(hours=1))
        self.post = Post.objects.create(election=self.election, title='President', display_order=1)
        self.c1 = Candidate.objects.create(post=self.post, display_name='Alice')
        self.c2 = Candidate.objects.create(post=self.post, display_name='Bob')

    def test_one_vote_per_post(self):
        Vote.objects.create(voter=self.voter, post=self.post, candidate=self.c1)
        with self.assertRaises(IntegrityError):
            # Unique constraint must fail
            Vote.objects.create(voter=self.voter, post=self.post, candidate=self.c2)
