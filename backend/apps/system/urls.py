"""
URLs pour l'interface d'administration système
"""
from django.urls import path
from . import views

urlpatterns = [
    path('', views.system_info, name='system_info'),
    path('trigger-update/', views.trigger_update, name='trigger_update'),
    path('withdraw-consent/', views.withdraw_consent, name='withdraw_consent'),
]
