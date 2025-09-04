from django.contrib import admin
from django.http import HttpResponse
from django.urls import path, include
from apps.common.views import landing_page


def healthz(_): return HttpResponse("ok", content_type="text/plain")

urlpatterns = [
    path("admin/", admin.site.urls),
	path("", landing_page, name="landing"),
    path("healthz/", healthz),
    path("auth/", include("apps.users.web.urls")),
    path("api/auth/", include("apps.users.api.urls")),
]
