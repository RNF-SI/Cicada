"""Comptes et sessions : désactiver coupe, se déconnecter révoque, les essais
de mot de passe sont limités, l'impersonation ne fait que regarder."""
import pytest
from django.core.cache import cache
from django.test import override_settings
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import RefreshToken

from apps.authentication.providers import usershub
from tests.factories.users import (
    AdminOrganismeFactory, OrganismeFactory, RoleFactory, SuperAdminFactory,
)

pytestmark = [pytest.mark.django_db, pytest.mark.integration]

MOT_DE_PASSE = 'Correct-cheval-42'


def _porteur(jeton):
    client = APIClient()
    client.credentials(HTTP_AUTHORIZATION=f'Bearer {jeton}')
    return client


@pytest.fixture
def compte():
    user = RoleFactory(email='agent@test.fr', identifiant='agent')
    user.set_password(MOT_DE_PASSE)
    user.save()
    return user


class TestDesactivation:
    def test_un_compte_desactive_perd_l_acces_des_la_requete_suivante(self, compte):
        acces = str(RefreshToken.for_user(compte).access_token)
        client = _porteur(acces)
        assert client.get('/api/auth/me/').status_code == 200
        compte.active = False
        compte.save()
        assert client.get('/api/auth/me/').status_code == 401
        assert client.get('/api/plans/plans/').status_code == 401

    def test_un_compte_desactive_ne_rafraichit_plus(self, compte):
        rafraichissement = str(RefreshToken.for_user(compte))
        compte.active = False
        compte.save()
        reponse = APIClient().post('/api/auth/refresh/', {'refresh': rafraichissement}, format='json')
        assert reponse.status_code == 401


class TestSessions:
    def test_la_deconnexion_revoque_le_jeton_de_rafraichissement(self, compte):
        jetons = RefreshToken.for_user(compte)
        client = _porteur(str(jetons.access_token))
        assert client.post('/api/auth/logout/', {'refresh': str(jetons)}, format='json').status_code == 200
        reponse = APIClient().post('/api/auth/refresh/', {'refresh': str(jetons)}, format='json')
        assert reponse.status_code == 401

    def test_on_ne_revoque_pas_le_jeton_d_un_autre(self, compte):
        autre = RefreshToken.for_user(RoleFactory())
        client = _porteur(str(RefreshToken.for_user(compte).access_token))
        assert client.post('/api/auth/logout/', {'refresh': str(autre)}, format='json').status_code == 400
        assert APIClient().post('/api/auth/refresh/', {'refresh': str(autre)}, format='json').status_code == 200

    def test_changer_son_mot_de_passe_ferme_les_autres_sessions(self, compte):
        acces = str(RefreshToken.for_user(compte).access_token)
        compte.set_password('Un-autre-mot-de-passe-7')
        compte.save()
        assert _porteur(acces).get('/api/auth/me/').status_code == 401

    def test_le_jeton_d_acces_est_court_en_production(self):
        # Le développement l'allonge (config/settings/development.py) ; la base,
        # celle de la production, le garde court.
        from config.settings import base
        assert base.SIMPLE_JWT['ACCESS_TOKEN_LIFETIME'].total_seconds() <= 3600
        assert base.SIMPLE_JWT['CHECK_REVOKE_TOKEN'] is True
        assert 'rest_framework_simplejwt.token_blacklist' in base.INSTALLED_APPS


def _connexion(identifiant, mot_de_passe, client_ip):
    # Apache d'entrée puis Apache du conteneur : « <forgé>, <client>, <proxy> ».
    return APIClient().post(
        '/api/auth/login/', {'username': identifiant, 'password': mot_de_passe}, format='json',
        HTTP_X_FORWARDED_FOR=f'6.6.6.{client_ip}, {client_ip_reel(client_ip)}, 10.0.0.2',
    )


def client_ip_reel(i):
    return f'203.0.113.{i}'


@pytest.fixture
def cache_vide():
    cache.clear()
    yield
    cache.clear()


