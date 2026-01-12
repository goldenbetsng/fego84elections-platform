from __future__ import annotations

from django.http import HttpRequest, HttpResponse
from django.shortcuts import render

from .models import ContentBlock


def get_block(key: str, default_title: str = '', default_body: str = '') -> dict:
    block = ContentBlock.objects.filter(key=key, is_active=True).first()
    if block:
        return {'title': block.title, 'body': block.body}
    return {'title': default_title, 'body': default_body}


def home(request: HttpRequest) -> HttpResponse:
    ctx = {
        'banner': get_block('home_banner', default_title="FEGO '84 Election", default_body=''),
        'scroll': get_block('home_scroll', default_body=''),
        'intro': get_block('home_intro', default_body='Please log in to vote.'),
        'footer': get_block('footer', default_body=''),
    }
    return render(request, 'public/home.html', ctx)


def about(request: HttpRequest) -> HttpResponse:
    ctx = {
        'about': get_block('about', default_title='About Us', default_body=''),
        'footer': get_block('footer', default_body=''),
    }
    return render(request, 'public/about.html', ctx)
