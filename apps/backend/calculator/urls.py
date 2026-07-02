from django.urls import path
from . import views

urlpatterns = [
    path('', views.calculator_view, name='calculator'),
    path('result/', views.calculator_result_view, name='calculator_result'),
]
