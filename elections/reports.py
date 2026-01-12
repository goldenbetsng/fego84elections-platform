from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List

from django.db.models import Count

from .models import Election, Post, Vote


@dataclass
class CandidateResult:
    candidate_id: int
    display_name: str
    votes: int


@dataclass
class PostResults:
    post: Post
    total_votes: int
    candidate_results: List[CandidateResult]
    is_tie: bool
    tied_candidate_ids: List[int]


def compute_post_results(post: Post) -> PostResults:
    qs = (
        Vote.objects.filter(post=post)
        .values("candidate_id", "candidate__display_name")
        .annotate(votes=Count("id"))
        .order_by("-votes", "candidate__display_name")
    )
    candidate_results = [
        CandidateResult(
            candidate_id=row["candidate_id"],
            display_name=row["candidate__display_name"],
            votes=row["votes"],
        )
        for row in qs
    ]
    total_votes = sum(cr.votes for cr in candidate_results)
    is_tie = False
    tied_candidate_ids: List[int] = []
    if candidate_results:
        top_votes = candidate_results[0].votes
        tied = [cr for cr in candidate_results if cr.votes == top_votes]
        if len(tied) > 1:
            is_tie = True
            tied_candidate_ids = [cr.candidate_id for cr in tied]

    return PostResults(
        post=post,
        total_votes=total_votes,
        candidate_results=candidate_results,
        is_tie=is_tie,
        tied_candidate_ids=tied_candidate_ids,
    )


def compute_election_results(election: Election) -> List[PostResults]:
    posts = election.posts.filter(is_active=True).order_by("display_order", "id")
    return [compute_post_results(p) for p in posts]


def results_as_dict(election: Election) -> Dict[str, Any]:
    """JSON-safe results structure for archiving."""
    out: Dict[str, Any] = {
        "election_id": election.id,
        "election_title": election.title,
        "posts": [],
    }
    for pr in compute_election_results(election):
        out["posts"].append(
            {
                "post_id": pr.post.id,
                "post_title": pr.post.title,
                "is_tiebreak": pr.post.is_tiebreak,
                "parent_post_id": pr.post.parent_post_id,
                "total_votes": pr.total_votes,
                "is_tie": pr.is_tie,
                "tied_candidate_ids": pr.tied_candidate_ids,
                "candidates": [
                    {
                        "candidate_id": cr.candidate_id,
                        "display_name": cr.display_name,
                        "votes": cr.votes,
                    }
                    for cr in pr.candidate_results
                ],
            }
        )
    return out
