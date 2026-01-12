from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple

from django.utils import timezone

from accounts.models import User
from .models import Election, Post, Vote


@dataclass
class ParticipationCell:
    voted: bool
    cast_at: Optional[str]


@dataclass
class ParticipationRow:
    user: User
    by_post: Dict[int, ParticipationCell]


def build_participation_rows(election: Election, voters: List[User], posts: List[Post]) -> List[ParticipationRow]:
    """Build per-voter participation without exposing ballot selections."""
    votes = (
        Vote.objects.filter(post__election=election, voter__in=voters)
        .values("voter_id", "post_id", "cast_at")
    )
    vote_map: Dict[Tuple[int, int], str] = {
        (v["voter_id"], v["post_id"]): v["cast_at"].astimezone(timezone.get_current_timezone()).isoformat(timespec="seconds")
        for v in votes
    }

    rows: List[ParticipationRow] = []
    for u in voters:
        by_post: Dict[int, ParticipationCell] = {}
        for p in posts:
            cast_at = vote_map.get((u.id, p.id))
            by_post[p.id] = ParticipationCell(voted=bool(cast_at), cast_at=cast_at)
        rows.append(ParticipationRow(user=u, by_post=by_post))
    return rows


def participation_as_dict(election: Election) -> dict:
    posts = list(election.posts.filter(is_active=True).order_by("display_order", "id"))
    voters = list(User.objects.filter(role=User.Role.VOTER, is_active=True).order_by("username"))
    rows = build_participation_rows(election, voters, posts)
    return {
        "election_id": election.id,
        "election_title": election.title,
        "posts": [{"id": p.id, "title": p.title} for p in posts],
        "voters": [
            {
                "user_id": r.user.id,
                "username": r.user.username,
                "first_name": r.user.first_name,
                "last_name": r.user.last_name,
                "cells": {
                    str(post_id): {"voted": cell.voted, "cast_at": cell.cast_at}
                    for post_id, cell in r.by_post.items()
                },
            }
            for r in rows
        ],
    }
