"""
Seeder pour les logs d'activité.
"""
from datetime import timedelta
from typing import Any, Dict, List

from django.utils import timezone

from apps.core.models import ActivityLog
from apps.notifications.models import ValidationRequest
from apps.plans.models import PlanGestion
from apps.users.models import BibOrganismes, Role, Site

from .base import BaseSeeder


class ActivityLogsSeeder(BaseSeeder):
    """
    Crée des logs d'activité de test.

    Visibilités:
    - public: activités normales (create, update, add_member, etc.)
    - admin: activités de validation
    - system: activités RGPD et alertes système

    Actions:
    - create, update, delete
    - add_member, remove_member
    - add_referent, remove_referent
    - activate, deactivate
    - file_upload
    - validation_approved, validation_rejected
    - rgpd_request, rgpd_cancelled, rgpd_anonymized
    - status_change
    """

    name = 'activity_logs'
    dependencies = ['users', 'sites', 'plans', 'organismes', 'validation_requests']

    def _get_activity_logs_data(
        self,
        users: List[Role],
        sites: List[Site],
        plans: List[PlanGestion],
        organismes: List[BibOrganismes],
        validation_requests: List[ValidationRequest]
    ) -> List[Dict]:
        """Retourne les données des logs d'activité."""
        now = timezone.now()

        super_admin = users[0]
        admin_rnf = users[1]
        admin_cen = users[2]
        ref_camargue = users[3]
        ref_vercors = users[4]
        user_rnf = users[5]
        user_cen = users[6]

        site_camargue = sites[0] if len(sites) > 0 else None
        site_vercors = sites[3] if len(sites) > 3 else None
        site_aiguilles = sites[1] if len(sites) > 1 else None

        plan1 = plans[0] if len(plans) > 0 else None
        plan2 = plans[1] if len(plans) > 1 else None

        org_rnf = organismes[0] if len(organismes) > 0 else None
        org_cen = organismes[1] if len(organismes) > 1 else None

        return [
            # ACTIVITÉS RGPD (visibility='system')
            {
                'entity_type': 'user',
                'entity_id': user_rnf.id_role,
                'entity_name': user_rnf.get_full_name() or user_rnf.email,
                'actor': user_rnf,
                'actor_name': user_rnf.get_full_name() or user_rnf.email,
                'action': 'rgpd_request',
                'description': f"{user_rnf.email} a demandé la suppression de son compte",
                'related_user': user_rnf,
                'related_organisme': org_rnf,
                'metadata': {'reason': 'Ne souhaite plus utiliser le service', 'grace_period_days': 30},
                'visibility': 'system',
                'created_at': now - timedelta(days=25),
            },
            {
                'entity_type': 'user',
                'entity_id': user_cen.id_role,
                'entity_name': user_cen.get_full_name() or user_cen.email,
                'actor': user_cen,
                'actor_name': user_cen.get_full_name() or user_cen.email,
                'action': 'rgpd_request',
                'description': f"{user_cen.email} a demandé la suppression de son compte",
                'related_user': user_cen,
                'related_organisme': org_cen,
                'metadata': {'reason': 'Changement de poste'},
                'visibility': 'system',
                'created_at': now - timedelta(days=15),
            },
            {
                'entity_type': 'user',
                'entity_id': user_cen.id_role,
                'entity_name': user_cen.get_full_name() or user_cen.email,
                'actor': user_cen,
                'actor_name': user_cen.get_full_name() or user_cen.email,
                'action': 'rgpd_cancelled',
                'description': f"{user_cen.email} a annulé sa demande de suppression de compte",
                'related_user': user_cen,
                'related_organisme': org_cen,
                'metadata': {'cancelled_after_days': 5},
                'visibility': 'system',
                'created_at': now - timedelta(days=10),
            },
            {
                'entity_type': 'user',
                'entity_id': 99999,
                'entity_name': 'Utilisateur anonymisé #99999',
                'actor': None,
                'actor_name': 'Système',
                'action': 'rgpd_anonymized',
                'description': "Compte utilisateur anonymisé suite à l'expiration du délai de grâce RGPD",
                'related_user': None,
                'related_organisme': org_rnf,
                'metadata': {'original_email_hash': 'sha256:abc123...', 'anonymized_fields': ['email', 'nom', 'prenom']},
                'visibility': 'system',
                'created_at': now - timedelta(days=60),
            },

            # ALERTES SYSTÈME (visibility='system')
            {
                'entity_type': 'site',
                'entity_id': site_aiguilles.id_site if site_aiguilles else 1,
                'entity_name': site_aiguilles.nom_site if site_aiguilles else 'Site orphelin',
                'actor': None,
                'actor_name': 'Système',
                'action': 'status_change',
                'description': "Alerte : site sans utilisateurs actifs détecté (site orphelin)",
                'related_site': site_aiguilles,
                'related_organisme': org_rnf,
                'metadata': {'alert_type': 'site_orphaned', 'last_user_removed_at': str(now - timedelta(days=5))},
                'visibility': 'system',
                'created_at': now - timedelta(days=5),
            },
            {
                'entity_type': 'organisme',
                'entity_id': org_cen.id_organisme if org_cen else 1,
                'entity_name': org_cen.nom_organisme if org_cen else 'Organisme test',
                'actor': None,
                'actor_name': 'Système',
                'action': 'status_change',
                'description': "Alerte : organisme sans administrateur détecté",
                'related_organisme': org_cen,
                'metadata': {'alert_type': 'organisme_no_admin', 'previous_admin_deactivated_at': str(now - timedelta(days=7))},
                'visibility': 'system',
                'created_at': now - timedelta(days=7),
            },
            {
                'entity_type': 'user',
                'entity_id': super_admin.id_role,
                'entity_name': super_admin.get_full_name() or super_admin.email,
                'actor': None,
                'actor_name': 'Système',
                'action': 'status_change',
                'description': "Maintenance système : nettoyage des tokens expirés effectué",
                'related_user': None,
                'metadata': {'maintenance_type': 'token_cleanup', 'tokens_removed': 42},
                'visibility': 'system',
                'created_at': now - timedelta(days=1),
            },

            # ACTIVITÉS DE VALIDATION (visibility='admin')
            {
                'entity_type': 'validation',
                'entity_id': validation_requests[1].id if len(validation_requests) > 1 else 1,
                'entity_name': f"Demande d'accès site - {validation_requests[1].requester.email if len(validation_requests) > 1 and validation_requests[1].requester else 'user@test.fr'}",
                'actor': admin_cen,
                'actor_name': admin_cen.get_full_name() or admin_cen.email,
                'action': 'validation_approved',
                'description': "Demande d'accès au site approuvée par l'administrateur",
                'related_site': validation_requests[1].target_site if len(validation_requests) > 1 else site_vercors,
                'related_organisme': org_cen,
                'metadata': {'request_type': 'site_access', 'response_time_hours': 12},
                'visibility': 'admin',
                'created_at': now - timedelta(days=14),
            },
            {
                'entity_type': 'validation',
                'entity_id': validation_requests[5].id if len(validation_requests) > 5 else 2,
                'entity_name': f"Demande de nomination référent - {validation_requests[5].requester.email if len(validation_requests) > 5 and validation_requests[5].requester else 'referent@test.fr'}",
                'actor': super_admin,
                'actor_name': super_admin.get_full_name() or super_admin.email,
                'action': 'validation_approved',
                'description': "Nomination comme référent approuvée",
                'related_site': validation_requests[5].target_site if len(validation_requests) > 5 else site_camargue,
                'related_organisme': org_rnf,
                'metadata': {'request_type': 'referent_validation', 'as_referent': True},
                'visibility': 'admin',
                'created_at': now - timedelta(days=10),
            },
            {
                'entity_type': 'validation',
                'entity_id': validation_requests[3].id if len(validation_requests) > 3 else 3,
                'entity_name': f"Demande d'accès plan - {validation_requests[3].requester.email if len(validation_requests) > 3 and validation_requests[3].requester else 'user@test.fr'}",
                'actor': admin_rnf,
                'actor_name': admin_rnf.get_full_name() or admin_rnf.email,
                'action': 'validation_rejected',
                'description': "Demande d'accès au plan rejetée - réservée aux membres de l'organisme",
                'related_plan': validation_requests[3].target_plan if len(validation_requests) > 3 else plans[0],
                'related_organisme': org_rnf,
                'metadata': {'request_type': 'plan_access', 'rejection_reason': 'Réservée aux membres RNF'},
                'visibility': 'admin',
                'created_at': now - timedelta(days=8),
            },

            # ACTIVITÉS PUBLIQUES (visibility='public')
            {
                'entity_type': 'site',
                'entity_id': site_camargue.id_site if site_camargue else 1,
                'entity_name': site_camargue.nom_site if site_camargue else 'Camargue',
                'actor': super_admin,
                'actor_name': super_admin.get_full_name() or super_admin.email,
                'action': 'create',
                'description': f"Site '{site_camargue.nom_site if site_camargue else 'Camargue'}' créé",
                'related_site': site_camargue,
                'related_organisme': org_rnf,
                'visibility': 'public',
                'created_at': now - timedelta(days=90),
            },
            {
                'entity_type': 'site',
                'entity_id': site_camargue.id_site if site_camargue else 1,
                'entity_name': site_camargue.nom_site if site_camargue else 'Camargue',
                'actor': ref_camargue,
                'actor_name': ref_camargue.get_full_name() or ref_camargue.email,
                'action': 'update',
                'description': f"Site '{site_camargue.nom_site if site_camargue else 'Camargue'}' mis à jour",
                'related_site': site_camargue,
                'related_organisme': org_rnf,
                'changes': {'surf_off': {'old': '10000', 'new': '12500'}, 'description': {'old': None, 'new': 'Description mise à jour'}},
                'visibility': 'public',
                'created_at': now - timedelta(days=30),
            },
            {
                'entity_type': 'site',
                'entity_id': site_camargue.id_site if site_camargue else 1,
                'entity_name': site_camargue.nom_site if site_camargue else 'Camargue',
                'actor': admin_rnf,
                'actor_name': admin_rnf.get_full_name() or admin_rnf.email,
                'action': 'add_member',
                'description': f"{user_rnf.get_full_name() or user_rnf.email} ajouté au site Camargue",
                'related_site': site_camargue,
                'related_user': user_rnf,
                'related_organisme': org_rnf,
                'metadata': {'member_id': user_rnf.id_role, 'is_referent': False},
                'visibility': 'public',
                'created_at': now - timedelta(days=20),
            },
            {
                'entity_type': 'site',
                'entity_id': site_camargue.id_site if site_camargue else 1,
                'entity_name': site_camargue.nom_site if site_camargue else 'Camargue',
                'actor': admin_rnf,
                'actor_name': admin_rnf.get_full_name() or admin_rnf.email,
                'action': 'add_referent',
                'description': f"{ref_camargue.get_full_name() or ref_camargue.email} nommé référent du site Camargue",
                'related_site': site_camargue,
                'related_user': ref_camargue,
                'related_organisme': org_rnf,
                'metadata': {'referent_id': ref_camargue.id_role},
                'visibility': 'public',
                'created_at': now - timedelta(days=85),
            },
            {
                'entity_type': 'plan',
                'entity_id': plan1.id_pg if plan1 else 1,
                'entity_name': plan1.nom if plan1 else 'Plan de Gestion Test',
                'actor': ref_camargue,
                'actor_name': ref_camargue.get_full_name() or ref_camargue.email,
                'action': 'create',
                'description': f"Plan de gestion '{plan1.nom if plan1 else 'Test'}' créé",
                'related_plan': plan1,
                'related_site': site_camargue,
                'related_organisme': org_rnf,
                'visibility': 'public',
                'created_at': now - timedelta(days=60),
            },
            {
                'entity_type': 'plan',
                'entity_id': plan1.id_pg if plan1 else 1,
                'entity_name': plan1.nom if plan1 else 'Plan de Gestion Test',
                'actor': ref_camargue,
                'actor_name': ref_camargue.get_full_name() or ref_camargue.email,
                'action': 'update',
                'description': f"Plan de gestion '{plan1.nom if plan1 else 'Test'}' mis à jour",
                'related_plan': plan1,
                'related_site': site_camargue,
                'related_organisme': org_rnf,
                'changes': {'statut': {'old': 'draft', 'new': 'valide'}},
                'visibility': 'public',
                'created_at': now - timedelta(days=45),
            },
            {
                'entity_type': 'plan',
                'entity_id': plan2.id_pg if plan2 else 2,
                'entity_name': plan2.nom if plan2 else 'Plan de Gestion 2',
                'actor': admin_cen,
                'actor_name': admin_cen.get_full_name() or admin_cen.email,
                'action': 'add_referent',
                'description': f"{ref_vercors.get_full_name() or ref_vercors.email} nommé référent du plan",
                'related_plan': plan2,
                'related_site': site_vercors,
                'related_user': ref_vercors,
                'related_organisme': org_cen,
                'metadata': {'referent_id': ref_vercors.id_role},
                'visibility': 'public',
                'created_at': now - timedelta(days=40),
            },
            {
                'entity_type': 'user',
                'entity_id': user_rnf.id_role,
                'entity_name': user_rnf.get_full_name() or user_rnf.email,
                'actor': admin_rnf,
                'actor_name': admin_rnf.get_full_name() or admin_rnf.email,
                'action': 'activate',
                'description': f"Compte de {user_rnf.email} activé",
                'related_user': user_rnf,
                'related_organisme': org_rnf,
                'visibility': 'public',
                'created_at': now - timedelta(days=50),
            },
            {
                'entity_type': 'user',
                'entity_id': users[7].id_role if len(users) > 7 else 8,
                'entity_name': users[7].get_full_name() if len(users) > 7 else 'Ancien utilisateur',
                'actor': super_admin,
                'actor_name': super_admin.get_full_name() or super_admin.email,
                'action': 'deactivate',
                'description': "Compte désactivé suite au départ de l'organisme",
                'related_user': users[7] if len(users) > 7 else None,
                'related_organisme': org_rnf,
                'metadata': {'reason': "Départ de l'organisme"},
                'visibility': 'public',
                'created_at': now - timedelta(days=35),
            },
            {
                'entity_type': 'plan',
                'entity_id': plan1.id_pg if plan1 else 1,
                'entity_name': plan1.nom if plan1 else 'Plan de Gestion Test',
                'actor': ref_camargue,
                'actor_name': ref_camargue.get_full_name() or ref_camargue.email,
                'action': 'file_upload',
                'description': "Document 'Rapport_annuel_2024.pdf' téléversé",
                'related_plan': plan1,
                'related_site': site_camargue,
                'related_organisme': org_rnf,
                'metadata': {'filename': 'Rapport_annuel_2024.pdf', 'size_bytes': 2456789, 'type': 'document'},
                'visibility': 'public',
                'created_at': now - timedelta(days=5),
            },
            {
                'entity_type': 'organisme',
                'entity_id': org_rnf.id_organisme if org_rnf else 1,
                'entity_name': org_rnf.nom_organisme if org_rnf else 'RNF',
                'actor': super_admin,
                'actor_name': super_admin.get_full_name() or super_admin.email,
                'action': 'update',
                'description': f"Organisme '{org_rnf.nom_organisme if org_rnf else 'RNF'}' mis à jour",
                'related_organisme': org_rnf,
                'changes': {'adresse': {'old': None, 'new': '57 rue Cuvier, 75005 Paris'}},
                'visibility': 'public',
                'created_at': now - timedelta(days=15),
            },
            # Activités récentes
            {
                'entity_type': 'site',
                'entity_id': site_vercors.id_site if site_vercors else 4,
                'entity_name': site_vercors.nom_site if site_vercors else 'Vercors',
                'actor': ref_vercors,
                'actor_name': ref_vercors.get_full_name() or ref_vercors.email,
                'action': 'update',
                'description': "Site Vercors : mise à jour des coordonnées",
                'related_site': site_vercors,
                'related_organisme': org_cen,
                'changes': {'coord_x': {'old': '5.5', 'new': '5.6'}},
                'visibility': 'public',
                'created_at': now - timedelta(hours=2),
            },
            {
                'entity_type': 'plan',
                'entity_id': plan2.id_pg if plan2 else 2,
                'entity_name': plan2.nom if plan2 else 'Plan Vercors',
                'actor': ref_vercors,
                'actor_name': ref_vercors.get_full_name() or ref_vercors.email,
                'action': 'update',
                'description': "Plan Vercors: Ajout des objectifs 2026",
                'related_plan': plan2,
                'related_site': site_vercors,
                'related_organisme': org_cen,
                'visibility': 'public',
                'created_at': now - timedelta(hours=5),
            },
            {
                'entity_type': 'site',
                'entity_id': site_camargue.id_site if site_camargue else 1,
                'entity_name': site_camargue.nom_site if site_camargue else 'Camargue',
                'actor': user_rnf,
                'actor_name': user_rnf.get_full_name() or user_rnf.email,
                'action': 'file_upload',
                'description': "Photo 'Flamants_roses.jpg' ajoutée au site Camargue",
                'related_site': site_camargue,
                'related_organisme': org_rnf,
                'metadata': {'filename': 'Flamants_roses.jpg', 'size_bytes': 1234567, 'type': 'photo'},
                'visibility': 'public',
                'created_at': now - timedelta(hours=26),
            },
        ]

    def seed(self) -> List[ActivityLog]:
        """
        Crée les logs d'activité de test.

        Returns:
            Liste des ActivityLog créés
        """
        self.log_header("Création des logs d'activité")

        users = self.context.require('users')
        sites = self.context.require('sites')
        plans = self.context.require('plans')
        organismes = self.context.require('organismes')
        validation_requests = self.context.require('validation_requests')

        activity_logs_data = self._get_activity_logs_data(
            users, sites, plans, organismes, validation_requests
        )

        activity_logs = []
        for log_data in activity_logs_data:
            created_at = log_data.pop('created_at')

            log = ActivityLog.objects.create(**log_data)
            # Mettre à jour created_at manuellement
            ActivityLog.objects.filter(pk=log.pk).update(created_at=created_at)
            log.refresh_from_db()

            activity_logs.append(log)

            vis_label = {'public': '[PUBLIC]', 'admin': '[ADMIN]', 'system': '[SYSTEM]'}
            self.log_item('créé', f"{vis_label.get(log.visibility, '')} {log.action} - {log.entity_name[:30]}")

        # Compter par visibilité
        public_count = sum(1 for l in activity_logs if l.visibility == 'public')
        admin_count = sum(1 for l in activity_logs if l.visibility == 'admin')
        system_count = sum(1 for l in activity_logs if l.visibility == 'system')

        self.log(
            f"  {len(activity_logs)} logs d'activité ({public_count} public, {admin_count} admin, {system_count} system)",
            'SUCCESS'
        )
        self.context.set('activity_logs', activity_logs)
        return activity_logs

    def reset(self) -> int:
        """
        Supprime les logs d'activité de test.

        Returns:
            Nombre de ActivityLog supprimés
        """
        return ActivityLog.objects.all().delete()[0]

    def get_dry_run_summary(self) -> List[str]:
        """
        Résumé des logs d'activité qui seraient créés.

        Returns:
            Liste des lignes du résumé
        """
        return [
            "\nLogs d'activité (25+):",
            '  Visibilités:',
            '    - public: activités normales',
            '    - admin: activités de validation',
            '    - system: activités RGPD et alertes système',
            '  Actions: create, update, delete, add_member, remove_member,',
            '           add_referent, remove_referent, activate, deactivate,',
            '           file_upload, validation_approved, validation_rejected,',
            '           rgpd_request, rgpd_cancelled, rgpd_anonymized, status_change',
        ]
