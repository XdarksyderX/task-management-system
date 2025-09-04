from django.contrib import admin
from django.http import HttpResponse
from django.urls import path, include
from apps.common.views import landing_page, dashboard

def healthz(_): return HttpResponse("ok", content_type="text/plain")

urlpatterns = [
    path("admin/", admin.site.urls),
    path("", landing_page, name="landing"),
    path("dashboard/", dashboard, name="dashboard"),
    path("healthz/", healthz),

    path("auth/", include("apps.users.urls")),
    path("tasks/", include("apps.tasks.urls")),
    path("teams/", include("apps.users.team_urls")),  # For team templates
    path(
        "api/",
        include([
            path("", include("apps.users.api.urls")),  # Direct under /api/
            path("tasks/", include("apps.tasks.api.urls")),
        ])
    ),
]
