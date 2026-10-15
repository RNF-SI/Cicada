"""
Connexion par un GeoNature / UsersHub (#689) et rattachement à l'organisme (#691).

GeoNature est simulé : on remplace les appels HTTP du module par des réponses
préparées. Ce qui est vérifié, c'est ce que CICADA fait de ces réponses.
"""
import uuid
from unittest import mock

import pytest
import requests
from rest_framework.test import APIClient

from apps.users.models import BibOrganismes, Role
from tests.factories.users import AdminOrganismeFactory, OrganismeFactory, RoleFactory

URL = '/api/auth/login-geonature/'
GN = 'https://geonature.test/api'
MODULE = 'apps.authentication.providers.usershub.requests'

pytestmark = [pytest.mark.django_db, pytest.mark.integration]


@pytest.fixture(autouse=True)
def geonature_configure(settings):
    settings.AUTH_PROVIDER = 'geonature'
    settings.GEONATURE_AUTH_URL = GN
    settings.GEONATURE_AUTH_ID_APPLICATION = '14'
    settings.GEONATURE_AUTH_LIBELLE = 'RNF'
    settings.GEONATURE_AUTH_ORGANISMES_EXCLUS = {-1, 2}


@pytest.fixture(autouse=True)
def sans_throttle(settings):
    from django.core.cache import cache
    cache.clear()


def reponse(status_code=200, json=None):
    r = mock.Mock(status_code=status_code)
    r.json.return_value = json
    return r


def utilisateur_gn(**kwargs):
    user = {
        'id_role': 146, 'identifiant': 'cdupont', 'email': 'claire.dupont@reserve.fr',
        'nom_role': 'Dupont', 'prenom_role': 'Claire', 'id_organisme': 3,
    }
    user.update(kwargs)
    return {'token': 'jeton-gn', 'expires': '2026-10-14T10:00:00', 'user': user}


def fiche_organisme(uuid_organisme, nom='Réserves Naturelles de France', **kwargs):
    fiche = {'id_organisme': 3, 'uuid_organisme': str(uuid_organisme), 'nom_organisme': nom,
             'ville_organisme': 'Dijon', 'cp_organisme': '21000'}
    fiche.update(kwargs)
    return fiche


def connecter(login_json, organisme_json=None, organisme_status=200):
    """Simule GeoNature et poste une connexion. Renvoie (réponse CICADA, mock requests)."""
    with mock.patch(MODULE) as req:
        req.RequestException = requests.RequestException
        req.post.return_value = login_json if isinstance(login_json, mock.Mock) else reponse(200, login_json)
        req.get.return_value = reponse(organisme_status, organisme_json)
        res = APIClient().post(URL, {'login': 'cdupont', 'password': 'secret'}, format='json')
    return res, req


class TestUnSeulModeDeConnexion:
    """Un seul mode à la fois : jamais GeoNature et mot de passe CICADA en parallèle."""

    def test_mode_geonature_annonce(self):
        res = APIClient().get('/api/auth/mode/')
        assert res.status_code == 200
        assert res.json() == {'mode': 'geonature', 'libelle': 'RNF'}

    def test_mode_local_par_defaut(self, settings):
        settings.AUTH_PROVIDER = 'local'
        assert APIClient().get('/api/auth/mode/').json() == {'mode': 'local'}
        # La connexion GeoNature n'existe pas en mode local, même réglée.
        res = APIClient().post(URL, {'login': 'x', 'password': 'y'}, format='json')
        assert res.status_code == 404

    def test_mot_de_passe_cicada_refuse_en_mode_geonature(self):
        compte = RoleFactory(email='local@test.fr')
        compte.set_password('MotDePasse123!')
        compte.save()
        res = APIClient().post('/api/auth/login/', {'username': 'local@test.fr', 'password': 'MotDePasse123!'},
                               format='json')
        assert res.status_code == 403
        assert 'RNF' in res.json()['detail']

    @pytest.mark.parametrize('url, corps', [
        ('/api/auth/register/', {'email': 'n@test.fr'}),
        ('/api/auth/password-reset/', {'email': 'n@test.fr'}),
        ('/api/auth/password-reset/confirm/', {'uid': 'x', 'token': 'y', 'new_password': 'zzzzzzzz'}),
    ])
    def test_inscription_et_mot_de_passe_oublie_fermes(self, url, corps):
        res = APIClient().post(url, corps, format='json')
        assert res.status_code == 403

    def test_changement_de_mot_de_passe_ferme(self):
        compte = RoleFactory()
        client = APIClient()
        client.force_authenticate(compte)
        res = client.post(f'/api/users/users/{compte.pk}/change_password/',
                          {'old_password': 'a', 'new_password': 'b'}, format='json')
        assert res.status_code == 403

    def test_mot_de_passe_cicada_accepte_en_mode_local(self, settings):
        settings.AUTH_PROVIDER = 'local'
        compte = RoleFactory(email='local@test.fr')
        compte.set_password('MotDePasse123!')
        compte.save()
        res = APIClient().post('/api/auth/login/', {'username': 'local@test.fr', 'password': 'MotDePasse123!'},
                               format='json')
        assert res.status_code == 200

    def test_mode_geonature_sans_reglages(self, settings):
        settings.GEONATURE_AUTH_URL = ''
        res = APIClient().post(URL, {'login': 'x', 'password': 'y'}, format='json')
        assert res.status_code == 503


