"""
URL configuration for backend project.
"""
from django.contrib import admin
from django.urls import path, include
from . import views
urlpatterns = [
    path("admin/", admin.site.urls),
    path("", views.landing, name="landing"),
    path("login/", views.login_view, name="login"),
    path("register/", views.register_view, name="register"),
    path("logout/", views.logout_view, name="logout"),
    path("app/", views.user_app, name="user_app"),
    path("admin-console/", views.admin_console, name="admin_console"),
    path("example/", views.example, name="example"),
    path("api/advice/", views.advice_api, name="advice_api"),
    path("api/calculate/", views.calculate_api, name="calculate_api"),
    path("api/news/", views.news_api, name="news_api"),
    path("api/prompts/", views.prompt_api, name="prompt_api"),
    path("chat/", include("chat.urls")),
    path("calculator/", include("calculator.urls")),
    path("news/", include("news.urls")),
    path("home/", include("home.urls")),
]