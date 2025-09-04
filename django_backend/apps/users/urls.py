from django.urls import path, include
from .views import login_page, register_page

app_name = 'users'

urlpatterns = [
    # Web templates
    path("login/", login_page, name="login"),
    path("register/", register_page, name="register"),
]
