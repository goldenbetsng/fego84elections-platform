from django.urls import path
from . import views_voter

urlpatterns = [
    path('', views_voter.dashboard, name='voter_dashboard'),
    path('post/<int:post_id>/', views_voter.vote_post, name='vote_post'),
]
