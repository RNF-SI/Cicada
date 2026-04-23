"""
Seeder pour les notifications.
"""
from datetime import timedelta
from typing import Any, Dict, List

from django.utils import timezone

from apps.notifications.models import Notification
from apps.plans.models import PlanGestion
from apps.users.models import BibOrganismes, Role, Site

from .base import BaseSeeder


class NotificationsSeeder(BaseSeeder):
    """
    Crée des notifications de test.

    Types de notifications:
    - validation_request
    - validation_approved
    - validation_rejected
    - user_associated_site
    - user_associated_plan
    - user_removed_site
    - user_removed_plan
    - account_deactivated
    - account_activated
    - organisme_changed
    - organisme_no_admin
    - site_orphaned
    - welcome
    - info
    - system_alert
    """

    name = 'notifications'
    dependencies = ['users', 'sites', 'plans', 'organismes', 'validation_requests']

    def _get_notifications_data(
        self,
        users: List[Role],
        sites: List[Site],
        plans: List[PlanGestion],
        organismes: List[BibOrganismes]
    ) -> List[Dict]:
        """Retourne les données des notifications."""
        admin = users[0]
        admin_rnf = users[1]
        admin_cen = users[2]
        referent_camargue = users[3]
        referent_vercors = users[4]
        user_rnf = users[5]
        user_cen = users[6]

        return [
            # Notifications pour admin_rnf
            {
                'recipient': admin_rnf,
                'notification_type': 'validation_request',
                'title': "Nouvelle demande d'inscription",
                'message': 'Marc Lefebvre souhaite rejoindre votre organisme RNF. Veuillez examiner sa demande.',
                'priority': 'high',
                'action_url': '/administration/validations',
                'read': False,
            },
            {
                'recipient': admin_rnf,
                'notification_type': 'validation_request',
                'title': "Demande d'accès au plan Camargue",
                'message': "Emma Durand demande l'accès au plan de gestion 2020-2030 de la Camargue.",
                'priority': 'medium',
                'related_user': user_rnf,
                'related_plan': plans[0],
                'action_url': '/administration/validations',
                'read': False,
            },
            {
                'recipient': admin_rnf,
                'notification_type': 'info',
                'title': 'Plan de gestion mis à jour',
                'message': "Le plan Aiguilles Rouges a été modifié par l'équipe.",
                'priority': 'low',
                'related_plan': plans[1],
                'read': True,
            },
            {
                'recipient': admin_rnf,
                'notification_type': 'system_alert',
                'title': 'Maintenance prévue',
                'message': 'Une maintenance est prévue le 15 janvier 2026 de 2h à 4h.',
                'priority': 'medium',
                'read': True,
            },

            # Notifications pour admin_cen
            {
                'recipient': admin_cen,
                'notification_type': 'validation_request',
                'title': "Nouvelle demande d'inscription",
                'message': 'Léa Simon souhaite rejoindre votre organisme CEN AURA.',
                'priority': 'high',
                'action_url': '/administration/validations',
                'read': False,
            },
            {
                'recipient': admin_cen,
                'notification_type': 'validation_approved',
                'title': 'Demande approuvée',
                'message': "L'accès de Thomas Leroy au site du Vercors a été approuvé.",
                'priority': 'low',
                'related_user': user_cen,
                'related_site': sites[3],
                'read': True,
            },
            {
                'recipient': admin_cen,
                'notification_type': 'organisme_no_admin',
                'title': 'Attention : admin manquant',
                'message': "Suite au départ de Claire Dubois, votre organisme n'a plus qu'un seul administrateur.",
                'priority': 'critical',
                'related_organisme': organismes[1],
                'read': False,
            },

            # Notifications pour referent_camargue
            {
                'recipient': referent_camargue,
                'notification_type': 'user_associated_site',
                'title': 'Nouvel utilisateur sur votre site',
                'message': 'Un nouvel utilisateur a été ajouté au site de la Camargue.',
                'priority': 'medium',
                'related_site': sites[0],
                'read': False,
            },
            {
                'recipient': referent_camargue,
                'notification_type': 'info',
                'title': 'Rappel : bilan annuel',
                'message': 'Le bilan annuel du plan de gestion doit être soumis avant le 31 mars.',
                'priority': 'high',
                'related_plan': plans[0],
                'read': False,
            },

            # Notifications pour referent_vercors
            {
                'recipient': referent_vercors,
                'notification_type': 'validation_approved',
                'title': 'Vous êtes référent !',
                'message': 'Votre demande pour devenir référent du Marais de Brouage a été approuvée.',
                'priority': 'high',
                'related_site': sites[4],
                'read': True,
            },

            # Notifications pour user_rnf
            {
                'recipient': user_rnf,
                'notification_type': 'info',
                'title': 'Bienvenue !',
                'message': "Bienvenue sur la plateforme de gestion des plans. N'hésitez pas à explorer.",
                'priority': 'low',
                'read': True,
            },
            {
                'recipient': user_rnf,
                'notification_type': 'validation_rejected',
                'title': 'Demande refusée',
                'message': "Votre demande d'accès au plan Aiguilles Rouges a été refusée. Contactez votre administrateur.",
                'priority': 'medium',
                'related_plan': plans[1],
                'read': False,
            },

            # Notifications pour user_cen
            {
                'recipient': user_cen,
                'notification_type': 'user_associated_plan',
                'title': 'Accès accordé',
                'message': 'Vous avez maintenant accès au plan de gestion du Grand-Voyeux.',
                'priority': 'medium',
                'related_plan': plans[2],
                'read': True,
            },

            # Notifications pour super_admin
            {
                'recipient': admin,
                'notification_type': 'system_alert',
                'title': 'Rapport hebdomadaire',
                'message': '5 nouvelles inscriptions cette semaine. 3 plans mis à jour.',
                'priority': 'low',
                'read': True,
            },
            {
                'recipient': admin,
                'notification_type': 'site_orphaned',
                'title': 'Site sans gestionnaire',
                'message': "Le site de Scandola n'a plus d'utilisateur référent assigné.",
                'priority': 'critical',
                'related_site': sites[5],
                'read': False,
            },

            # Notifications additionnelles
            {
                'recipient': user_cen,
                'notification_type': 'welcome',
                'title': 'Bienvenue sur CICADA !',
                'message': 'Votre compte a été activé. Vous pouvez maintenant accéder à toutes les fonctionnalités de la plateforme.',
                'priority': 'medium',
                'read': True,
            },
            {
                'recipient': user_rnf,
                'notification_type': 'user_removed_site',
                'title': 'Accès retiré',
                'message': "Votre accès au site du Lac de Remoray a été retiré par l'administrateur.",
                'priority': 'medium',
                'related_site': sites[6],
                'read': False,
            },
            {
                'recipient': referent_vercors,
                'notification_type': 'user_removed_plan',
                'title': 'Retrait du plan de gestion',
                'message': "Vous n'êtes plus référent du plan de gestion 2018-2028 des Aiguilles Rouges.",
                'priority': 'medium',
                'related_plan': plans[1],
                'read': True,
            },
            {
                'recipient': admin_rnf,
                'notification_type': 'account_deactivated',
                'title': 'Compte utilisateur désactivé',
                'message': 'Le compte de Jean Martin (ancien.rnf@test.fr) a été désactivé suite à son départ.',
                'priority': 'high',
                'read': True,
            },
            {
                'recipient': admin_cen,
                'notification_type': 'account_activated',
                'title': 'Compte utilisateur réactivé',
                'message': "Le compte de Marie Dupont a été réactivé après vérification de son identité.",
                'priority': 'medium',
                'read': False,
            },
            {
                'recipient': user_rnf,
                'notification_type': 'organisme_changed',
                'title': 'Votre organisme a été modifié',
                'message': 'Votre organisme a été changé de "CEN AURA" vers "RNF" suite à votre mutation.',
                'priority': 'high',
                'related_organisme': organismes[0],
                'action_url': '/profile',
                'read': False,
            },

            # Notification: nouveau membre ajouté au plan (pour les référents)
            {
                'recipient': referent_camargue,
                'notification_type': 'info',
                'title': f'Nouvel utilisateur sur le plan {plans[0].nom}',
                'message': f'Emma Durand a été ajoutée comme membre du plan de gestion {plans[0].nom}.',
                'priority': 'low',
                'related_plan': plans[0],
                'related_user': user_rnf,
                'action_url': f'/plans/{plans[0].slug or plans[0].id_pg}',
                'read': False,
            },
            {
                'recipient': admin,
                'notification_type': 'info',
                'title': f'Nouvel utilisateur sur le plan {plans[0].nom}',
                'message': f'Emma Durand a été ajoutée comme membre du plan de gestion {plans[0].nom}.',
                'priority': 'low',
                'related_plan': plans[0],
                'related_user': user_rnf,
                'action_url': f'/plans/{plans[0].slug or plans[0].id_pg}',
                'read': True,
            },

            # Notification: site validé pour un plan (pour les référents)
            {
                'recipient': referent_camargue,
                'notification_type': 'info',
                'title': f'Site lié au plan {plans[0].nom}',
                'message': f'Le site {sites[4].nom_site} a été lié au plan de gestion {plans[0].nom}.',
                'priority': 'medium',
                'related_plan': plans[0],
                'related_site': sites[4],
                'action_url': f'/plans/{plans[0].slug or plans[0].id_pg}',
                'read': False,
            },
        ]

    def seed(self) -> List[Notification]:
        """
        Crée les notifications de test.

        Returns:
            Liste des Notification créées
        """
        self.log_header('Création des notifications')

        users = self.context.require('users')
        sites = self.context.require('sites')
        plans = self.context.require('plans')
        organismes = self.context.require('organismes')

        notifications_data = self._get_notifications_data(users, sites, plans, organismes)

        notifications = []
        for notif_data in notifications_data:
            is_read = notif_data.pop('read', False)

            notif, created = Notification.objects.get_or_create(
                recipient=notif_data['recipient'],
                notification_type=notif_data['notification_type'],
                title=notif_data['title'],
                defaults={
                    'message': notif_data['message'],
                    'priority': notif_data['priority'],
                    'related_user': notif_data.get('related_user'),
                    'related_site': notif_data.get('related_site'),
                    'related_plan': notif_data.get('related_plan'),
                    'related_organisme': notif_data.get('related_organisme'),
                    'action_url': notif_data.get('action_url'),
                    'read': is_read,
                    'read_at': timezone.now() if is_read else None,
                    'expires_at': timezone.now() + timedelta(days=30),
                }
            )
            notifications.append(notif)

            status = "créé" if created else "existant"
            read_status = "[LU]" if is_read else "[NON LU]"
            self.log_item(status, f"{notif.notification_type} -> {notif.recipient.email} {read_status}")

        self.log_summary(len(notifications), 'notifications')
        self.context.set('notifications', notifications)
        return notifications

    def reset(self) -> int:
        """
        Supprime les notifications de test.

        Returns:
            Nombre de Notification supprimées
        """
        return Notification.objects.all().delete()[0]

    def get_dry_run_summary(self) -> List[str]:
        """
        Résumé des notifications qui seraient créées.

        Returns:
            Liste des lignes du résumé
        """
        return [
            '\nNotifications (24):',
            '  Types: validation_request, validation_approved, validation_rejected,',
            '         user_associated_site, user_associated_plan, user_removed_site,',
            '         user_removed_plan, account_deactivated, account_activated,',
            '         organisme_changed, organisme_no_admin, site_orphaned,',
            '         welcome, info, system_alert',
            '  Priorités: low, medium, high, critical',
            '\nRépartition par utilisateur:',
            '    - admin@test.fr:              3 notifications (1 non lue)',
            '    - admin.rnf@test.fr:          4 notifications (2 non lues)',
            '    - admin.cen@test.fr:          3 notifications (2 non lues)',
            '    - referent.camargue@test.fr:  4 notifications (4 non lues)',
            '    - referent.vercors@test.fr:   2 notifications (0 non lues)',
            '    - user.rnf@test.fr:           4 notifications (2 non lues)',
            '    - user.cen@test.fr:           2 notifications (0 non lues)',
        ]
