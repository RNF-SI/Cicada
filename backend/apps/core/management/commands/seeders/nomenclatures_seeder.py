"""
Seeder pour les nomenclatures.
"""
from typing import Any, Dict, List

from apps.core.models import TypeNomenclature, Nomenclature

from .base import BaseSeeder


class NomenclaturesSeeder(BaseSeeder):
    """
    Cree les nomenclatures necessaires.

    Types de nomenclatures:
    - Espace naturel (type_site)
    - Evaluation PG (type_eval)
    - Redacteur type (type_redac)
    """

    name = 'nomenclatures'
    dependencies = []

    # Types de nomenclature
    TYPES_DATA = [
        {'id': 1, 'mnemonique': 'Espace naturel', 'label': "Type d'espace naturel"},
        {'id': 2, 'mnemonique': 'Evaluation PG', 'label': "Niveau d'evaluation des plans de gestion"},
        {'id': 3, 'mnemonique': 'Redacteur type', 'label': "Type de redacteur d'un plan de gestion"},
    ]

    # Types de site (alignes sur nomenclatures_inserts.sql)
    SITE_TYPES = [
        {'id': 42, 'mnemonique': 'RNN', 'label': 'Reserve Naturelle Nationale'},
        {'id': 43, 'mnemonique': 'RNR', 'label': 'Reserve Naturelle Regionale'},
        {'id': 44, 'mnemonique': 'RNC', 'label': 'Reserve Naturelle de Corse'},
        {'id': 93, 'mnemonique': 'PPRN', 'label': 'Perimetre de protection de reserve naturelle'},
        {'id': 600, 'mnemonique': 'PNR', 'label': 'Parc Naturel Regional'},
        {'id': 601, 'mnemonique': 'ENS', 'label': 'Espace Naturel Sensible'},
        {'id': 602, 'mnemonique': 'APB', 'label': 'Arrete de Protection de Biotope'},
        {'id': 604, 'mnemonique': 'AUTRE', 'label': 'Autre'},
    ]

    # Types d'evaluation
    EVAL_TYPES = [
        {'id': 45, 'mnemonique': 'Aucune', 'label': 'Aucune evaluation', 'hierarchy': '1'},
        {'id': 47, 'mnemonique': 'Intermediaire', 'label': 'Evaluation intermediaire', 'hierarchy': '2'},
        {'id': 46, 'mnemonique': 'Finale', 'label': 'Evaluation finale', 'hierarchy': '3'},
    ]

    # Types de redacteur
    REDAC_TYPES = [
        {'id': 48, 'mnemonique': 'OG', 'label': 'Organisme Gestionnaire'},
        {'id': 603, 'mnemonique': 'BE', 'label': "Bureau d'etudes"},
        {'id': 50, 'mnemonique': 'Autre', 'label': 'Autre'},
    ]

    def seed(self) -> Dict[str, TypeNomenclature]:
        """
        Cree les nomenclatures.

        Returns:
            Dict avec les types de nomenclature crees
        """
        self.log_header('Creation des nomenclatures')

        # Creer les types de nomenclature
        type_site, _ = TypeNomenclature.objects.get_or_create(
            id_type=1,
            defaults={'mnemonique': 'Espace naturel', 'label': "Type d'espace naturel"}
        )

        type_eval, _ = TypeNomenclature.objects.get_or_create(
            id_type=2,
            defaults={'mnemonique': 'Evaluation PG', 'label': "Niveau d'evaluation des plans de gestion"}
        )

        type_redac, _ = TypeNomenclature.objects.get_or_create(
            id_type=3,
            defaults={'mnemonique': 'Redacteur type', 'label': "Type de redacteur d'un plan de gestion"}
        )

        # Creer les nomenclatures de type de site
        for st in self.SITE_TYPES:
            Nomenclature.objects.update_or_create(
                id_nomenclature=st['id'],
                defaults={
                    'id_type': type_site,
                    'cd_nomenclature': None,
                    'mnemonique': st['mnemonique'],
                    'label': st['label'],
                    'actif': True
                }
            )
            self.log_item('site', f"{st['label']} ({st['mnemonique']})")

        # Creer les nomenclatures d'evaluation
        for et in self.EVAL_TYPES:
            Nomenclature.objects.update_or_create(
                id_nomenclature=et['id'],
                defaults={
                    'id_type': type_eval,
                    'cd_nomenclature': None,
                    'mnemonique': et['mnemonique'],
                    'label': et['label'],
                    'hierarchy': et.get('hierarchy'),
                    'actif': True
                }
            )
            self.log_item('eval', f"{et['label']} ({et['mnemonique']})")

        # Creer les nomenclatures de redacteur
        for rt in self.REDAC_TYPES:
            Nomenclature.objects.update_or_create(
                id_nomenclature=rt['id'],
                defaults={
                    'id_type': type_redac,
                    'cd_nomenclature': None,
                    'mnemonique': rt['mnemonique'],
                    'label': rt['label'],
                    'actif': True
                }
            )
            self.log_item('redac', f"{rt['label']} ({rt['mnemonique']})")

        self.log('  Nomenclatures creees', 'SUCCESS')

        result = {
            'type_site': type_site,
            'type_eval': type_eval,
            'type_redac': type_redac
        }
        self.context.set('nomenclatures', result)
        return result

    def reset(self) -> int:
        """
        Les nomenclatures ne sont pas supprimees car elles sont des donnees de reference.

        Returns:
            0 (aucune nomenclature supprimee)
        """
        return 0

    def get_dry_run_summary(self) -> List[str]:
        """
        Resume des nomenclatures qui seraient creees.

        Returns:
            Liste des lignes du resume
        """
        return [
            '\nNomenclatures:',
            '  - 3 types de nomenclature (site, evaluation, redacteur)',
            '  - 8 types de site (RNN, RNR, RNC, PPRN, PNR, ENS, APB, Autre)',
            "  - 3 types d'evaluation",
            '  - 3 types de redacteur',
        ]
