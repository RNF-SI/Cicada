"""Tests pour la commande import_taxref."""

import csv
import io
import os
import tempfile

import pytest
from django.core.management import call_command
from django.db import connection

from apps.taxonomy.models import (
    BibTaxrefRang,
    BibTaxrefHabitat,
    BibTaxrefStatut,
    Taxref,
    TMetaTaxref,
)
from apps.taxonomy.management.commands.import_taxref import (
    RANGS, HABITATS, STATUTS, TAXREF_CSV_COLUMNS,
    LITE_RANGS_ALLOWED, LITE_GROUP_CAPS,
)


def _create_test_csv(tmpdir, rows, encoding='latin-1'):
    """Crée un fichier CSV TaxRef de test."""
    # TAXREF_CSV_COLUMNS contient les noms CSV en majuscules (CD_NOM, FR, RANG, etc.)
    csv_path = os.path.join(tmpdir, 'TAXREFv18.txt')
    with open(csv_path, 'w', encoding=encoding, newline='') as f:
        writer = csv.DictWriter(f, fieldnames=TAXREF_CSV_COLUMNS,
                                delimiter='\t')
        writer.writeheader()
        for row in rows:
            writer.writerow(row)
    return csv_path


def _make_taxon_row(cd_nom, cd_ref=None, rang='ES', regne='Animalia',
                     group2='Mammiferes', lb_nom='Test taxon',
                     nom_vern='Taxon test'):
    """Crée une ligne de données taxon pour les tests.

    Utilise les noms de colonnes CSV (majuscules) tels qu'ils apparaissent
    dans le vrai fichier TaxRef.
    """
    if cd_ref is None:
        cd_ref = cd_nom
    return {
        'CD_NOM': str(cd_nom),
        'FR': 'P',
        'HABITAT': '3',
        'RANG': rang,
        'REGNE': regne,
        'PHYLUM': 'Chordata',
        'CLASSE': 'Mammalia',
        'ORDRE': 'Carnivora',
        'FAMILLE': 'Canidae',
        'SOUS_FAMILLE': '',
        'TRIBU': '',
        'CD_TAXSUP': '',
        'CD_SUP': '',
        'CD_REF': str(cd_ref),
        'LB_NOM': lb_nom,
        'LB_AUTEUR': 'Linnaeus, 1758',
        'NOM_COMPLET': f'{lb_nom} Linnaeus, 1758',
        'NOM_COMPLET_HTML': f'<i>{lb_nom}</i> Linnaeus, 1758',
        'NOM_VALIDE': f'{lb_nom} Linnaeus, 1758',
        'NOM_VERN': nom_vern,
        'NOM_VERN_ENG': '',
        'GROUP1_INPN': 'Mammifères',
        'GROUP2_INPN': group2,
        'GROUP3_INPN': '',
        'URL': '',
    }


@pytest.mark.django_db
@pytest.mark.unit
class TestLoadReferenceData:
    """Tests pour le chargement des données de référence."""

    def test_rangs_count(self):
        """Vérifie que toutes les données de référence sont définies."""
        assert len(RANGS) == 16

    def test_habitats_count(self):
        assert len(HABITATS) == 8

    def test_statuts_count(self):
        assert len(STATUTS) == 15

    def test_lite_rangs_are_subset(self):
        """Les rangs autorisés en mode lite sont un sous-ensemble des rangs."""
        all_rang_codes = {r[0] for r in RANGS}
        assert LITE_RANGS_ALLOWED.issubset(all_rang_codes)


@pytest.mark.django_db
@pytest.mark.unit
class TestLiteFilter:
    """Tests pour le filtre du mode lite."""

    def test_lite_filter_excludes_synonyms(self):
        """En mode lite, les synonymes (cd_nom != cd_ref) sont exclus."""
        from collections import defaultdict
        from apps.taxonomy.management.commands.import_taxref import Command

        cmd = Command()
        group_counts = defaultdict(int)

        # Nom de référence : inclus
        row_valid = {'CD_NOM': '100', 'CD_REF': '100', 'RANG': 'ES',
                     'GROUP2_INPN': 'Mammiferes'}
        assert cmd._should_include_row_lite(row_valid, group_counts) is True

        # Synonyme : exclu
        row_syn = {'CD_NOM': '101', 'CD_REF': '100', 'RANG': 'ES',
                   'GROUP2_INPN': 'Mammiferes'}
        assert cmd._should_include_row_lite(row_syn, group_counts) is False

    def test_lite_filter_excludes_subspecies(self):
        """En mode lite, les sous-espèces sont exclues."""
        from collections import defaultdict
        from apps.taxonomy.management.commands.import_taxref import Command

        cmd = Command()
        group_counts = defaultdict(int)

        row = {'CD_NOM': '100', 'CD_REF': '100', 'RANG': 'SSES',
               'GROUP2_INPN': 'Mammiferes'}
        assert cmd._should_include_row_lite(row, group_counts) is False

    def test_lite_filter_respects_group_cap(self):
        """En mode lite, le cap par groupe est respecté."""
        from collections import defaultdict
        from apps.taxonomy.management.commands.import_taxref import Command

        cmd = Command()
        group_counts = defaultdict(int)

        # On devrait pouvoir ajouter jusqu'au cap
        cap = LITE_GROUP_CAPS.get('Mammiferes', 50)
        for i in range(cap):
            row = {'CD_NOM': str(i), 'CD_REF': str(i), 'RANG': 'ES',
                   'GROUP2_INPN': 'Mammiferes'}
            cmd._should_include_row_lite(row, group_counts)

        # Le suivant devrait être refusé
        row_over = {'CD_NOM': str(cap + 1), 'CD_REF': str(cap + 1),
                    'RANG': 'ES', 'GROUP2_INPN': 'Mammiferes'}
        assert cmd._should_include_row_lite(
            row_over, group_counts
        ) is False


