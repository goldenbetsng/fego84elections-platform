from __future__ import annotations

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import HttpRequest, HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone

from accounts.models import User
from .models import Election, Post, Candidate, Vote
from auditlog.utils import log_event


def get_current_election() -> Election | None:
    """Return the most relevant election for the voter dashboard.

    Prefer OPEN elections. If none are OPEN, allow the newest election that has
    at least one post explicitly OPEN (used for tie-break rounds).
    """
    open_election = Election.objects.filter(status=Election.Status.OPEN).order_by('-created_at').first()
    if open_election:
        return open_election

    # Fall back to newest election that has any post with status OPEN.
    return (
        Election.objects.filter(posts__status=Post.Status.OPEN, posts__is_active=True)
        .order_by('-created_at')
        .distinct()
        .first()
    )


@login_required
def dashboard(request: HttpRequest) -> HttpResponse:
    if getattr(request.user, 'role', User.Role.VOTER) != User.Role.VOTER:
        return redirect('/admin/')

    election = get_current_election()
    if not election:
        messages.info(request, 'No open election at the moment.')
        return render(request, 'voter/dashboard.html', {'election': None, 'post_rows': []})

    posts = election.posts.filter(is_active=True)
    vote_map = {
        v.post_id: v
        for v in Vote.objects.filter(voter=request.user, post__in=posts)
        .select_related('candidate')
    }

    post_rows = [{'post': p, 'vote': vote_map.get(p.id)} for p in posts]

    ctx = {
        'election': election,
        'post_rows': post_rows,
        'now': timezone.now(),
        'is_open_now': election.is_open_now(),
    }
    return render(request, 'voter/dashboard.html', ctx)


@login_required
def vote_post(request: HttpRequest, post_id: int) -> HttpResponse:
    if getattr(request.user, 'role', User.Role.VOTER) != User.Role.VOTER:
        return redirect('/admin/')

    post = get_object_or_404(Post, id=post_id, is_active=True)
    election = post.election

    # Voting window enforcement (server-side)
    if not post.is_open_now():
        messages.error(request, 'Voting is not open for this category.')
        return redirect('voter_dashboard')

    # Candidate restriction: candidate cannot vote in their own post
    is_candidate_here = Candidate.objects.filter(post=post, user=request.user, is_active=True).exists()
    if is_candidate_here:
        messages.error(request, 'You cannot vote in a category where you are standing as a candidate.')
        return redirect('voter_dashboard')

    existing_vote = Vote.objects.filter(voter=request.user, post=post).select_related('candidate').first()
    candidates = post.candidates.filter(is_active=True)

    if request.method == 'POST':
        if existing_vote:
            messages.error(request, 'You have already voted in this category. Votes cannot be changed.')
            return redirect('vote_post', post_id=post.id)

        candidate_id = request.POST.get('candidate_id')
        candidate = candidates.filter(id=candidate_id).first()
        if not candidate:
            messages.error(request, 'Please select a valid candidate.')
            return redirect('vote_post', post_id=post.id)

        vote = Vote.objects.create(voter=request.user, post=post, candidate=candidate)
        log_event(actor=request.user, event_type='VOTE_CAST', metadata={
            'election_id': election.id,
            'post_id': post.id,
            'candidate_id': candidate.id,
        })
        messages.success(request, f'Vote recorded for {candidate.display_name}.')
        return redirect('voter_dashboard')

    return render(request, 'voter/vote_post.html', {
        'election': election,
        'post': post,
        'candidates': candidates,
        'existing_vote': existing_vote,
    })
