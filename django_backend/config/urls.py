from django.contrib import admin
from django.http import HttpResponse
from django.urls import path, include
from django.shortcuts import render
from apps.common.views import (
    landing_page, dashboard,
    analytics_index, analytics_dashboard, analytics_tasks_distribution,
    analytics_user_stats, analytics_team_performance, analytics_reports
)
from apps.common.jwks_views import jwks_endpoint, public_key_endpoint

def healthz(_): return HttpResponse("ok", content_type="text/plain")

# Custom error views
def custom_404(request, exception):
    return render(request, '404.html', status=404)

def custom_500(request):
    return render(request, '500.html', status=500)

def custom_403(request, exception):
    return render(request, '403.html', status=403)

# Test views for error pages (remove in production)
def test_404(request):
    from django.http import Http404
    raise Http404("Test 404 error")

def test_500(request):
    raise Exception("Test 500 error")

def test_403(request):
    from django.core.exceptions import PermissionDenied
    raise PermissionDenied("Test 403 error")

urlpatterns = [
    path("admin/", admin.site.urls),
    path("", landing_page, name="landing"),
    path("dashboard/", dashboard, name="dashboard"),
    path("healthz/", healthz),

    # Analytics URLs
    path("analytics/", analytics_index, name="analytics_index"),
    path("analytics/dashboard/", analytics_dashboard, name="analytics_dashboard"),
    path("analytics/tasks/", analytics_tasks_distribution, name="analytics_tasks_distribution"),
    path("analytics/user-stats/", analytics_user_stats, name="analytics_user_stats"),
    path("analytics/team-performance/", analytics_team_performance, name="analytics_team_performance"),
    path("analytics/reports/", analytics_reports, name="analytics_reports"),

    # JWKS endpoints for JWT public key distribution
    path(".well-known/jwks.json", jwks_endpoint, name="jwks"),
    path("api/auth/public-key/", public_key_endpoint, name="public-key"),

    # Test error pages (remove in production)
    path("test/404/", test_404, name="test_404"),
    path("test/500/", test_500, name="test_500"),
    path("test/403/", test_403, name="test_403"),

    path("auth/", include("apps.users.urls")),
    path("tasks/", include("apps.tasks.urls")),
    path("teams/", include("apps.users.urls")),  # For team templates
    path(
        "api/",
        include([
            path("", include("apps.users.api.urls")),
            path("", include("apps.tasks.api.urls")),
        ])
    ),
]

# Error handlers
handler404 = custom_404
handler500 = custom_500
handler403 = custom_403
