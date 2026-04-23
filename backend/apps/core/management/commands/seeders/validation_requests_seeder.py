"""
Seeder pour les demandes de validation.
"""
from datetime import timedelta
from typing import Any, Dict, List

from django.utils import timezone

from apps.notifications.models import ValidationRequest
from apps.plans.models import PlanGestion
from apps.users.models import BibOrganismes, Role, Site

from .base import BaseSeeder


class ValidationRequestsSeeder(BaseSeeder):
    """
    Crée des demandes de validation de test.

    Hiérarchie des permissions pour la validation:
    - super_admin: peut valider TOUTES les demandes
    - admin_og: peut valider les demandes liées à son organisme
    - référent: peut valider les demandes sur ses sites
    - utilisateur: ne peut pas valider

    Types de demandes:
    - user_registration
    - site_access
    - plan_access
    - referent_validation
    - admin_deactivation
    - module_access
    - site_creation
    - site_org_link
    - site_org_unlink
    - invite_org_to_site
    - invite_user_to_site
    - plan_site_link
    """

    name = 'validation_requests'
    dependencies = ['users', 'sites', 'plans', 'organismes']

    def _get_validation_requests_data(
        self,
        users: List[Role],
        sites: List[Site],
        plans: List[PlanGestion],
        organismes: List[BibOrganismes]
    ) -> List[Dict]:
        """Retourne les données des demandes de validation."""
        admin = users[0]  # super_admin
        admin_rnf = users[1]
        admin_cen = users[2]
        referent_camargue = users[3]
        referent_vercors = users[4]
        user_rnf = users[5]
        user_cen = users[6]

        now = timezone.now()

        return [
            # DEMANDES D'ACCÈS SITE
            {
                'request_type': 'site_access',
                'requester': user_rnf,
                'target_site': sites[1],
                'status': 'pending',
                'justification': 'Je souhaite participer au suivi des espèces végétales de la réserve.',
            },
            {
                'request_type': 'site_access',
                'requester': user_cen,
                'target_site': sites[3],
                'status': 'approved',
                'justification': 'Intégration équipe Vercors.',
                'validator': admin_cen,
                'validation_comment': "Bienvenue dans l'équipe !",
                'validated_at': now - timedelta(days=3),
            },

            # DEMANDES D'ACCÈS PLAN
            # Demandes en attente (pending) - pour tester la section "Plans en attente"
            {
                'request_type': 'plan_access',
                'requester': user_rnf,
                'target_plan': plans[4],  # Plan Marais de Brouage
                'status': 'pending',
                'justification': "Besoin d'accès pour comparer les méthodes de gestion des zones humides.",
            },
            {
                'request_type': 'plan_access',
                'requester': user_rnf,
                'target_plan': plans[3],  # Plan inter-sites Vercors-Écrins
                'status': 'pending',
                'justification': "Je participe à un projet de recherche inter-régional.",
            },
            {
                'request_type': 'plan_access',
                'requester': user_cen,
                'target_plan': plans[0],  # Plan Camargue
                'status': 'pending',
                'justification': "Collaboration avec RNF pour le suivi des oiseaux migrateurs.",
            },
            {
                'request_type': 'plan_access',
                'requester': user_cen,
                'target_plan': plans[5],  # Plan Lac de Remoray
                'status': 'pending',
                'justification': "Étude comparative des écosystèmes lacustres.",
            },
            {
                'request_type': 'plan_access',
                'requester': referent_camargue,
                'target_plan': plans[2],  # Plan Grand-Voyeux
                'status': 'pending',
                'justification': "Échange de bonnes pratiques entre sites.",
            },
            # Demande refusée (pour tester le bouton "Redemander")
            {
                'request_type': 'plan_access',
                'requester': user_cen,
                'target_plan': plans[1],  # Plan Aiguilles Rouges
                'status': 'rejected',
                'justification': "Je voudrais consulter ce plan pour m'inspirer.",
                'validator': admin_rnf,
                'validation_comment': 'Ce plan est réservé aux membres de RNF.',
                'validated_at': now - timedelta(days=7),
            },
            # Demande approuvée (pour tester l'accès accordé)
            {
                'request_type': 'plan_access',
                'requester': referent_vercors,
                'target_plan': plans[0],  # Plan Camargue
                'status': 'approved',
                'justification': "Besoin d'accès pour partager les méthodes de suivi.",
                'validator': admin_rnf,
                'validation_comment': 'Accès accordé pour la collaboration inter-sites.',
                'validated_at': now - timedelta(days=2),
            },

            # VALIDATION RÉFÉRENT
            {
                'request_type': 'referent_validation',
                'requester': user_rnf,
                'target_site': sites[6],
                'status': 'pending',
                'justification': 'Je souhaite devenir référent pour ce site proche de mon domicile.',
            },
            {
                'request_type': 'referent_validation',
                'requester': referent_vercors,
                'target_site': sites[4],
                'status': 'approved',
                'justification': 'Expertise zone humide.',
                'validator': admin,
                'validation_comment': 'Référent validé.',
                'validated_at': now - timedelta(days=14),
            },

            # DÉSACTIVATION ADMIN
            {
                'request_type': 'admin_deactivation',
                'requester': admin,
                'target_user': users[8] if len(users) > 8 else None,
                'requested_organisme': organismes[1],
                'status': 'pending',
                'justification': "Départ de l'organisation, besoin de transférer les responsabilités.",
            },

            # DEMANDES D'ACCÈS MODULE
            {
                'request_type': 'module_access',
                'requester': user_cen,
                'target_module': 'zonages',
                'status': 'pending',
                'justification': 'Je travaille sur les zonages réglementaires pour le Vercors.',
            },
            {
                'request_type': 'module_access',
                'requester': user_rnf,
                'target_module': 'zonages',
                'status': 'approved',
                'justification': "Besoin d'accès pour le suivi des zonages de la Camargue.",
                'validator': admin,
                'validation_comment': 'Accès accordé pour le projet Camargue.',
                'validated_at': now - timedelta(days=5),
            },
            {
                'request_type': 'module_access',
                'requester': referent_vercors,
                'target_module': 'zonages',
                'status': 'rejected',
                'justification': 'Je souhaite consulter les zonages.',
                'validator': admin,
                'validation_comment': 'Accès refusé : formation requise avant utilisation de ce module.',
                'validated_at': now - timedelta(days=10),
            },

            # CRÉATION DE SITE
            {
                'request_type': 'site_creation',
                'requester': user_cen,
                'status': 'pending',
                'justification': 'Je souhaite créer un nouveau site pour la Tourbière du Mont Bar dans le Puy-de-Dôme.',
            },
            {
                'request_type': 'site_creation',
                'requester': referent_vercors,
                'status': 'approved',
                'justification': 'Nouveau site ENS dans les Hautes-Alpes.',
                'validator': admin,
                'validation_comment': 'Site créé avec succès. Bienvenue !',
                'validated_at': now - timedelta(days=30),
            },

            # LIEN SITE-ORGANISME
            {
                'request_type': 'site_org_link',
                'requester': admin_cen,
                'target_site': sites[5],
                'requested_organisme': organismes[1],
                'status': 'pending',
                'justification': 'Notre organisme participe à un projet de suivi inter-régional.',
            },
            {
                'request_type': 'site_org_link',
                'requester': admin_rnf,
                'target_site': sites[3],
                'requested_organisme': organismes[0],
                'status': 'approved',
                'justification': 'Partenariat pour le suivi de la faune alpine.',
                'validator': admin_cen,
                'validation_comment': 'Partenariat validé. Bienvenue !',
                'validated_at': now - timedelta(days=14),
            },

            # RETRAIT SITE-ORGANISME
            {
                'request_type': 'site_org_unlink',
                'requester': admin_rnf,
                'target_site': sites[3],
                'requested_organisme': organismes[1],
                'status': 'pending',
                'justification': "Fin du partenariat inter-régional. CEN AURA n'intervient plus sur ce site.",
            },
            {
                'request_type': 'site_org_unlink',
                'requester': referent_camargue,
                'target_site': sites[0],
                'requested_organisme': organismes[3],
                'status': 'approved',
                'justification': "Projet terminé, retrait de l'organisme partenaire.",
                'validator': admin,
                'validation_comment': 'Retrait effectué. Merci pour la collaboration.',
                'validated_at': now - timedelta(days=10),
            },
            {
                'request_type': 'site_org_unlink',
                'requester': user_rnf,
                'target_site': sites[6],
                'requested_organisme': organismes[0],
                'status': 'rejected',
                'justification': 'Demande de retrait de RNF du site.',
                'validator': admin_rnf,
                'validation_comment': "RNF est le gestionnaire principal de ce site. Le retrait n'est pas possible.",
                'validated_at': now - timedelta(days=5),
            },

            # INVITATION ORGANISME VERS SITE
            {
                'request_type': 'invite_org_to_site',
                'requester': referent_camargue,
                'target_site': sites[0],
                'requested_organisme': organismes[1],
                'status': 'pending',
                'justification': 'Nous invitons CEN AURA à participer au projet de suivi des flamants roses.',
            },
            {
                'request_type': 'invite_org_to_site',
                'requester': admin_rnf,
                'target_site': sites[1],
                'requested_organisme': organismes[3],
                'status': 'approved',
                'justification': 'Invitation pour collaboration scientifique.',
                'validator': admin,
                'validation_comment': 'Collaboration acceptée.',
                'validated_at': now - timedelta(days=21),
            },

            # INVITATION UTILISATEUR VERS SITE
            {
                'request_type': 'invite_user_to_site',
                'requester': referent_camargue,
                'target_site': sites[0],
                'target_user': user_cen,
                'status': 'pending',
                'justification': "Nous vous invitons à rejoindre l'équipe du site Camargue pour le projet biodiversité.",
            },
            {
                'request_type': 'invite_user_to_site',
                'requester': admin_rnf,
                'target_site': sites[6],
                'target_user': user_rnf,
                'status': 'approved',
                'justification': "Invitation à rejoindre l'équipe du Lac de Remoray.",
                'validator': user_rnf,
                'validation_comment': "J'accepte avec plaisir de rejoindre cette équipe !",
                'validated_at': now - timedelta(days=5),
            },
            {
                'request_type': 'invite_user_to_site',
                'requester': referent_vercors,
                'target_site': sites[3],
                'target_user': user_rnf,
                'status': 'rejected',
                'justification': 'Invitation à participer au suivi floristique.',
                'validator': user_rnf,
                'validation_comment': "Merci pour l'invitation mais je ne suis pas disponible actuellement.",
                'validated_at': now - timedelta(days=7),
            },

            # LIEN PLAN-SITE (demande de liaison d'un site à un plan)
            {
                'request_type': 'plan_site_link',
                'requester': referent_camargue,
                'target_plan': plans[0],  # Plan Camargue
                'target_site': sites[3],  # Vercors
                'status': 'pending',
                'justification': 'Collaboration inter-sites sur le suivi des oiseaux migrateurs.',
            },
            {
                'request_type': 'plan_site_link',
                'requester': referent_vercors,
                'target_plan': plans[3],  # Plan inter-sites Vercors-Écrins
                'target_site': sites[4],  # Marais de Brouage
                'status': 'pending',
                'justification': 'Extension du plan aux zones humides du littoral atlantique.',
            },
            {
                'request_type': 'plan_site_link',
                'requester': user_rnf,
                'target_plan': plans[1],  # Plan Aiguilles Rouges
                'target_site': sites[6],  # Lac de Remoray
                'status': 'approved',
                'justification': 'Étude comparative des écosystèmes montagnards et lacustres.',
                'validator': admin_rnf,
                'validation_comment': 'Lien approuvé pour le projet de recherche.',
                'validated_at': now - timedelta(days=4),
            },
            # Demande par un référent de site non lié au plan
            {
                'request_type': 'plan_site_link',
                'requester': referent_vercors,
                'target_plan': plans[1],  # Plan Aiguilles Rouges (referent_vercors n'est pas membre)
                'target_site': sites[3],  # Vercors (referent_vercors est référent)
                'status': 'pending',
                'justification': 'Lier le site du Vercors au plan Aiguilles Rouges pour étude comparative.',
            },
        ]

    def seed(self) -> List[ValidationRequest]:
        """
        Crée les demandes de validation de test.

        Returns:
            Liste des ValidationRequest créées
        """
        self.log_header('Création des demandes de validation')

        users = self.context.require('users')
        sites = self.context.require('sites')
        plans = self.context.require('plans')
        organismes = self.context.require('organismes')

        validation_requests_data = self._get_validation_requests_data(
            users, sites, plans, organismes
        )

        validation_requests = []
        for vr_data in validation_requests_data:
            validator = vr_data.pop('validator', None)
            validation_comment = vr_data.pop('validation_comment', None)
            validated_at = vr_data.pop('validated_at', None)

            if validator and not validated_at:
                validated_at = timezone.now()

            vr, created = ValidationRequest.objects.get_or_create(
                request_type=vr_data['request_type'],
                requester=vr_data.get('requester'),
                target_site=vr_data.get('target_site'),
                target_plan=vr_data.get('target_plan'),
                target_user=vr_data.get('target_user'),
                target_module=vr_data.get('target_module'),
                defaults={
                    'status': vr_data['status'],
                    'justification': vr_data.get('justification'),
                    'requested_organisme': vr_data.get('requested_organisme'),
                    'validator': validator,
                    'validation_comment': validation_comment,
                    'validated_at': validated_at,
                    'expires_at': timezone.now() + timedelta(days=14) if vr_data['status'] == 'pending' else None,
                }
            )
            validation_requests.append(vr)

            status_str = "créé" if created else "existant"
            validated_info = ""
            if validated_at:
                validated_info = f" (validé le {validated_at.strftime('%d/%m/%Y')})"
            self.log_item(status_str, f"{vr.request_type} - {vr.status}{validated_info}")

        self.log_summary(len(validation_requests), 'demandes de validation')
        self.context.set('validation_requests', validation_requests)
        return validation_requests

    def reset(self) -> int:
        """
        Supprime les demandes de validation de test.

        Returns:
            Nombre de ValidationRequest supprimées
        """
        return ValidationRequest.objects.all().delete()[0]

    def get_dry_run_summary(self) -> List[str]:
        """
        Résumé des demandes qui seraient créées.

        Returns:
            Liste des lignes du résumé
        """
        return [
            '\nDemandes de validation (31):',
            '  Types: user_registration, site_access, plan_access, referent_validation,',
            '         admin_deactivation, module_access, site_creation, site_org_link,',
            '         site_org_unlink, invite_org_to_site, invite_user_to_site, plan_site_link',
            '  Statuts: pending, approved, rejected',
            '\n  Demandes plan_access (7):',
            '    - 5 demandes pending (user_rnf, user_cen, referent_camargue)',
            '    - 1 demande rejected (user_cen -> Aiguilles Rouges)',
            '    - 1 demande approved (referent_vercors -> Camargue)',
            '\n  Autres demandes:',
            '    - site_access approved: il y a 3 jours',
            '    - referent_validation approved: il y a 2 semaines',
            '    - module_access approved (user_rnf -> zonages): il y a 5 jours',
            '    - module_access rejected (referent_vercors -> zonages): il y a 10 jours',
            '    - module_access pending (user_cen -> zonages): en attente',
            '\nHiérarchie des permissions de validation:',
            '  super_admin > admin_og > référent > utilisateur',
            '  - super_admin: peut valider TOUTES les demandes',
            '  - admin_og: demandes liées à son organisme',
            '  - référent: demandes sur ses sites',
        ]
