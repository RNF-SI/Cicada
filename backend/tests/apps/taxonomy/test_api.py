"""Tests d'intégration pour l'API TaxRef."""

import pytest
from rest_framework.test import APIClient

from apps.taxonomy.models import Taxref, TMetaTaxref, VMTaxrefListForAutocomplete
from django.db import connection

from tests.factories import RoleFactory


def _create_test_taxons():
    """Crée un ensemble de taxons de test."""
    Taxref.objects.create(
        cd_nom=60577, cd_ref=60577, id_rang='ES',
        regne='Animalia', classe='Mammalia', ordre='Carnivora',
        famille='Canidae', lb_nom='Canis lupus',
        nom_complet='Canis lupus Linnaeus, 1758',
        nom_valide='Canis lupus Linnaeus, 1758',
        nom_vern='Loup gris',
        group2_inpn='Mammiferes',
    )
    Taxref.objects.create(
        cd_nom=3811, cd_ref=3811, id_rang='ES',
        regne='Animalia', classe='Aves', ordre='Falconiformes',
        famille='Accipitridae', lb_nom='Aquila chrysaetos',
        nom_complet='Aquila chrysaetos (Linnaeus, 1758)',
        nom_valide='Aquila chrysaetos (Linnaeus, 1758)',
        nom_vern='Aigle royal',
        group2_inpn='Oiseaux',
    )
    Taxref.objects.create(
        cd_nom=79301, cd_ref=79301, id_rang='ES',
        regne='Plantae', classe='Equisetopsida',
        ordre='Lamiales', famille='Plantaginaceae',
        lb_nom='Plantago lanceolata',
        nom_complet='Plantago lanceolata L., 1753',
        nom_valide='Plantago lanceolata L., 1753',
        nom_vern='Plantain lancéolé',
        group2_inpn='Angiospermes',
    )
    # Un synonyme (cd_nom != cd_ref)
    Taxref.objects.create(
        cd_nom=99999, cd_ref=60577, id_rang='ES',
        regne='Animalia', classe='Mammalia',
        lb_nom='Canis lupus subsp.',
        nom_complet='Canis lupus subsp.',
        group2_inpn='Mammiferes',
    )


def _refresh_materialized_view():
    """Recrée la vue matérialisée avec les données de test."""
    with connection.cursor() as cursor:
        cursor.execute(
            'DROP MATERIALIZED VIEW IF EXISTS '
            'taxonomie.vm_taxref_list_forautocomplete'
        )
        cursor.execute("""
            CREATE MATERIALIZED VIEW taxonomie.vm_taxref_list_forautocomplete AS
            SELECT
                t.cd_nom,
                t.cd_ref,
                COALESCE(t.lb_nom, '') || ' ' || COALESCE(t.nom_vern, '')
                    AS search_name,
                t.nom_valide,
                t.nom_vern,
                t.lb_nom,
                t.regne,
                t.group2_inpn,
                t.id_rang
            FROM taxonomie.taxref t
            WHERE t.cd_nom = t.cd_ref
            ORDER BY t.lb_nom
        """)
        cursor.execute("""
            CREATE UNIQUE INDEX IF NOT EXISTS idx_vm_test_cd_nom
            ON taxonomie.vm_taxref_list_forautocomplete (cd_nom)
        """)


@pytest.mark.django_db
@pytest.mark.integration
class TestTaxrefListEndpoint:
    """Tests pour GET /api/taxref/."""

    def setup_method(self):
        self.client = APIClient()
        self.user = RoleFactory()
        self.client.force_authenticate(user=self.user)
        _create_test_taxons()

    def test_list_requires_auth(self):
        client = APIClient()
        response = client.get('/api/taxref/')
        assert response.status_code == 401

    def test_list_returns_taxons(self):
        response = self.client.get('/api/taxref/')
        assert response.status_code == 200

    def test_filter_by_regne(self):
        response = self.client.get('/api/taxref/', {'regne': 'Animalia'})
        assert response.status_code == 200
        results = response.data.get('results', response.data)
        for taxon in results:
            assert taxon['regne'] == 'Animalia'

    def test_filter_by_group2_inpn(self):
        response = self.client.get(
            '/api/taxref/', {'group2_inpn': 'Oiseaux'}
        )
        assert response.status_code == 200
        results = response.data.get('results', response.data)
        assert len(results) == 1
        assert results[0]['lb_nom'] == 'Aquila chrysaetos'


