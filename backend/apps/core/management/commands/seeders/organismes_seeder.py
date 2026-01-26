"""
Seeder pour les organismes.
"""
from typing import Any, List

from apps.users.models import BibOrganismes, Role, CorOgSite
from apps.notifications.models import PendingUser, ValidationRequest

from .base import BaseSeeder


class OrganismesSeeder(BaseSeeder):
    """
    Cree les organismes de test.

    Organismes:
    - Reserves Naturelles de France
    - CEN Auvergne-Rhone-Alpes
    - DREAL Nouvelle-Aquitaine
    - Parc National des Ecrins
    - Office Francais de la Biodiversite
    """

    name = 'organismes'
    dependencies = []

    ORGANISMES_DATA = [
        {
            'nom_organisme': 'Reserves Naturelles de France',
            'email_organisme': 'contact@reserves-naturelles.org',
            'ville_organisme': 'Dijon',
            'cp_organisme': '21000',
            'adresse_organisme': '6 rue de la Manutention',
            'tel_organisme': '03 80 48 91 00'
        },
        {
            'nom_organisme': 'CEN Auvergne-Rhone-Alpes',
            'email_organisme': 'contact@cen-aura.org',
            'ville_organisme': 'Lyon',
            'cp_organisme': '69007',
            'adresse_organisme': '11 Allee de Lodz',
            'tel_organisme': '04 72 31 84 50'
        },
        {
            'nom_organisme': 'DREAL Nouvelle-Aquitaine',
            'email_organisme': 'contact@nouvelle-aquitaine.gouv.fr',
            'ville_organisme': 'Bordeaux',
            'cp_organisme': '33000',
            'adresse_organisme': '15 rue Arthur Ranc',
            'tel_organisme': '05 56 24 80 80'
        },
        {
            'nom_organisme': 'Parc National des Ecrins',
            'email_organisme': 'contact@ecrins-parcnational.fr',
            'ville_organisme': 'Gap',
            'cp_organisme': '05000',
            'adresse_organisme': 'Domaine de Charance',
            'tel_organisme': '04 92 40 20 10'
        },
        {
            'nom_organisme': 'Office Francais de la Biodiversite',
            'email_organisme': 'contact@ofb.gouv.fr',
            'ville_organisme': 'Vincennes',
            'cp_organisme': '94300',
            'adresse_organisme': '12 Cours Louis Lumiere',
            'tel_organisme': '01 45 14 36 00'
        },
    ]

    # Variations de noms a nettoyer (avec/sans accents)
    VARIATIONS_TO_CLEAN = [
        ('CEN Auvergne-Rhône-Alpes', 'CEN Auvergne-Rhone-Alpes'),
        ('DREAL Auvergne-Rhône-Alpes', 'DREAL Auvergne-Rhone-Alpes'),
    ]

    def _clean_duplicates(self) -> None:
        """Nettoie les doublons potentiels (variations avec/sans accents)."""
        for old_name, canonical_name in self.VARIATIONS_TO_CLEAN:
            old_org = BibOrganismes.objects.filter(nom_organisme=old_name).first()
            if old_org:
                canonical_org = BibOrganismes.objects.filter(nom_organisme=canonical_name).first()
                if canonical_org:
                    # Les deux existent - fusionner
                    Role.objects.filter(id_organisme=old_org).update(id_organisme=canonical_org)
                    CorOgSite.objects.filter(uuid_og=old_org).update(uuid_og=canonical_org)
                    PendingUser.objects.filter(requested_organisme=old_org).update(requested_organisme=canonical_org)
                    ValidationRequest.objects.filter(requested_organisme=old_org).update(requested_organisme=canonical_org)
                    old_org.delete()
                    self.log(f"  [FUSION] '{old_name}' -> '{canonical_name}'")
                else:
                    # Seul l'ancien existe - le renommer
                    old_org.nom_organisme = canonical_name
                    old_org.save()
                    self.log(f"  [RENOMME] '{old_name}' -> '{canonical_name}'")

    def seed(self) -> List[BibOrganismes]:
        """
        Cree les organismes de test.

        Returns:
            Liste des organismes crees
        """
        self.log_header('Creation des organismes')

        # Nettoyer les doublons potentiels
        self._clean_duplicates()

        organismes = []
        for org_data in self.ORGANISMES_DATA:
            org, created = BibOrganismes.objects.get_or_create(
                nom_organisme=org_data['nom_organisme'],
                defaults=org_data
            )
            organismes.append(org)

            status = "cree" if created else "existant"
            self.log_item(status, org.nom_organisme)

        self.log_summary(len(organismes), 'organismes')
        self.context.set('organismes', organismes)
        return organismes

    def reset(self) -> int:
        """
        Supprime les organismes de test.

        Returns:
            Nombre d'organismes supprimes
        """
        test_organismes = [org['nom_organisme'] for org in self.ORGANISMES_DATA]
        deleted_count = BibOrganismes.objects.filter(nom_organisme__in=test_organismes).delete()[0]
        return deleted_count

    def get_dry_run_summary(self) -> List[str]:
        """
        Resume des organismes qui seraient crees.

        Returns:
            Liste des lignes du resume
        """
        return [
            '\nOrganismes (5):',
            '  - Reserves Naturelles de France',
            '  - CEN Auvergne-Rhone-Alpes',
            '  - DREAL Nouvelle-Aquitaine',
            '  - Parc National des Ecrins',
            '  - Office Francais de la Biodiversite',
        ]
