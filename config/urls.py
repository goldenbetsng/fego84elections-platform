from django.contrib import admin
from django.urls import path, include

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', include('content_blocks.urls')),
    path('accounts/', include('accounts.urls')),
    path('voter/', include('elections.urls_voter')),
]
