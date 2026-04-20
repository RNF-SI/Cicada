"""
Seeder pour les utilisateurs en attente d'inscription (PendingUser).
"""
from datetime import timedelta
from typing import Any, Dict, List

from django.contrib.auth.hashers import make_password
from django.utils import timezone

from apps.notifications.models import PendingUser, ValidationRequest
from apps.users.models import BibOrganismes, Role

from .base import BaseSeeder


DEFAULT_PASSWORD = 'Test123!'


class PendingUsersSeeder(BaseSeeder):
    """
    Cree les utilisateurs en attente d'inscription (PendingUser).

    Chaque PendingUser a sa propre ValidationRequest unique.
    Ces demandes peuvent etre validees par:
    - super_admin: toutes les demandes
    - admin_og: demandes pour leur organisme

    Utilisateurs en attente:
    - nouveau.user1@test.fr -> RNF
    - nouveau.user2@test.fr -> CEN AURA
    - nouveau.user3@test.fr -> DREAL
    """

    name = 'pending_users'
    dependencies = ['organismes']

    def _get_pending_users_data(
        self,
        organismes: List[BibOrganismes]
    ) -> List[Dict]:
        """Retourne les donnees des utilisateurs en attente."""
        return [
            {
                'email': 'nouveau.user1@test.fr',
                'identifiant': 'm.lefebvre',
                'password': DEFAULT_PASSWORD,
                'nom_role': 'Lefebvre',
                'prenom_role': 'Marc',
                'requested_organisme': organismes[0],  # RNF
                'justification': 'Je suis naturaliste et je souhaite contribuer aux plans de gestion de RNF.',
            },
            {
                'email': 'nouveau.user2@test.fr',
                'identifiant': 'l.simon',
                'password': DEFAULT_PASSWORD,
                'nom_role': 'Simon',
                'prenom_role': 'Lea',
                'requested_organisme': organismes[1],  # CEN AURA
                'justification': 'Nouvelle recrue au CEN AURA, en attente de validation par mon administrateur.',
            },
            {
                'email': 'nouveau.user3@test.fr',
                'identifiant': None,  # Demande sans identifiant pour couvrir ce chemin
                'password': DEFAULT_PASSWORD,
                'nom_role': 'Michel',
                'prenom_role': 'Paul',
                'requested_organisme': organismes[2],  # DREAL
                'justification': 'Agent DREAL affecte au suivi des espaces naturels.',
            },
        ]

    def _fix_orphan_approved_requests(self) -> None:
        """Corrige les demandes d'inscription approuvees sans requester lie."""
        # Mapping emails de test -> organisme
        test_emails = {
            'nouveau.user1@test.fr': 'RNF',
            'nouveau.user2@test.fr': 'CEN Auvergne-Rhone-Alpes',
            'nouveau.user3@test.fr': 'DREAL Auvergne-Rhone-Alpes',
        }

        orphan_approved = ValidationRequest.objects.filter(
            request_type='user_registration',
            status='approved',
            requester__isnull=True
        )

        for vr in orphan_approved:
            for email, org_name in test_emails.items():
                user = Role.objects.filter(email__iexact=email).first()
                if user and vr.requested_organisme:
                    if vr.requested_organisme.nom_organisme == org_name:
                        vr.requester = user
                        vr.save(update_fields=['requester'])
                        self.log(f"  [FIX] Requester lie pour validation #{vr.id}: {user}")
                        break

    def seed(self) -> List[PendingUser]:
        """
        Cree les utilisateurs en attente d'inscription.

        Returns:
            Liste des PendingUser crees
        """
        self.log_header("Creation des utilisateurs en attente d'inscription")

        organismes = self.context.require('organismes')

        # Corriger les demandes orphelines
        self._fix_orphan_approved_requests()

        pending_users_data = self._get_pending_users_data(organismes)

        pending_users = []
        for pu_data in pending_users_data:
            # Verifier si le PendingUser existe deja
            existing_pending = PendingUser.objects.filter(email=pu_data['email']).first()

            if existing_pending:
                pending_users.append(existing_pending)
                org_name = pu_data['requested_organisme'].nom_organisme
                self.log_item('existant', f"{pu_data['email']} -> {org_name}")
                continue

            # Creer une ValidationRequest unique pour cette inscription
            validation_request = ValidationRequest.objects.create(
                request_type='user_registration',
                requester=None,
                requested_organisme=pu_data['requested_organisme'],
                status='pending',
                justification=pu_data['justification'],
                expires_at=timezone.now() + timedelta(days=7),
            )

            # Creer le PendingUser lie a cette ValidationRequest
            pending_user = PendingUser.objects.create(
                email=pu_data['email'],
                identifiant=pu_data.get('identifiant'),
                password_hash=make_password(pu_data['password']),
                nom_role=pu_data['nom_role'],
                prenom_role=pu_data['prenom_role'],
                requested_organisme=pu_data['requested_organisme'],
                justification=pu_data['justification'],
                validation_request=validation_request,
                ip_address='127.0.0.1',
                user_agent='Mozilla/5.0 (Test Data)',
            )
            pending_users.append(pending_user)

            org_name = pu_data['requested_organisme'].nom_organisme
            self.log_item('cree', f"{pu_data['email']} -> {org_name}")
            if self.verbosity >= 2:
                self.stdout.write(f"         ValidationRequest #{validation_request.id} (pending)")

        self.log_summary(len(pending_users), "utilisateurs en attente")
        self.context.set('pending_users', pending_users)
        return pending_users

    def reset(self) -> int:
        """
        Supprime les utilisateurs en attente de test.

        Returns:
            Nombre de PendingUser supprimes
        """
        return PendingUser.objects.all().delete()[0]

    def get_dry_run_summary(self) -> List[str]:
        """
        Resume des utilisateurs en attente qui seraient crees.

        Returns:
            Liste des lignes du resume
        """
        return [
            "\nUtilisateurs en attente d'inscription - PendingUser (3):",
            '  Chaque PendingUser a sa propre ValidationRequest unique.',
            '  - nouveau.user1@test.fr - Demande RNF',
            '      Validable par: admin@test.fr, admin.rnf@test.fr',
            '  - nouveau.user2@test.fr - Demande CEN AURA',
            '      Validable par: admin@test.fr, admin.cen@test.fr',
            '  - nouveau.user3@test.fr - Demande DREAL',
            "      Validable par: admin@test.fr (pas d'admin DREAL)",
        ]
