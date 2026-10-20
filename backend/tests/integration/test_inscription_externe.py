"""
#724 — Inscription sur une plateforme externe.

Une structure peut confier l'inscription à une autre plateforme (annuaire,
portail…) : son URL se règle dans Administration > Paramètres. Elle remplace
alors l'inscription locale — une seule porte d'entrée : les boutons « Créer
un compte » y mènent, et le formulaire local est refusé par le serveur.
"""
import pytest
from rest_framework.test import APIClient

from apps.core.models import SiteConfiguration
from tests.factories.users import AdminOrganismeFactory, SuperAdminFactory

pytestmark = [pytest.mark.django_db, pytest.mark.integration]

URL = 'https://inscription.example.org/cicada'
INSCRIPTION = {
    'email': 'nouveau@test.fr', 'password': 'StrongPass123!', 'password_confirm': 'StrongPass123!',
    'nom_role': 'Doe', 'prenom_role': 'Jane', 'identifiant': 'jdoe-externe',
}


def client(user=None):
    c = APIClient()
    if user:
        c.force_authenticate(user=user)
    return c


def test_vide_par_defaut_et_public():
    assert client().get('/api/settings/').json()['inscription_url_externe'] == ''


def test_reglable_par_le_super_admin():
    reponse = client(SuperAdminFactory()).patch(
        '/api/settings/', {'inscription_url_externe': URL}, format='json')
    assert reponse.status_code == 200
    assert reponse.json()['inscription_url_externe'] == URL
    assert client().get('/api/settings/').json()['inscription_url_externe'] == URL


def test_reservee_au_super_admin():
    reponse = client(AdminOrganismeFactory()).patch(
        '/api/settings/', {'inscription_url_externe': URL}, format='json')
    assert reponse.status_code == 403
    assert SiteConfiguration.get_instance().inscription_url_externe == ''


@pytest.mark.parametrize('valeur', ['javascript:alert(1)', 'pas une url', 'ftp://example.org'])
def test_url_http_seulement(valeur):
    reponse = client(SuperAdminFactory()).patch(
        '/api/settings/', {'inscription_url_externe': valeur}, format='json')
    assert reponse.status_code == 400


def test_l_inscription_locale_est_refusee_quand_l_url_est_renseignee():
    config = SiteConfiguration.get_instance()
    config.inscription_url_externe = URL
    config.save()
    reponse = client().post('/api/auth/register/', INSCRIPTION, format='json')
    assert reponse.status_code == 403
    assert reponse.json()['inscription_url_externe'] == URL


def test_vider_l_url_rouvre_l_inscription_locale():
    config = SiteConfiguration.get_instance()
    config.inscription_url_externe = URL
    config.save()
    client(SuperAdminFactory()).patch('/api/settings/', {'inscription_url_externe': ''}, format='json')
    reponse = client().post('/api/auth/register/', INSCRIPTION, format='json')
    assert reponse.status_code != 403
