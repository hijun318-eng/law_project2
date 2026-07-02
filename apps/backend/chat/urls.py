from django.urls import path
from . import views

app_name = 'chat'

urlpatterns = [
    path('', views.chat_view, name='chat'),
    path('result/<int:id>/', views.result_view, name='result'),
    path('history/', views.history_view, name='history'),
]
