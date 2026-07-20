"""Tests de l'endpoint GET /api/campanule/autocomplete/ (#584)."""

import pytest
from rest_framework import status
from rest_framework.test import APIClient

from apps.campanule.models import AutocompleteProtocole
from tests.factories.users import RoleFactory


@pytest.fixture
def api_client():
    return APIClient()


@pytest.fixture
def protocoles(db):
    """Trois protocoles volontairement créés dans le désordre alphabétique."""
    return [
        AutocompleteProtocole.objects.create(
            cd_protocole=3,
            search_name='Suivi des chiroptères',
            lb_protocole_court='Suivi des chiroptères',
            lb_protocole_complet='Suivi des chiroptères en gîte',
            cible='Chiroptères',
        ),
        AutocompleteProtocole.objects.create(
            cd_protocole=1,
            search_name='Aile de papillon',
            lb_protocole_court='Aile de papillon',
            lb_protocole_complet='Protocole aile de papillon',
            cible='Insectes',
        ),
        AutocompleteProtocole.objects.create(
            cd_protocole=2,
            search_name='Comptage oiseaux',
            lb_protocole_court='Comptage oiseaux',
            lb_protocole_complet='Comptage des oiseaux nicheurs',
            cible='Oiseaux',
        ),
    ]


@pytest.mark.django_db
@pytest.mark.integration
class TestCampanuleAutocompleteEndpoint:

    def test_unauthenticated_returns_401(self, api_client):
        response = api_client.get('/api/campanule/autocomplete/')
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_empty_search_returns_alphabetical_list(self, api_client, protocoles):
        """#584 — sans terme de recherche, on renvoie la liste par ordre alphabétique."""
        api_client.force_authenticate(user=RoleFactory())

        response = api_client.get('/api/campanule/autocomplete/')

        assert response.status_code == status.HTTP_200_OK
        labels = [p['lb_protocole_court'] for p in response.data]
        assert labels == ['Aile de papillon', 'Comptage oiseaux', 'Suivi des chiroptères']

    def test_empty_search_respects_limit(self, api_client, protocoles):
        api_client.force_authenticate(user=RoleFactory())

        response = api_client.get('/api/campanule/autocomplete/', {'limit': 2})

        assert response.status_code == status.HTTP_200_OK
        assert len(response.data) == 2

    def test_empty_search_respects_cible_filter(self, api_client, protocoles):
        api_client.force_authenticate(user=RoleFactory())

        response = api_client.get('/api/campanule/autocomplete/', {'cible': 'Oiseaux'})

        assert response.status_code == status.HTTP_200_OK
        assert [p['cd_protocole'] for p in response.data] == [2]
