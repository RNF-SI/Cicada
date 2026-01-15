"""
Admin pour les notifications et validations.
"""
from django.contrib import admin
from django.utils.html import format_html

from .models import Notification, ValidationRequest, PendingUser


@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    """Admin pour les notifications."""

    list_display = [
        'id',
        'recipient',
        'notification_type',
        'title_truncated',
        'priority_badge',
        'read_status',
        'email_status',
        'created_at',
    ]
    list_filter = [
        'notification_type',
        'priority',
        'read',
        'email_sent',
        'created_at',
    ]
    search_fields = [
        'recipient__email',
        'recipient__nom_role',
        'title',
        'message',
    ]
    readonly_fields = [
        'created_at',
        'read_at',
        'email_sent_at',
    ]
    ordering = ['-created_at']
    date_hierarchy = 'created_at'

    fieldsets = (
        ('Destinataire', {
            'fields': ('recipient',)
        }),
        ('Contenu', {
            'fields': ('notification_type', 'title', 'message', 'priority')
        }),
        ('Objets lies', {
            'fields': (
                'related_user',
                'related_site',
                'related_plan',
                'related_organisme',
                'related_validation',
            ),
            'classes': ('collapse',)
        }),
        ('Action', {
            'fields': ('action_url',)
        }),
        ('Statut', {
            'fields': ('read', 'read_at', 'email_sent', 'email_sent_at')
        }),
        ('Metadata', {
            'fields': ('created_at', 'expires_at'),
            'classes': ('collapse',)
        }),
    )

    def title_truncated(self, obj):
        """Titre tronque."""
        if len(obj.title) > 50:
            return obj.title[:50] + '...'
        return obj.title
    title_truncated.short_description = 'Titre'

    def priority_badge(self, obj):
        """Badge de priorite."""
        colors = {
            'low': '#82DB8A',
            'medium': '#F7D35C',
            'high': '#FA9965',
            'critical': '#FF7579',
        }
        color = colors.get(obj.priority, '#999')
        return format_html(
            '<span style="background-color: {}; padding: 2px 8px; border-radius: 4px; color: #333;">{}</span>',
            color,
            obj.get_priority_display()
        )
    priority_badge.short_description = 'Priorite'

    def read_status(self, obj):
        """Statut de lecture."""
        if obj.read:
            return format_html(
                '<span style="color: green;">✓ Lu</span>'
            )
        return format_html(
            '<span style="color: orange;">○ Non lu</span>'
        )
    read_status.short_description = 'Lu'

    def email_status(self, obj):
        """Statut d'envoi email."""
        if obj.email_sent:
            return format_html(
                '<span style="color: green;">✉ Envoye</span>'
            )
        return format_html(
            '<span style="color: gray;">-</span>'
        )
    email_status.short_description = 'Email'


