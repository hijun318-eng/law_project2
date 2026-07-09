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

    path("api/admin/users/toggle-status/", views.admin_toggle_user_status, name="admin_toggle_user_status"),
    path("api/admin/vectordb/rebuild/", views.admin_rebuild_vectordb, name="admin_rebuild_vectordb"),
    path("api/admin/vectordb/reprocess/", views.admin_reprocess_failed, name="admin_reprocess_failed"),
    path("api/admin/performance/", views.admin_performance_data, name="admin_performance_data"),
    path("api/admin/performance/price-config/", views.PriceConfigView.as_view(), name="admin_price_config"),

    path("api/advice/", views.advice_api, name="advice_api"),
    path("api/advice/feedback/", views.feedback_api, name="feedback_api"),
    path("api/advice/history/<int:history_id>/", views.HistoryDetailView.as_view(), name="history_detail_api"),
    path("api/calculate/", views.calculate_api, name="calculate_api"),
    path("api/news/", views.news_api, name="news_api"),
    path("api/news/stream/", views.news_stream_api, name="news_stream_api"),
    path("api/prompts/", views.prompt_api, name="prompt_api"),

]