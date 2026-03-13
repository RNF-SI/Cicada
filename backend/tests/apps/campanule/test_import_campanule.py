"""Tests pour la commande import_campanule."""

import pytest
from django.core.management import call_command
from django.db import connection

from apps.campanule.models import (
    AutocompleteProtocole,
    CampanuleAttribut,
    CampanuleDocsWeb,
    CampanuleMethode,
    CampanuleMethAttributsRel,
    CampanuleMethBiblioRel,
    CampanuleProtAttributsRel,
    CampanuleProtBiblioRel,
    CampanuleProtEchantillonnage,
    CampanuleProtMethRel,
    CampanuleProtocole,
    CampanuleProtTechRel,
    CampanuleTechnique,
    CampanuleTechAttributsRel,
    CampanuleTechBiblioRel,
)

# Flag module-level pour n'importer qu'une fois
_imported = False


def _ensure_imported():
    """Import CAMPanule une seule fois par session de tests."""
    global _imported
    if not _imported:
        call_command('import_campanule', '--force')
        _imported = True


@pytest.mark.django_db(transaction=True)
class TestImportCampanule:
    """Tests d'import du référentiel CAMPanule (10 tests)."""

    @pytest.fixture(autouse=True)
    def setup(self):
        _ensure_imported()

    def test_import_loads_main_tables(self):
        """Les 3 tables principales + complémentaires sont chargées."""
        assert CampanuleProtocole.objects.count() > 200
        assert CampanuleMethode.objects.count() > 10
        assert CampanuleTechnique.objects.count() > 100
        assert CampanuleAttribut.objects.count() > 100
        assert CampanuleProtEchantillonnage.objects.count() > 200
        assert CampanuleDocsWeb.objects.count() > 200

    def test_import_loads_correspondence_tables(self):
        """Les 8 tables de correspondance sont remplies."""
        assert CampanuleProtAttributsRel.objects.count() > 1000
        assert CampanuleProtBiblioRel.objects.count() > 100
        assert CampanuleProtMethRel.objects.count() > 30
        assert CampanuleProtTechRel.objects.count() > 300
        assert CampanuleMethAttributsRel.objects.count() > 20
        assert CampanuleMethBiblioRel.objects.count() > 20
        assert CampanuleTechAttributsRel.objects.count() > 500
        assert CampanuleTechBiblioRel.objects.count() > 100

    def test_autocomplete_excludes_obsolete(self):
        """L'autocomplete exclut les protocoles obsolètes."""
        autocomplete_count = AutocompleteProtocole.objects.count()
        total_count = CampanuleProtocole.objects.count()
        obsolete_count = CampanuleProtocole.objects.filter(
            obsolete='true'
        ).count()

        assert autocomplete_count == total_count - obsolete_count
        assert autocomplete_count > 0

    def test_protocole_data_integrity(self):
        """Les champs d'un protocole connu sont correctement importés."""
        epoc = CampanuleProtocole.objects.filter(
            lb_protocole_court__icontains='EPOC'
        ).first()
        assert epoc is not None
        assert epoc.cible == 'Oiseaux'
        assert 'Protocoles standardisés' in epoc.categorie_prot
        assert len(epoc.prot_auteur) > 0

    def test_technique_data_integrity(self):
        """Les champs d'une technique connue sont correctement importés."""
        tech = CampanuleTechnique.objects.filter(
            lb_technique_fr__icontains='filet'
        ).first()
        assert tech is not None
        assert tech.categorie_tech is not None
        assert tech.uuid is not None

    def test_relational_integrity(self):
        """Aucune relation orpheline dans prot_tech_rel."""
        prot_ids = set(
            CampanuleProtocole.objects.values_list('cd_protocole', flat=True)
        )
        tech_ids = set(
            CampanuleTechnique.objects.values_list('cd_technique', flat=True)
        )
        assert CampanuleProtTechRel.objects.exclude(
            cd_protocole__in=prot_ids
        ).count() == 0
        assert CampanuleProtTechRel.objects.exclude(
            cd_technique__in=tech_ids
        ).count() == 0

    def test_autocomplete_search(self):
        """La recherche ILIKE fonctionne sur la table autocomplete."""
        with connection.cursor() as cursor:
            cursor.execute("""
                SELECT COUNT(*) FROM ref_campanule.autocomplete_protocole
                WHERE search_name ILIKE %s
            """, ['%oiseaux%'])
            count = cursor.fetchone()[0]
        assert count > 0

    def test_attribut_categories(self):
        """Les 6 catégories d'attributs attendues sont présentes."""
        categories = set(
            CampanuleAttribut.objects.values_list(
                'categorie_attribut', flat=True
            ).distinct()
        )
        expected = {'DOMAINE', 'OBJECTIF', 'TYPE_CIBLE',
                    'GPE_GRAND_PUBLIC', 'MATERIEL', 'COLLECTE'}
        assert expected.issubset(categories)

    def test_idempotence(self):
        """L'import sans --force ne recharge pas."""
        count_before = CampanuleProtocole.objects.count()
        call_command('import_campanule')
        assert CampanuleProtocole.objects.count() == count_before

    def test_force_reloads(self):
        """L'import --force recharge correctement."""
        call_command('import_campanule', '--force')
        assert CampanuleProtocole.objects.count() > 200