class TestLimiteDesEssais:
    def test_changer_l_en_tete_forge_ne_contourne_plus_la_limite(self, compte, cache_vide, settings):
        """Le développement coupe les limites ; on remet celles de la production."""
        from config.settings import base
        from rest_framework.settings import api_settings
        from apps.authentication.throttles import AuthRateThrottle
        settings.REST_FRAMEWORK = {**base.REST_FRAMEWORK, 'NUM_PROXIES': 2}
        api_settings.reload()
        AuthRateThrottle.THROTTLE_RATES = api_settings.DEFAULT_THROTTLE_RATES
        try:
            codes = []
            for essai in range(7):
                reponse = APIClient().post(
                    '/api/auth/login/', {'username': 'inconnu', 'password': 'faux'}, format='json',
                    HTTP_X_FORWARDED_FOR=f'6.6.6.{essai}, 203.0.113.7, 10.0.0.2')
                codes.append(reponse.status_code)
            assert codes[-1] == 429, codes
        finally:
            settings.REST_FRAMEWORK = __import__('django.conf', fromlist=['settings']).settings.REST_FRAMEWORK
            api_settings.reload()
            AuthRateThrottle.THROTTLE_RATES = api_settings.DEFAULT_THROTTLE_RATES

    def test_un_compte_se_ferme_apres_dix_echecs_d_ou_qu_ils_viennent(self, compte, cache_vide):
        for essai in range(10):
            assert _connexion('agent', 'faux', essai).status_code in (401, 429)
        reponse = _connexion('agent', MOT_DE_PASSE, 99)
        assert reponse.status_code == 429
        assert 'tentatives' in reponse.json()['detail']

    def test_un_succes_remet_le_compteur_a_zero(self, compte, cache_vide):
        for essai in range(3):
            _connexion('agent', 'faux', essai)
        assert _connexion('agent', MOT_DE_PASSE, 50).status_code == 200
        from apps.authentication import echecs
        assert not echecs.bloque('agent')


class TestFuitesDInformation:
    def test_une_demande_en_attente_ne_se_devoile_pas_sans_son_mot_de_passe(self, db, cache_vide):
        from django.contrib.auth.hashers import make_password
        from tests.factories.notifications import PendingUserFactory
        organisme = OrganismeFactory(nom_organisme='Organisme Secret')
        PendingUserFactory(
            email='demandeur@test.fr', password_hash=make_password(MOT_DE_PASSE),
            requested_organisme=organisme)
        reponse = APIClient().post(
            '/api/auth/login/', {'username': 'demandeur@test.fr', 'password': 'faux'}, format='json')
        assert reponse.status_code == 401
        assert 'Organisme Secret' not in reponse.content.decode()
        assert 'attente' not in reponse.content.decode()

    def test_le_dernier_editeur_des_parametres_n_est_pas_public(self, db):
        reponse = APIClient().get('/api/settings/')
        if reponse.status_code == 200:
            assert reponse.json().get('updated_by_name') in (None, '')


class TestImpersonation:
    @override_settings(IMPERSONATION_ECRITURE=False)
    def test_un_jeton_d_impersonation_ne_peut_pas_ecrire(self, db):
        admin = SuperAdminFactory()
        cible = RoleFactory()
        client = APIClient()
        client.force_authenticate(admin)
        jetons = client.post(f'/api/auth/impersonate/{cible.pk}/', {'reason': 'test'}, format='json').json()
        imp = _porteur(jetons['access'])
        assert imp.get('/api/auth/me/').status_code == 200
        reponse = imp.post('/api/plans/plans/', {'nom': 'Écrit en se faisant passer'}, format='json')
        assert reponse.status_code == 403
        assert imp.post('/api/auth/stop-impersonation/', {}, format='json').status_code != 403


class TestRoles:
    def test_un_admin_d_organisme_ne_donne_pas_l_acces_a_l_admin_django(self, db):
        admin = AdminOrganismeFactory()
        collegue = RoleFactory(id_organisme=admin.id_organisme)
        client = APIClient()
        client.force_authenticate(admin)
        client.patch(f'/api/users/users/{collegue.pk}/', {'is_staff': True}, format='json')
        collegue.refresh_from_db()
        assert collegue.is_staff is False

    def test_usershub_ne_relie_pas_un_super_admin_par_son_email(self, db):
        SuperAdminFactory(email='chef@rnf.fr')
        identite = usershub.IdentiteUsersHub(id_role=4242, email='chef@rnf.fr', identifiant='chef')
        with pytest.raises(usershub.UsersHubErreur) as erreur:
            usershub.compte_pour(identite)
        assert erreur.value.status_code == 409

    def test_usershub_relie_un_admin_d_organisme_d_un_autre_organisme_non(self, db):
        AdminOrganismeFactory(email='admin@cen.fr')
        identite = usershub.IdentiteUsersHub(id_role=4243, email='admin@cen.fr', identifiant='admin')
        with pytest.raises(usershub.UsersHubErreur):
            usershub.compte_pour(identite)
