"""Tests d'intégration pour l'API HabRef."""

import pytest
from django.db import connection
from rest_framework.test import APIClient

from apps.habitats.models import (
    Habref, Typoref, AutocompleteHabitat, HabrefCorrespHab,
)
from tests.factories import RoleFactory


def _create_test_habitats():
    """Crée un ensemble de données de test pour HabRef."""
    Typoref.objects.create(
        cd_typo=7, lb_typo='EUNIS', territoire='France'
    )
    Typoref.objects.create(
        cd_typo=8, lb_typo='Corine Biotopes', territoire='Europe'
    )

    Habref.objects.create(
        cd_hab=1000, cd_typo=7, lb_code='G1.1',
        lb_hab_fr='Forêts riveraines', niveau=3,
        fg_validite='NR',
    )
    Habref.objects.create(
        cd_hab=2000, cd_typo=7, lb_code='C1.1',
        lb_hab_fr='Lacs et mares oligotrophes', niveau=3,
        fg_validite='NR',
    )
    Habref.objects.create(
        cd_hab=3000, cd_typo=8, lb_code='31.2',
        lb_hab_fr='Landes sèches', niveau=2,
        fg_validite='NR',
    )

    # Correspondance
    HabrefCorrespHab.objects.create(
        cd_hab=1000, cd_hab_entre=3000, cd_typo_entre=8,
        lb_hab_entre='Landes sèches', type_rel='est_equivalent',
    )

    # Autocomplete
    for hab in Habref.objects.all():
        AutocompleteHabitat.objects.create(
            cd_hab=hab.cd_hab,
            cd_typo=hab.cd_typo,
            lb_code=hab.lb_code,
            search_name=f'{hab.lb_code} {hab.lb_hab_fr}',
            lb_hab_fr=hab.lb_hab_fr,
            lb_typo=Typoref.objects.filter(
                cd_typo=hab.cd_typo
            ).first().lb_typo if hab.cd_typo else None,
            niveau=hab.niveau,
        )


@pytest.mark.django_db
@pytest.mark.integration
class TestHabrefDetailEndpoint:
    """Tests pour GET /api/habref/<cd_hab>/."""

    def setup_method(self):
        self.client = APIClient()
        self.user = RoleFactory()
        self.client.force_authenticate(user=self.user)
        _create_test_habitats()

    def test_detail_requires_auth(self):
        client = APIClient()
        response = client.get('/api/habref/1000/')
        assert response.status_code == 401

    def test_detail_returns_habitat(self):
        response = self.client.get('/api/habref/1000/')
        assert response.status_code == 200
        assert response.data['cd_hab'] == 1000
        assert response.data['lb_hab_fr'] == 'Forêts riveraines'

    def test_detail_not_found(self):
        response = self.client.get('/api/habref/0/')
        assert response.status_code == 404


@pytest.mark.django_db
@pytest.mark.integration
class TestHabrefTypoEndpoint:
    """Tests pour GET /api/habref/typo/."""

    def setup_method(self):
        self.client = APIClient()
        self.user = RoleFactory()
        self.client.force_authenticate(user=self.user)
        _create_test_habitats()

    def test_typo_list(self):
        response = self.client.get('/api/habref/typo/')
        assert response.status_code == 200
        assert len(response.data) == 2
        typo_names = [t['lb_typo'] for t in response.data]
        assert 'EUNIS' in typo_names
        assert 'Corine Biotopes' in typo_names


@pytest.mark.django_db
@pytest.mark.integration
class TestHabrefCorrespondanceEndpoint:
    """Tests pour GET /api/habref/correspondance/<cd_hab>/."""

    def setup_method(self):
        self.client = APIClient()
        self.user = RoleFactory()
        self.client.force_authenticate(user=self.user)
        _create_test_habitats()

    def test_correspondance_returns_results(self):
        response = self.client.get('/api/habref/correspondance/1000/')
        assert response.status_code == 200
        assert len(response.data) == 1
        assert response.data[0]['cd_hab_entre'] == 3000

    def test_correspondance_empty(self):
        response = self.client.get('/api/habref/correspondance/2000/')
        assert response.status_code == 200
        assert len(response.data) == 0


@pytest.mark.django_db
@pytest.mark.integration
class TestHabrefAutocompleteEndpoint:
    """Tests pour GET /api/habref/autocomplete/."""

    def setup_method(self):
        self.client = APIClient()
        self.user = RoleFactory()
        self.client.force_authenticate(user=self.user)
        _create_test_habitats()
        # Créer les index trigramme pour l'autocomplete
        with connection.cursor() as cursor:
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_autocomplete_habitat_trgm_test
                ON ref_habitats.autocomplete_habitat
                USING gin (search_name gin_trgm_ops)
            """)

    def test_autocomplete_requires_min_2_chars(self):
        response = self.client.get(
            '/api/habref/autocomplete/', {'search': 'a'}
        )
        assert response.status_code == 200
        assert response.data == []

    def test_autocomplete_finds_by_name(self):
        response = self.client.get(
            '/api/habref/autocomplete/', {'search': 'Forêts'}
        )
        assert response.status_code == 200
        assert len(response.data) >= 1
        cd_habs = [r['cd_hab'] for r in response.data]
        assert 1000 in cd_habs

    def test_autocomplete_filter_by_cd_typo(self):
        response = self.client.get(
            '/api/habref/autocomplete/',
            {'search': 'Landes', 'cd_typo': '8'},
        )
        assert response.status_code == 200
        for r in response.data:
            assert r['cd_typo'] == 8