@pytest.mark.django_db
@pytest.mark.integration
class TestTaxrefDetailEndpoint:
    """Tests pour GET /api/taxref/<cd_nom>/."""

    def setup_method(self):
        self.client = APIClient()
        self.user = RoleFactory()
        self.client.force_authenticate(user=self.user)
        _create_test_taxons()

    def test_detail_returns_taxon(self):
        response = self.client.get('/api/taxref/60577/')
        assert response.status_code == 200
        assert response.data['cd_nom'] == 60577
        assert response.data['lb_nom'] == 'Canis lupus'
        assert response.data['nom_vern'] == 'Loup gris'

    def test_detail_not_found(self):
        response = self.client.get('/api/taxref/0/')
        assert response.status_code == 404


@pytest.mark.django_db
@pytest.mark.integration
class TestTaxrefVersionEndpoint:
    """Tests pour GET /api/taxref/version/."""

    def setup_method(self):
        self.client = APIClient()
        self.user = RoleFactory()
        self.client.force_authenticate(user=self.user)

    def test_version_returns_404_when_empty(self):
        response = self.client.get('/api/taxref/version/')
        assert response.status_code == 404

    def test_version_returns_meta(self):
        TMetaTaxref.objects.create(
            referential_name='taxref', version='18'
        )
        response = self.client.get('/api/taxref/version/')
        assert response.status_code == 200
        assert response.data['version'] == '18'
        assert response.data['referential_name'] == 'taxref'


@pytest.mark.django_db
@pytest.mark.integration
class TestTaxrefAutocompleteEndpoint:
    """Tests pour GET /api/taxref/autocomplete/."""

    def setup_method(self):
        self.client = APIClient()
        self.user = RoleFactory()
        self.client.force_authenticate(user=self.user)
        _create_test_taxons()
        _refresh_materialized_view()

    def test_autocomplete_requires_min_2_chars(self):
        response = self.client.get('/api/taxref/autocomplete/', {'search': 'a'})
        assert response.status_code == 200
        assert response.data == []

    def test_autocomplete_finds_by_latin_name(self):
        response = self.client.get(
            '/api/taxref/autocomplete/', {'search': 'Canis'}
        )
        assert response.status_code == 200
        assert len(response.data) >= 1
        cd_noms = [r['cd_nom'] for r in response.data]
        assert 60577 in cd_noms

    def test_autocomplete_finds_by_vernacular_name(self):
        response = self.client.get(
            '/api/taxref/autocomplete/', {'search': 'Loup'}
        )
        assert response.status_code == 200
        assert len(response.data) >= 1

    def test_autocomplete_respects_limit(self):
        response = self.client.get(
            '/api/taxref/autocomplete/', {'search': 'a', 'limit': '1'}
        )
        # search 'a' is <2 chars, returns empty
        assert response.status_code == 200

    def test_autocomplete_filter_by_regne(self):
        response = self.client.get(
            '/api/taxref/autocomplete/',
            {'search': 'Plan', 'regne': 'Plantae'},
        )
        assert response.status_code == 200
        for r in response.data:
            assert r['regne'] == 'Plantae'


@pytest.mark.django_db
@pytest.mark.integration
class TestTaxrefSearchFieldEndpoint:
    """Tests pour GET /api/taxref/search/<field>/<ilike>/."""

    def setup_method(self):
        self.client = APIClient()
        self.user = RoleFactory()
        self.client.force_authenticate(user=self.user)
        _create_test_taxons()

    def test_search_by_nom_vern(self):
        response = self.client.get('/api/taxref/search/nom_vern/Loup/')
        assert response.status_code == 200
        assert len(response.data) >= 1
        assert response.data[0]['cd_nom'] == 60577

    def test_search_invalid_field(self):
        response = self.client.get('/api/taxref/search/invalid_field/test/')
        assert response.status_code == 400

    def test_search_by_famille(self):
        response = self.client.get('/api/taxref/search/famille/Canidae/')
        assert response.status_code == 200
        assert len(response.data) >= 1
