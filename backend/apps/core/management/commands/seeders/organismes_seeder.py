"""
Seeder pour les organismes.
"""
from typing import Any, List

from apps.users.models import BibOrganismes, Role, CorOgSite
from apps.notifications.models import PendingUser, ValidationRequest
from apps.core.models import Nomenclature

from .base import BaseSeeder


class OrganismesSeeder(BaseSeeder):
    """
    Crée les organismes de test.

    Organismes:
    - Réserves Naturelles de France
    - CEN Auvergne-Rhône-Alpes
    - DREAL Nouvelle-Aquitaine
    - Parc National des Écrins
    - Office Français de la Biodiversité
    """

    name = 'organismes'
    dependencies = []

    ORGANISMES_DATA = [
        {
            'nom_organisme': 'Réserves Naturelles de France',
            'email_organisme': 'contact@example.org',
            'ville_organisme': 'Dijon',
            'cp_organisme': '21000',
            'adresse_organisme': '6 rue de la Manutention',
            'tel_organisme': '03 80 48 91 00'
        },
        {
            'nom_organisme': 'CEN Auvergne-Rhône-Alpes',
            'email_organisme': 'contact@cen-aura.org',
            'ville_organisme': 'Lyon',
            'cp_organisme': '69007',
            'adresse_organisme': '11 Allée de Lodz',
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
            'nom_organisme': 'Parc National des Écrins',
            'email_organisme': 'contact@ecrins-parcnational.fr',
            'ville_organisme': 'Gap',
            'cp_organisme': '05000',
            'adresse_organisme': 'Domaine de Charance',
            'tel_organisme': '04 92 40 20 10'
        },
        {
            'nom_organisme': 'Office Français de la Biodiversité',
            'email_organisme': 'contact@ofb.gouv.fr',
            'ville_organisme': 'Vincennes',
            'cp_organisme': '94300',
            'adresse_organisme': '12 Cours Louis Lumière',
            'tel_organisme': '01 45 14 36 00'
        },
    ]

    # Variations de noms à nettoyer (ancien nom ASCII → nom canonique accentué).
    # Utilisé pour migrer les bases dev ou staging qui contiennent encore
    # les noms sans accent créés avant ce seeder.
    VARIATIONS_TO_CLEAN = [
        ('Reserves Naturelles de France', 'Réserves Naturelles de France'),
        ('CEN Auvergne-Rhone-Alpes', 'CEN Auvergne-Rhône-Alpes'),
        ('Parc National des Ecrins', 'Parc National des Écrins'),
        ('Office Francais de la Biodiversite', 'Office Français de la Biodiversité'),
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

    # Mapping nom_organisme -> cd_nomenclature TYPE_ORGANISME
    TYPE_ORGANISME_MAP = {
        'Réserves Naturelles de France': 'RNF',
        'CEN Auvergne-Rhône-Alpes': 'CEN',
        'DREAL Nouvelle-Aquitaine': 'DREAL',
        'Parc National des Écrins': 'PNX',
        'Office Français de la Biodiversité': 'OFB',
    }

    def seed(self) -> List[BibOrganismes]:
        """
        Crée les organismes de test.

        Returns:
            Liste des organismes créés
        """
        self.log_header('Création des organismes')

        # Nettoyer les doublons potentiels
        self._clean_duplicates()

        # Charger les nomenclatures TYPE_ORGANISME
        type_nomenclatures = {
            n.cd_nomenclature: n
            for n in Nomenclature.objects.filter(id_type__mnemonique='TYPE_ORGANISME')
        }

        organismes = []
        for org_data in self.ORGANISMES_DATA:
            org, created = BibOrganismes.objects.get_or_create(
                nom_organisme=org_data['nom_organisme'],
                defaults=org_data
            )

            # Assigner le type d'organisme si disponible
            type_code = self.TYPE_ORGANISME_MAP.get(org_data['nom_organisme'])
            if type_code and type_code in type_nomenclatures:
                if not org.id_type_organisme or org.id_type_organisme != type_nomenclatures[type_code]:
                    org.id_type_organisme = type_nomenclatures[type_code]
                    org.save(update_fields=['id_type_organisme'])

            organismes.append(org)

            status = "créé" if created else "existant"
            self.log_item(status, f"{org.nom_organisme} ({type_code or '?'})")

        self.log_summary(len(organismes), 'organismes')
        self.context.set('organismes', organismes)
        return organismes

    def reset(self) -> int:
        """
        Supprime les organismes de test.

        Returns:
            Nombre d'organismes supprimés
        """
        # Inclure aussi les anciennes variations ASCII pour que le reset
        # nettoie correctement les bases qui n'ont pas encore été migrées.
        canonical_names = [org['nom_organisme'] for org in self.ORGANISMES_DATA]
        legacy_names = [old for old, _ in self.VARIATIONS_TO_CLEAN]
        test_organismes = canonical_names + legacy_names
        deleted_count = BibOrganismes.objects.filter(nom_organisme__in=test_organismes).delete()[0]
        return deleted_count

    def get_dry_run_summary(self) -> List[str]:
        """
        Résumé des organismes qui seraient créés.

        Returns:
            Liste des lignes du résumé
        """
        return [
            '\nOrganismes (5):',
            '  - Réserves Naturelles de France',
            '  - CEN Auvergne-Rhône-Alpes',
            '  - DREAL Nouvelle-Aquitaine',
            '  - Parc National des Écrins',
            '  - Office Français de la Biodiversité',
        ]
