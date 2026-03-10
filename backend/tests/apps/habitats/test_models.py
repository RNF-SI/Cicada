"""Tests unitaires pour les modèles HabRef."""

import pytest

from apps.habitats.models import (
    Typoref,
    Habref,
    HabrefCorrespHab,
    HabrefCorrespTaxon,
    AutocompleteHabitat,
)


@pytest.mark.django_db
@pytest.mark.unit
class TestTyporef:
    """Tests pour le modèle Typoref."""

    def test_create_typoref(self):
        typo = Typoref.objects.create(
            cd_typo=7,
            lb_typo='EUNIS',
            territoire='France',
        )
        assert typo.cd_typo == 7
        assert str(typo) == 'EUNIS'

    def test_str_representation_fallback(self):
        typo = Typoref.objects.create(cd_typo=99)
        assert str(typo) == 'Typo 99'


@pytest.mark.django_db
@pytest.mark.unit
class TestHabref:
    """Tests pour le modèle Habref."""

    def test_create_habitat(self):
        hab = Habref.objects.create(
            cd_hab=1234,
            cd_typo=7,
            lb_code='G1.1',
            lb_hab_fr='Forêts riveraines',
            niveau=3,
        )
        assert hab.cd_hab == 1234
        assert hab.lb_hab_fr == 'Forêts riveraines'
        assert str(hab) == 'Forêts riveraines'

    def test_str_fallback(self):
        hab = Habref.objects.create(cd_hab=5678)
        assert str(hab) == 'cd_hab=5678'

    def test_hierarchy(self):
        parent = Habref.objects.create(cd_hab=1, lb_hab_fr='Parent', niveau=1)
        child = Habref.objects.create(
            cd_hab=2, lb_hab_fr='Enfant', niveau=2, cd_hab_sup=1
        )
        assert child.cd_hab_sup == parent.cd_hab


@pytest.mark.django_db
@pytest.mark.unit
class TestHabrefCorrespHab:
    """Tests pour le modèle HabrefCorrespHab."""

    def test_create_correspondance(self):
        corr = HabrefCorrespHab.objects.create(
            cd_hab=100,
            cd_hab_entre=200,
            cd_typo_entre=8,
            lb_hab_entre='Correspondance test',
            type_rel='est_equivalent',
        )
        assert corr.cd_hab == 100
        assert corr.cd_hab_entre == 200


@pytest.mark.django_db
@pytest.mark.unit
class TestHabrefCorrespTaxon:
    """Tests pour le modèle HabrefCorrespTaxon."""

    def test_create_correspondance_taxon(self):
        corr = HabrefCorrespTaxon.objects.create(
            cd_hab=100,
            cd_nom=60577,
            nom_cite='Canis lupus',
        )
        assert corr.cd_hab == 100
        assert corr.cd_nom == 60577


@pytest.mark.django_db
@pytest.mark.unit
class TestAutocompleteHabitat:
    """Tests pour le modèle AutocompleteHabitat."""

    def test_create_autocomplete(self):
        auto = AutocompleteHabitat.objects.create(
            cd_hab=1234,
            cd_typo=7,
            lb_code='G1.1',
            search_name='G1.1 Forêts riveraines',
            lb_hab_fr='Forêts riveraines',
            lb_typo='EUNIS',
            niveau=3,
        )
        assert str(auto) == 'G1.1 Forêts riveraines'