@pytest.mark.django_db
@pytest.mark.integration
class TestImportTaxrefCommand:
    """Tests d'intégration pour la commande import_taxref avec CSV mockés."""

    def test_import_with_test_csv(self):
        """Test de l'import avec un fichier CSV de test."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Créer un faux ZIP contenant un CSV
            rows = [
                _make_taxon_row(1, lb_nom='Canis lupus',
                                nom_vern='Loup gris'),
                _make_taxon_row(2, lb_nom='Vulpes vulpes',
                                nom_vern='Renard roux'),
                _make_taxon_row(3, cd_ref=1,
                                lb_nom='Canis lupus synonym'),
            ]

            # Créer directement le CSV dans un sous-répertoire
            extract_dir = os.path.join(tmpdir, 'TAXREF_v18')
            os.makedirs(extract_dir)
            _create_test_csv(extract_dir, rows)

            # Créer un ZIP factice pour le cache
            import zipfile
            zip_path = os.path.join(tmpdir, 'TAXREF_v18.zip')
            with zipfile.ZipFile(zip_path, 'w') as zf:
                csv_path = os.path.join(extract_dir, 'TAXREFv18.txt')
                zf.write(csv_path, 'TAXREFv18.txt')

            # Lancer l'import
            call_command(
                'import_taxref',
                '--force',
                '--cache-dir', tmpdir,
                verbosity=0,
            )

            # Vérifier les résultats
            assert Taxref.objects.count() == 3
            assert BibTaxrefRang.objects.count() == 16
            assert BibTaxrefHabitat.objects.count() == 8
            assert BibTaxrefStatut.objects.count() == 15

            meta = TMetaTaxref.objects.filter(
                referential_name='taxref'
            ).first()
            assert meta is not None
            assert meta.version == '18'

    def test_import_lite_with_test_csv(self):
        """Test de l'import en mode lite."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Créer des taxons avec différents rangs et groupes
            rows = [
                _make_taxon_row(1, rang='ES', group2='Mammiferes',
                                lb_nom='Espece valide'),
                _make_taxon_row(2, rang='SSES', group2='Mammiferes',
                                lb_nom='Sous-espece'),
                _make_taxon_row(3, cd_ref=1, rang='ES',
                                group2='Mammiferes',
                                lb_nom='Synonyme'),
                _make_taxon_row(4, rang='ES', group2='Oiseaux',
                                lb_nom='Oiseau test'),
            ]

            extract_dir = os.path.join(tmpdir, 'TAXREF_v18')
            os.makedirs(extract_dir)
            _create_test_csv(extract_dir, rows)

            import zipfile
            zip_path = os.path.join(tmpdir, 'TAXREF_v18.zip')
            with zipfile.ZipFile(zip_path, 'w') as zf:
                csv_path = os.path.join(extract_dir, 'TAXREFv18.txt')
                zf.write(csv_path, 'TAXREFv18.txt')

            call_command(
                'import_taxref',
                '--force',
                '--lite',
                '--cache-dir', tmpdir,
                verbosity=0,
            )

            # En mode lite : seuls les noms valides, rang ES ou supérieur
            # -> cd_nom=1 (ES, valide), cd_nom=4 (ES, valide, Oiseaux)
            # Exclus : cd_nom=2 (SSES), cd_nom=3 (synonyme)
            assert Taxref.objects.count() == 2
            assert Taxref.objects.filter(cd_nom=1).exists()
            assert Taxref.objects.filter(cd_nom=4).exists()
            assert not Taxref.objects.filter(cd_nom=2).exists()
            assert not Taxref.objects.filter(cd_nom=3).exists()

            meta = TMetaTaxref.objects.filter(
                referential_name='taxref_lite'
            ).first()
            assert meta is not None

    def test_idempotent_import(self):
        """L'import ne re-lance pas si la version est déjà installée."""
        TMetaTaxref.objects.create(
            referential_name='taxref', version='18'
        )
        # Cet appel ne devrait rien faire (pas de --force)
        out = io.StringIO()
        call_command('import_taxref', stdout=out, verbosity=1)
        assert 'déjà installé' in out.getvalue()
