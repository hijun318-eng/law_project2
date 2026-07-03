from django.urls import path
from . import views

app_name = 'calculator'

urlpatterns = [
    path('', views.calculator_view, name='calculator'),
    path('result/', views.calculator_result_view, name='calculator_result'),
]
