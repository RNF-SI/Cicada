"""
URLs pour l'API de suivi des instances
"""
from django.urls import path
from . import views

urlpatterns = [
    path('instances/register/', views.register_instance, name='register_instance'),
    path('instances/heartbeat/', views.heartbeat, name='heartbeat'),
    path('instances/version/', views.check_version, name='check_version'),
    path('instances/me/', views.instance_me, name='instance_me'),
    path('admin/stats/', views.admin_stats, name='admin_stats'),
    path('admin/instances/', views.admin_instances, name='admin_instances'),
]