class TestAppelsAGeoNature:
    def test_mot_de_passe_relaye_et_jeton_utilise_pour_l_organisme(self):
        u = uuid.uuid4()
        res, req = connecter(utilisateur_gn(), fiche_organisme(u))
        assert res.status_code == 200
        req.post.assert_called_once()
        assert req.post.call_args.args[0] == f'{GN}/auth/login'
        assert req.post.call_args.kwargs['json'] == {'login': 'cdupont', 'password': 'secret', 'id_application': '14'}
        assert req.get.call_args.args[0] == f'{GN}/users/organism/3'
        assert req.get.call_args.kwargs['headers'] == {'Accept': 'application/json', 'Authorization': 'Bearer jeton-gn'}
        # Sans cet en-tête, GeoNature répond à un refus par une redirection.
        assert req.post.call_args.kwargs['headers'] == {'Accept': 'application/json'}

    def test_mauvais_mot_de_passe(self):
        res, _ = connecter(reponse(401, None))
        assert res.status_code == 401
        assert not Role.objects.filter(usershub_id_role=146).exists()

    def test_redirection_vers_la_page_de_connexion_vaut_refus(self):
        r = reponse(302, None)
        r.headers = {'Location': 'https://geonature.test/#/login?next=…'}
        res, _ = connecter(r)
        assert res.status_code == 401

    def test_autre_redirection_signale_une_adresse_mal_reglee(self):
        r = reponse(301, None)
        r.headers = {'Location': 'https://geonature.test/api/auth/login'}
        res, _ = connecter(r)
        assert res.status_code == 502

    def test_geonature_injoignable(self):
        with mock.patch(MODULE) as req:
            req.RequestException = requests.RequestException
            req.post.side_effect = requests.ConnectionError()
            res = APIClient().post(URL, {'login': 'cdupont', 'password': 'secret'}, format='json')
        assert res.status_code == 502

    def test_compte_sans_email_refuse(self):
        res, _ = connecter(utilisateur_gn(email=None))
        assert res.status_code == 403
        assert not Role.objects.filter(usershub_id_role=146).exists()


class TestCompte:
    def test_nouveau_compte_cree_avec_jetons_cicada(self):
        res, _ = connecter(utilisateur_gn(), fiche_organisme(uuid.uuid4()))
        assert res.status_code == 200
        corps = res.json()
        assert corps['access'] and corps['refresh']
        compte = Role.objects.get(usershub_id_role=146)
        assert compte.email == 'claire.dupont@reserve.fr'
        assert compte.role_level == 'utilisateur'
        assert compte.active and not compte.pending_validation
        assert not compte.has_usable_password()
        assert corps['user']['id'] == compte.id_role

    def test_compte_existant_retrouve_par_email_garde_ses_droits(self):
        organisme = OrganismeFactory(uuid_organisme=uuid.uuid4())
        existant = AdminOrganismeFactory(email='Claire.Dupont@reserve.fr', id_organisme=organisme)
        existant.set_password('MotDePasseLocal1!')
        existant.save()
        res, _ = connecter(utilisateur_gn(), fiche_organisme(organisme.uuid_organisme))
        assert res.status_code == 200
        existant.refresh_from_db()
        assert existant.usershub_id_role == 146
        assert existant.role_level == 'admin_og'
        assert Role.objects.filter(email__iexact='claire.dupont@reserve.fr').count() == 1

    def test_compte_relie_retrouve_par_id_meme_si_email_change(self):
        relie = RoleFactory(email='ancien@reserve.fr', usershub_id_role=146)
        res, _ = connecter(utilisateur_gn(), fiche_organisme(uuid.uuid4()))
        assert res.status_code == 200
        relie.refresh_from_db()
        assert relie.email == 'claire.dupont@reserve.fr'
        assert Role.objects.filter(usershub_id_role=146).count() == 1

    def test_email_pris_par_un_compte_relie_a_un_autre_usershub(self):
        RoleFactory(email='claire.dupont@reserve.fr', usershub_id_role=999)
        res, _ = connecter(utilisateur_gn(), fiche_organisme(uuid.uuid4()))
        assert res.status_code == 409

    def test_compte_desactive_refuse(self):
        RoleFactory(email='claire.dupont@reserve.fr', active=False)
        res, _ = connecter(utilisateur_gn(), fiche_organisme(uuid.uuid4()))
        assert res.status_code == 403


