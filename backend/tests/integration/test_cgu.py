"""
#746 — Conditions générales d'utilisation propres à l'instance.

Le super admin rédige les CGU (Markdown) dans Administration > Paramètres ;
des CGU par défaut sont fournies. Chaque modification du texte en publie une
nouvelle version : tout utilisateur qui n'a pas accepté la version en vigueur
doit le faire avant de continuer (`cgu_a_accepter`).
"""
from datetime import timedelta

import pytest
from django.utils import timezone
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import RefreshToken

from apps.core.cgu import CGU_PAR_DEFAUT
from apps.core.models import SiteConfiguration
from tests.factories.users import AdminOrganismeFactory, SuperAdminFactory, RoleFactory

pytestmark = [pytest.mark.django_db, pytest.mark.integration]

ACCEPTER = '/api/auth/cgu/accepter/'


def client(user=None):
    c = APIClient()
    if user:
        c.force_authenticate(user=user)
    return c


def version():
    return SiteConfiguration.get_instance().cgu_version.isoformat()


class TestTexte:
    def test_cgu_par_defaut_publiques(self):
        data = client().get('/api/settings/').json()
        assert data['cgu_texte'] == CGU_PAR_DEFAUT
        assert data['cgu_version']

    def test_les_cgu_par_defaut_annoncent_la_centralisation_publique(self):
        texte = CGU_PAR_DEFAUT.lower()
        assert 'centralisation' in texte
        assert 'public' in texte

    def test_modifier_le_texte_publie_une_nouvelle_version(self):
        avant = SiteConfiguration.get_instance().cgu_version
        reponse = client(SuperAdminFactory()).patch(
            '/api/settings/', {'cgu_texte': '# Mes CGU'}, format='json')
        assert reponse.status_code == 200
        config = SiteConfiguration.get_instance()
        assert config.cgu_texte == '# Mes CGU'
        assert config.cgu_version > avant

    def test_un_autre_reglage_ne_change_pas_la_version(self):
        avant = SiteConfiguration.get_instance().cgu_version
        client(SuperAdminFactory()).patch(
            '/api/settings/', {'cgu_texte': CGU_PAR_DEFAUT, 'accueil_titre': 'Bonjour'}, format='json')
        assert SiteConfiguration.get_instance().cgu_version == avant

    def test_texte_vide_refuse(self):
        reponse = client(SuperAdminFactory()).patch(
            '/api/settings/', {'cgu_texte': '   '}, format='json')
        assert reponse.status_code == 400

    def test_reserve_au_super_admin(self):
        reponse = client(AdminOrganismeFactory()).patch(
            '/api/settings/', {'cgu_texte': 'x'}, format='json')
        assert reponse.status_code == 403


class TestAcceptation:
    def test_un_nouvel_utilisateur_doit_accepter(self):
        assert client(RoleFactory()).get('/api/auth/me/').json()['cgu_a_accepter'] is True

    def test_accepter_la_version_en_vigueur(self):
        user = RoleFactory()
        reponse = client(user).post(ACCEPTER, {'version': version()}, format='json')
        assert reponse.status_code == 200
        assert reponse.json()['cgu_a_accepter'] is False
        user.refresh_from_db()
        assert user.cgu_acceptees_le is not None
        assert client(user).get('/api/auth/me/').json()['cgu_a_accepter'] is False

    def test_une_nouvelle_version_redemande_l_acceptation(self):
        user = RoleFactory()
        client(user).post(ACCEPTER, {'version': version()}, format='json')
        client(SuperAdminFactory()).patch('/api/settings/', {'cgu_texte': '# V2'}, format='json')
        assert client(user).get('/api/auth/me/').json()['cgu_a_accepter'] is True

    def test_version_perimee_refusee(self):
        """Le texte a changé pendant la lecture : accepter l'ancien ne vaut pas."""
        user = RoleFactory()
        ancienne = (SiteConfiguration.get_instance().cgu_version - timedelta(days=1)).isoformat()
        reponse = client(user).post(ACCEPTER, {'version': ancienne}, format='json')
        assert reponse.status_code == 409
        user.refresh_from_db()
        assert user.cgu_acceptees_le is None

    def test_anonyme_refuse(self):
        assert client().post(ACCEPTER, {'version': version()}, format='json').status_code == 401

    def test_impersonation_n_accepte_pas_a_la_place_de_l_utilisateur(self):
        user = RoleFactory()
        jeton = RefreshToken.for_user(user).access_token
        jeton['is_impersonating'] = True
        c = APIClient()
        c.credentials(HTTP_AUTHORIZATION=f'Bearer {jeton}')
        reponse = c.post(ACCEPTER, {'version': version()}, format='json')
        assert reponse.status_code == 403
        user.refresh_from_db()
        assert user.cgu_acceptees_le is None

    def test_la_connexion_indique_les_cgu_a_accepter(self):
        RoleFactory(email='cgu@test.fr', password='Test123!')
        reponse = APIClient().post(
            '/api/auth/login/', {'username': 'cgu@test.fr', 'password': 'Test123!'}, format='json')
        assert reponse.status_code == 200
        assert reponse.json()['user']['cgu_a_accepter'] is True

    def test_acceptation_anterieure_a_la_version(self):
        user = RoleFactory()
        user.cgu_acceptees_le = timezone.now() - timedelta(days=365)
        user.save()
        assert client(user).get('/api/auth/me/').json()['cgu_a_accepter'] is True
