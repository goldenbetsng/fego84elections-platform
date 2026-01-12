from __future__ import annotations

from django.contrib import messages
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.http import HttpRequest, HttpResponse
from django.shortcuts import redirect, render

from .models import User


def login_view(request: HttpRequest) -> HttpResponse:
    if request.user.is_authenticated:
        # Send voters to dashboard, admins to Django admin
        if getattr(request.user, 'role', User.Role.VOTER) == User.Role.VOTER:
            return redirect('voter_dashboard')
        return redirect('/admin/')

    if request.method == 'POST':
        username = request.POST.get('username', '').strip()
        password = request.POST.get('password', '')
        user = authenticate(request, username=username, password=password)
        if user is None:
            messages.error(request, 'Invalid username or password.')
        else:
            # Enforce voter register gating: only active users
            if not user.is_active:
                messages.error(request, 'Your account is inactive. Contact the administrator.')
            else:
                login(request, user)
                if getattr(user, 'role', User.Role.VOTER) == User.Role.VOTER:
                    return redirect('voter_dashboard')
                return redirect('/admin/')

    return render(request, 'registration/login.html')


@login_required
def logout_view(request: HttpRequest) -> HttpResponse:
    logout(request)
    return redirect('home')
