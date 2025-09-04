from django.urls import path
from .team_views import team_list, team_detail, team_create, team_edit

urlpatterns = [
    path("", team_list, name="team_list"),
    path("create/", team_create, name="team_create"),
    path("<int:team_id>/", team_detail, name="team_detail"),
    path("<int:team_id>/edit/", team_edit, name="team_edit"),
]
