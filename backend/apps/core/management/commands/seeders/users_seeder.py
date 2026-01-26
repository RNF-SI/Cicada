"""
Seeder pour les utilisateurs.
"""
from datetime import timedelta
from typing import Any, Dict, List

from django.utils import timezone

from apps.users.models import Role, CorRoleSite, BibOrganismes, Site

from .base import BaseSeeder


DEFAULT_PASSWORD = 'Test123!'

# Adresse email reelle pour les tests d'envoi de mail
REAL_TEST_EMAIL = 'test@reserves-naturelles.org'


class UsersSeeder(BaseSeeder):
    """
    Cree les utilisateurs de test avec differents roles.

    Utilisateurs actifs (8):
    - admin@test.fr (super_admin)
    - admin.rnf@test.fr (admin_og)
    - admin.cen@test.fr (admin_og)
    - referent.camargue@test.fr (referent)
    - referent.vercors@test.fr (referent)
    - user.rnf@test.fr (utilisateur)
    - user.cen@test.fr (utilisateur)
    - test@reserves-naturelles.org (utilisateur) - Pour tests email reels

    Utilisateurs inactifs (3):
    - ancien.rnf@test.fr
    - ancien.cen@test.fr
    - stagiaire.dreal@test.fr

    Utilisateurs en attente (2):
    - pending.rnf@test.fr
    - pending.cen@test.fr

    Utilisateurs RGPD (2):
    - deletion.recent@test.fr
    - deletion.old@test.fr
    """

    name = 'users'
    dependencies = ['organismes', 'sites', 'groups']

    def _get_users_data(
        self,
        organismes: List[BibOrganismes],
        sites: List[Site]
    ) -> List[Dict]:
        """Retourne les donnees des utilisateurs."""
        return [
            {
                'email': 'admin@test.fr',
                'nom_role': 'Admin',
                'prenom_role': 'Super',
                'identifiant': 'super_admin',
                'role_level': 'super_admin',
                'is_staff': True,
                'is_superuser': True,
                'id_organisme': organismes[0],  # RNF
                'groups': ['Super Administrateurs'],
                'sites_referent': [sites[0]]  # Camargue
            },
            {
                'email': 'admin.rnf@test.fr',
                'nom_role': 'Dupont',
                'prenom_role': 'Marie',
                'identifiant': 'admin_rnf',
                'role_level': 'admin_og',
                'is_staff': True,
                'is_superuser': False,
                'id_organisme': organismes[0],  # RNF
                'groups': ['Administrateurs Organisme'],
                'sites_referent': [sites[0], sites[1]]  # Camargue, Aiguilles Rouges
            },
            {
                'email': 'admin.cen@test.fr',
                'nom_role': 'Martin',
                'prenom_role': 'Jean',
                'identifiant': 'admin_cen',
                'role_level': 'admin_og',
                'is_staff': True,
                'is_superuser': False,
                'id_organisme': organismes[1],  # CEN AURA
                'groups': ['Administrateurs Organisme'],
                'sites_referent': [sites[2], sites[3]]  # Grand-Voyeux, Vercors
            },
            {
                'email': 'referent.camargue@test.fr',
                'nom_role': 'Bernard',
                'prenom_role': 'Sophie',
                'identifiant': 'ref_camargue',
                'role_level': 'utilisateur',
                'is_staff': False,
                'is_superuser': False,
                'id_organisme': organismes[0],  # RNF
                'groups': ['Utilisateurs'],
                'sites_referent': [sites[0]]  # Camargue
            },
            {
                'email': 'referent.vercors@test.fr',
                'nom_role': 'Petit',
                'prenom_role': 'Lucas',
                'identifiant': 'ref_vercors',
                'role_level': 'utilisateur',
                'is_staff': False,
                'is_superuser': False,
                'id_organisme': organismes[1],  # CEN AURA
                'groups': ['Utilisateurs'],
                'sites_referent': [sites[3]]  # Vercors
            },
            {
                'email': 'user.rnf@test.fr',
                'nom_role': 'Durand',
                'prenom_role': 'Emma',
                'identifiant': 'user_rnf',
                'role_level': 'utilisateur',
                'is_staff': False,
                'is_superuser': False,
                'id_organisme': organismes[0],  # RNF
                'groups': ['Utilisateurs'],
                'sites_referent': []
            },
            {
                'email': 'user.cen@test.fr',
                'nom_role': 'Leroy',
                'prenom_role': 'Thomas',
                'identifiant': 'user_cen',
                'role_level': 'utilisateur',
                'is_staff': False,
                'is_superuser': False,
                'id_organisme': organismes[1],  # CEN AURA
                'groups': ['Utilisateurs'],
                'sites_referent': [],
                'active': True
            },
            # Utilisateur avec adresse email reelle pour tests d'envoi
            {
                'email': REAL_TEST_EMAIL,
                'nom_role': 'TestEmail',
                'prenom_role': 'RNF',
                'identifiant': 'test_email_rnf',
                'role_level': 'utilisateur',
                'is_staff': False,
                'is_superuser': False,
                'id_organisme': organismes[0],  # RNF
                'groups': ['Utilisateurs'],
                'sites_referent': [sites[0]],  # Camargue - pour tester notifications site
                'active': True
            },
            # Utilisateurs inactifs
            {
                'email': 'ancien.rnf@test.fr',
                'nom_role': 'Moreau',
                'prenom_role': 'Pierre',
                'identifiant': 'ancien_rnf',
                'role_level': 'utilisateur',
                'is_staff': False,
                'is_superuser': False,
                'id_organisme': organismes[0],
                'groups': ['Utilisateurs'],
                'sites_referent': [],
                'active': False
            },
            {
                'email': 'ancien.cen@test.fr',
                'nom_role': 'Dubois',
                'prenom_role': 'Claire',
                'identifiant': 'ancien_cen',
                'role_level': 'admin_og',
                'is_staff': True,
                'is_superuser': False,
                'id_organisme': organismes[1],
                'groups': ['Administrateurs Organisme'],
                'sites_referent': [],
                'active': False
            },
            {
                'email': 'stagiaire.dreal@test.fr',
                'nom_role': 'Robert',
                'prenom_role': 'Julie',
                'identifiant': 'stagiaire_dreal',
                'role_level': 'utilisateur',
                'is_staff': False,
                'is_superuser': False,
                'id_organisme': organismes[2],
                'groups': ['Utilisateurs'],
                'sites_referent': [],
                'active': False
            },
            # Utilisateurs en attente de validation
            {
                'email': 'pending.rnf@test.fr',
                'nom_role': 'Girard',
                'prenom_role': 'Antoine',
                'identifiant': 'pending_rnf',
                'role_level': 'utilisateur',
                'is_staff': False,
                'is_superuser': False,
                'id_organisme': organismes[0],
                'groups': ['Utilisateurs'],
                'sites_referent': [],
                'active': True,
                'pending_validation': True
            },
            {
                'email': 'pending.cen@test.fr',
                'nom_role': 'Mercier',
                'prenom_role': 'Camille',
                'identifiant': 'pending_cen',
                'role_level': 'utilisateur',
                'is_staff': False,
                'is_superuser': False,
                'id_organisme': organismes[1],
                'groups': ['Utilisateurs'],
                'sites_referent': [],
                'active': True,
                'pending_validation': True
            },
            # Utilisateurs avec suppression demandee (RGPD)
            {
                'email': 'deletion.recent@test.fr',
                'nom_role': 'Fournier',
                'prenom_role': 'Nicolas',
                'identifiant': 'deletion_recent',
                'role_level': 'utilisateur',
                'is_staff': False,
                'is_superuser': False,
                'id_organisme': organismes[0],
                'groups': ['Utilisateurs'],
                'sites_referent': [],
                'active': False,
                'deletion_requested_days_ago': 5
            },
            {
                'email': 'deletion.old@test.fr',
                'nom_role': 'Blanc',
                'prenom_role': 'Isabelle',
                'identifiant': 'deletion_old',
                'role_level': 'utilisateur',
                'is_staff': False,
                'is_superuser': False,
                'id_organisme': organismes[1],
                'groups': ['Utilisateurs'],
                'sites_referent': [],
                'active': False,
                'deletion_requested_days_ago': 25
            },
        ]

    def _update_existing_superusers(self) -> None:
        """Met a jour les superusers existants pour avoir role_level='super_admin'."""
        existing_superusers = Role.objects.filter(is_superuser=True, role_level='utilisateur')
        for su in existing_superusers:
            su.role_level = 'super_admin'
            su.save(update_fields=['role_level'])
            self.log_item('mise a jour', f"{su.email}: role_level='super_admin'")

    def seed(self) -> List[Role]:
        """
        Cree les utilisateurs de test.

        Returns:
            Liste des utilisateurs crees
        """
        self.log_header('Creation des utilisateurs')

        organismes = self.context.require('organismes')
        sites = self.context.require('sites')
        groups = self.context.require('groups')

        # Mettre a jour les superusers existants
        self._update_existing_superusers()

        users_data = self._get_users_data(organismes, sites)

        users = []
        for user_data in users_data:
            user_groups = user_data.pop('groups')
            sites_referent = user_data.pop('sites_referent')
            is_active = user_data.pop('active', True)
            is_pending = user_data.pop('pending_validation', False)
            deletion_days_ago = user_data.pop('deletion_requested_days_ago', None)

            # Calculer la date de demande de suppression
            deletion_requested_at = None
            if deletion_days_ago is not None:
                deletion_requested_at = timezone.now() - timedelta(days=deletion_days_ago)

            user, created = Role.objects.update_or_create(
                email=user_data['email'],
                defaults={
                    'nom_role': user_data['nom_role'],
                    'prenom_role': user_data['prenom_role'],
                    'identifiant': user_data['identifiant'],
                    'role_level': user_data['role_level'],
                    'is_staff': user_data['is_staff'],
                    'is_superuser': user_data['is_superuser'],
                    'id_organisme': user_data['id_organisme'],
                    'active': is_active,
                    'pending_validation': is_pending,
                    'deletion_requested_at': deletion_requested_at,
                }
            )

            user.set_password(DEFAULT_PASSWORD)
            user.save()

            # Ajouter aux groupes
            for group_name in user_groups:
                if group_name in groups:
                    user.groups.add(groups[group_name])

            # Ajouter comme referent des sites
            for site in sites_referent:
                CorRoleSite.objects.get_or_create(
                    id_site=site,
                    id_role=user,
                    defaults={'referent': True, 'referent_valid': True, 'conservateur': False}
                )

            users.append(user)
            status = "cree" if created else "mis a jour"
            org_name = user_data['id_organisme'].nom_organisme if user_data['id_organisme'] else "N/A"
            self.log_item(status, f"{user.email} ({user_data['role_level']}) - {org_name}")

        self.log_summary(len(users), 'utilisateurs')
        self.context.set('users', users)
        return users

    def reset(self) -> int:
        """
        Supprime les utilisateurs de test.

        Returns:
            Nombre d'utilisateurs supprimes
        """
        test_emails = [
            'admin@test.fr', 'admin.rnf@test.fr', 'admin.cen@test.fr',
            'referent.camargue@test.fr', 'referent.vercors@test.fr',
            'user.rnf@test.fr', 'user.cen@test.fr',
            REAL_TEST_EMAIL,  # Utilisateur pour tests email reels
            'ancien.rnf@test.fr', 'ancien.cen@test.fr', 'stagiaire.dreal@test.fr',
            'pending.rnf@test.fr', 'pending.cen@test.fr',
            'deletion.recent@test.fr', 'deletion.old@test.fr',
        ]
        return Role.objects.filter(email__in=test_emails).delete()[0]

    def get_dry_run_summary(self) -> List[str]:
        """
        Resume des utilisateurs qui seraient crees.

        Returns:
            Liste des lignes du resume
        """
        return [
            '\nUtilisateurs actifs (8):',
            f'  Mot de passe commun: {DEFAULT_PASSWORD}',
            '  - admin@test.fr (super_admin)',
            '  - admin.rnf@test.fr (admin_og) - RNF',
            '  - admin.cen@test.fr (admin_og) - CEN AURA',
            '  - referent.camargue@test.fr (referent) - RNF',
            '  - referent.vercors@test.fr (referent) - CEN AURA',
            '  - user.rnf@test.fr (utilisateur) - RNF',
            '  - user.cen@test.fr (utilisateur) - CEN AURA',
            f'  - {REAL_TEST_EMAIL} (utilisateur) - RNF [EMAIL REEL POUR TESTS]',
            '\nUtilisateurs inactifs (3):',
            '  - ancien.rnf@test.fr (referent) - RNF [INACTIF]',
            '  - ancien.cen@test.fr (admin_og) - CEN AURA [INACTIF]',
            '  - stagiaire.dreal@test.fr (utilisateur) - DREAL [INACTIF]',
            '\nUtilisateurs en attente de validation (2):',
            '  - pending.rnf@test.fr - Utilisateur inscrit, en attente validation',
            '  - pending.cen@test.fr - Utilisateur inscrit, en attente validation',
        ]