@admin.register(ValidationRequest)
class ValidationRequestAdmin(admin.ModelAdmin):
    """Admin pour les demandes de validation."""

    list_display = [
        'id',
        'request_type',
        'requester_display',
        'target_display',
        'status_badge',
        'validator',
        'created_at',
        'validated_at',
    ]
    list_filter = [
        'request_type',
        'status',
        'created_at',
        'validated_at',
    ]
    search_fields = [
        'requester__email',
        'requester__nom_role',
        'target_site__nom_site',
        'target_plan__nom',
        'justification',
    ]
    readonly_fields = [
        'created_at',
        'updated_at',
        'validated_at',
    ]
    ordering = ['-created_at']
    date_hierarchy = 'created_at'

    fieldsets = (
        ('Type et statut', {
            'fields': ('request_type', 'status')
        }),
        ('Demandeur', {
            'fields': ('requester',)
        }),
        ('Cible', {
            'fields': (
                'target_site',
                'target_plan',
                'target_user',
                'requested_organisme',
                'requested_role_level',
            )
        }),
        ('Details', {
            'fields': ('justification',)
        }),
        ('Validation', {
            'fields': ('validator', 'validation_comment', 'validated_at')
        }),
        ('Metadata', {
            'fields': ('created_at', 'updated_at', 'expires_at'),
            'classes': ('collapse',)
        }),
    )

    actions = ['approve_requests', 'reject_requests']

    def requester_display(self, obj):
        """Affichage du demandeur."""
        if obj.requester:
            return str(obj.requester)
        if obj.request_type == 'user_registration' and hasattr(obj, 'pending_user'):
            return f"(Inscription) {obj.pending_user.get_full_name()}"
        return '-'
    requester_display.short_description = 'Demandeur'

    def target_display(self, obj):
        """Affichage de la cible."""
        if obj.target_site:
            return f"Site: {obj.target_site.nom_site}"
        if obj.target_plan:
            return f"Plan: {obj.target_plan.nom}"
        if obj.target_user:
            return f"Utilisateur: {obj.target_user}"
        if obj.requested_organisme:
            return f"Organisme: {obj.requested_organisme.nom_organisme}"
        return '-'
    target_display.short_description = 'Cible'

    def status_badge(self, obj):
        """Badge de statut."""
        colors = {
            'pending': '#F7D35C',
            'approved': '#82DB8A',
            'rejected': '#FF7579',
            'cancelled': '#999',
            'expired': '#999',
        }
        color = colors.get(obj.status, '#999')
        return format_html(
            '<span style="background-color: {}; padding: 2px 8px; border-radius: 4px; color: #333;">{}</span>',
            color,
            obj.get_status_display()
        )
    status_badge.short_description = 'Statut'

    @admin.action(description='Approuver les demandes selectionnees')
    def approve_requests(self, request, queryset):
        """Action pour approuver en masse."""
        from .services import ValidationService

        count = 0
        for validation_request in queryset.filter(status='pending'):
            try:
                if validation_request.request_type == 'user_registration':
                    ValidationService.approve_registration(
                        validation_request,
                        request.user,
                        'Approuve via admin'
                    )
                elif validation_request.request_type == 'site_access':
                    ValidationService.approve_site_access(
                        validation_request,
                        request.user,
                        'Approuve via admin'
                    )
                elif validation_request.request_type == 'plan_access':
                    ValidationService.approve_plan_access(
                        validation_request,
                        request.user,
                        'Approuve via admin'
                    )
                else:
                    validation_request.approve(request.user, 'Approuve via admin')
                count += 1
            except Exception as e:
                self.message_user(
                    request,
                    f"Erreur pour la demande {validation_request.id}: {e}",
                    level='error'
                )

        self.message_user(request, f"{count} demande(s) approuvee(s).")

    @admin.action(description='Rejeter les demandes selectionnees')
    def reject_requests(self, request, queryset):
        """Action pour rejeter en masse."""
        from .services import ValidationService

        count = 0
        for validation_request in queryset.filter(status='pending'):
            try:
                ValidationService.reject_request(
                    validation_request,
                    request.user,
                    'Rejete via admin'
                )
                count += 1
            except Exception as e:
                self.message_user(
                    request,
                    f"Erreur pour la demande {validation_request.id}: {e}",
                    level='error'
                )

        self.message_user(request, f"{count} demande(s) rejetee(s).")


@admin.register(PendingUser)
class PendingUserAdmin(admin.ModelAdmin):
    """Admin pour les utilisateurs en attente."""

    list_display = [
        'id',
        'email',
        'nom_complet',
        'requested_organisme',
        'validation_status',
        'created_at',
    ]
    list_filter = [
        'requested_organisme',
        'created_at',
    ]
    search_fields = [
        'email',
        'nom_role',
        'prenom_role',
    ]
    readonly_fields = [
        'password_hash',
        'created_at',
        'ip_address',
        'user_agent',
        'validation_request',
    ]
    ordering = ['-created_at']

    def nom_complet(self, obj):
        """Nom complet."""
        return obj.get_full_name()
    nom_complet.short_description = 'Nom complet'

    def validation_status(self, obj):
        """Statut de la demande associee."""
        if obj.validation_request:
            status = obj.validation_request.status
            colors = {
                'pending': '#F7D35C',
                'approved': '#82DB8A',
                'rejected': '#FF7579',
            }
            color = colors.get(status, '#999')
            return format_html(
                '<span style="background-color: {}; padding: 2px 8px; border-radius: 4px;">{}</span>',
                color,
                obj.validation_request.get_status_display()
            )
        return '-'
    validation_status.short_description = 'Statut validation'