class TestOrganisme:
    def test_organisme_connu_retrouve_par_uuid_pas_par_id(self):
        # L'id_organisme UsersHub (3) n'a rien à voir avec l'id CICADA : seul l'uuid compte.
        organisme = OrganismeFactory(uuid_organisme=uuid.uuid4(), nom_organisme='RNF')
        avant = BibOrganismes.objects.count()
        res, _ = connecter(utilisateur_gn(), fiche_organisme(organisme.uuid_organisme))
        assert res.status_code == 200
        assert BibOrganismes.objects.count() == avant
        assert Role.objects.get(usershub_id_role=146).id_organisme == organisme

    def test_organisme_inconnu_cree(self):
        u = uuid.uuid4()
        res, _ = connecter(utilisateur_gn(), fiche_organisme(u, nom='CEN Exemple'))
        assert res.status_code == 200
        organisme = BibOrganismes.objects.get(uuid_organisme=u)
        assert organisme.nom_organisme == 'CEN Exemple'
        assert organisme.ville_organisme == 'Dijon'
        assert organisme.additional_data == {'source': 'usershub', 'id_organisme_usershub': 3}
        assert Role.objects.get(usershub_id_role=146).id_organisme == organisme

    def test_changement_d_organisme_applique(self):
        ancien = OrganismeFactory(uuid_organisme=uuid.uuid4())
        nouveau = OrganismeFactory(uuid_organisme=uuid.uuid4())
        compte = RoleFactory(email='claire.dupont@reserve.fr', id_organisme=ancien)
        connecter(utilisateur_gn(), fiche_organisme(nouveau.uuid_organisme))
        compte.refresh_from_db()
        assert compte.id_organisme == nouveau

    def test_pseudo_organisme_exclu(self):
        avant = BibOrganismes.objects.count()
        res, req = connecter(utilisateur_gn(id_organisme=-1), fiche_organisme(uuid.uuid4(), nom='Autre'))
        assert res.status_code == 200
        req.get.assert_not_called()
        assert BibOrganismes.objects.count() == avant
        assert Role.objects.get(usershub_id_role=146).id_organisme is None

    @pytest.mark.parametrize('status_code', [404, 500])
    def test_organisme_illisible_n_empeche_pas_d_entrer_et_ne_retire_rien(self, status_code):
        # 404 : GeoNature antérieur à 2.17.0 (la route n'existe pas).
        organisme = OrganismeFactory(uuid_organisme=uuid.uuid4())
        compte = RoleFactory(email='claire.dupont@reserve.fr', id_organisme=organisme)
        res, _ = connecter(utilisateur_gn(), None, organisme_status=status_code)
        assert res.status_code == 200
        compte.refresh_from_db()
        assert compte.id_organisme == organisme


class TestPremiereConnexion:
    def test_compte_cree_par_geonature_notifie_les_admins_de_l_organisme(self):
        """#706 — un compte créé à la connexion n'a été vu par aucun admin."""
        from apps.notifications.models import Notification

        organisme = OrganismeFactory(uuid_organisme=uuid.uuid4())
        admin = AdminOrganismeFactory(id_organisme=organisme)
        res, _ = connecter(utilisateur_gn(), fiche_organisme(organisme.uuid_organisme))
        assert res.status_code == 200
        notif = Notification.objects.get(notification_type='user_first_login')
        assert notif.recipient == admin
        assert notif.related_user == Role.objects.get(usershub_id_role=146)
