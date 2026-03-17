"""
Interface d'administration pour les instances
"""
from django.contrib import admin
from .models import Instance, Heartbeat


@admin.register(Instance)
class InstanceAdmin(admin.ModelAdmin):
    list_display = ('token_short', 'version', 'last_heartbeat', 'is_active', 
                    'structure_name', 'rgpd_consent')
    list_filter = ('is_active', 'version', 'rgpd_consent', 'last_heartbeat')
    search_fields = ('token', 'admin_email', 'structure_name')
    readonly_fields = ('token', 'first_seen', 'created_at', 'updated_at')
    
    def token_short(self, obj):
        return str(obj.token)[:8] + '...'
    token_short.short_description = 'Token'


@admin.register(Heartbeat)
class HeartbeatAdmin(admin.ModelAdmin):
    list_display = ('instance', 'timestamp', 'version', 'ip_address')
    list_filter = ('timestamp', 'version')
    readonly_fields = ('instance', 'timestamp', 'version', 'ip_address')
