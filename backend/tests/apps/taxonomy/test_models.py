"""Tests unitaires pour les modèles TaxRef."""

import pytest
from django.db import connection

from apps.taxonomy.models import (
    BibTaxrefRang,
    BibTaxrefHabitat,
    BibTaxrefStatut,
    Taxref,
    TMetaTaxref,
)


@pytest.mark.django_db
@pytest.mark.unit
class TestBibTaxrefRang:
    """Tests pour le modèle BibTaxrefRang."""

    def test_create_rang(self):
        rang = BibTaxrefRang.objects.create(
            id_rang='ES', nom_rang='Espèce', tri_rang=22
        )
        assert rang.id_rang == 'ES'
        assert rang.nom_rang == 'Espèce'
        assert rang.tri_rang == 22

    def test_str_representation(self):
        rang = BibTaxrefRang.objects.create(
            id_rang='GN', nom_rang='Genre', tri_rang=15
        )
        assert str(rang) == 'Genre'


@pytest.mark.django_db
@pytest.mark.unit
class TestBibTaxrefHabitat:
    """Tests pour le modèle BibTaxrefHabitat."""

    def test_create_habitat(self):
        hab = BibTaxrefHabitat.objects.create(
            id_habitat=1, nom_habitat='Marin'
        )
        assert hab.id_habitat == 1
        assert str(hab) == 'Marin'


@pytest.mark.django_db
@pytest.mark.unit
class TestBibTaxrefStatut:
    """Tests pour le modèle BibTaxrefStatut."""

    def test_create_statut(self):
        stat = BibTaxrefStatut.objects.create(
            id_statut='P', nom_statut='Présent'
        )
        assert stat.id_statut == 'P'
        assert str(stat) == 'Présent'


@pytest.mark.django_db
@pytest.mark.unit
class TestTaxref:
    """Tests pour le modèle Taxref."""

    def test_create_taxon(self):
        taxon = Taxref.objects.create(
            cd_nom=60577,
            cd_ref=60577,
            id_rang='ES',
            regne='Animalia',
            phylum='Chordata',
            classe='Mammalia',
            ordre='Carnivora',
            famille='Canidae',
            lb_nom='Canis lupus',
            nom_complet='Canis lupus Linnaeus, 1758',
            nom_valide='Canis lupus Linnaeus, 1758',
            nom_vern='Loup gris',
            group2_inpn='Mammiferes',
        )
        assert taxon.cd_nom == 60577
        assert taxon.cd_ref == 60577
        assert taxon.regne == 'Animalia'

    def test_str_representation_with_nom_complet(self):
        taxon = Taxref.objects.create(
            cd_nom=1,
            nom_complet='Canis lupus Linnaeus, 1758',
        )
        assert str(taxon) == 'Canis lupus Linnaeus, 1758'

    def test_str_representation_with_lb_nom(self):
        taxon = Taxref.objects.create(cd_nom=2, lb_nom='Canis lupus')
        assert str(taxon) == 'Canis lupus'

    def test_str_representation_fallback(self):
        taxon = Taxref.objects.create(cd_nom=3)
        assert str(taxon) == 'cd_nom=3'

    def test_valid_name_filter(self):
        """Les noms valides ont cd_nom == cd_ref."""
        Taxref.objects.create(cd_nom=100, cd_ref=100, lb_nom='Valide')
        Taxref.objects.create(cd_nom=101, cd_ref=100, lb_nom='Synonyme')

        valid = Taxref.objects.filter(cd_nom__exact=models_F('cd_ref'))
        assert valid.count() == 1
        assert valid.first().lb_nom == 'Valide'


@pytest.mark.django_db
@pytest.mark.unit
class TestTMetaTaxref:
    """Tests pour le modèle TMetaTaxref."""

    def test_create_meta(self):
        meta = TMetaTaxref.objects.create(
            referential_name='taxref',
            version='18',
        )
        assert meta.referential_name == 'taxref'
        assert meta.version == '18'
        assert meta.update_date is not None

    def test_str_representation(self):
        meta = TMetaTaxref.objects.create(
            referential_name='taxref', version='18'
        )
        assert str(meta) == 'taxref v18'


# Helper pour le test de filtre cd_nom == cd_ref
from django.db.models import F as models_F
