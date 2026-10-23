"""
Connexion par un GeoNature / UsersHub (#689) et rattachement à l'organisme (#691).

La lecture de la base UsersHub est simulée (``usershub_base.authentifier``,
testé contre un vrai schéma dans test_api_connexion_usershub_base.py) : ce qui
est vérifié ici, c'est ce que CICADA fait de l'identité lue — mode de
connexion, compte, organisme.
"""
import uuid
from unittest import mock

import pytest
from rest_framework.test import APIClient

from apps.authentication.providers.usershub import IdentiteUsersHub
from apps.users.models import BibOrganismes, Role
from tests.factories.users import AdminOrganismeFactory, OrganismeFactory, RoleFactory

URL = '/api/auth/login-geonature/'
LECTURE = 'apps.authentication.providers.usershub_base.authentifier'

pytestmark = [pytest.mark.django_db, pytest.mark.integration]


@pytest.fixture(autouse=True)
def geonature_configure(settings):
    settings.AUTH_PROVIDER = 'geonature'
    settings.GEONATURE_AUTH_CODE_APPLICATION = 'CICADA'
    settings.USERSHUB_DB_HOST = 'usershub.test'
    settings.USERSHUB_DB_NAME = 'geonature'
    settings.USERSHUB_DB_USER = 'cicada_usershub'
    settings.USERSHUB_DB_PASSWORD = 'x'
    settings.GEONATURE_AUTH_LIBELLE = 'RNF'
    settings.GEONATURE_AUTH_ORGANISMES_EXCLUS = {-1, 2}


@pytest.fixture(autouse=True)
def sans_throttle(settings):
    from django.core.cache import cache
    cache.clear()


def fiche_organisme(uuid_organisme, nom='Réserves Naturelles de France', **kwargs):
    fiche = {'uuid_organisme': str(uuid_organisme), 'nom_organisme': nom,
             'ville_organisme': 'Dijon', 'cp_organisme': '21000'}
    fiche.update(kwargs)
    return fiche


def identite(fiche=None, **kwargs):
    valeurs = {'id_role': 146, 'identifiant': 'cdupont', 'email': 'claire.dupont@reserve.fr',
               'nom': 'Dupont', 'prenom': 'Claire', 'id_organisme': 3, 'fiche_organisme': fiche}
    valeurs.update(kwargs)
    return IdentiteUsersHub(**valeurs)


def connecter(compte_usershub):
    """Simule la lecture de UsersHub et poste une connexion. Renvoie (réponse, mock)."""
    with mock.patch(LECTURE, return_value=compte_usershub) as lecture:
        res = APIClient().post(URL, {'login': 'cdupont', 'password': 'secret'}, format='json')
    return res, lecture


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
        settings.USERSHUB_DB_HOST = ''
        res = APIClient().post(URL, {'login': 'x', 'password': 'y'}, format='json')
        assert res.status_code == 503

    def test_identifiants_transmis_a_la_lecture(self):
        res, lecture = connecter(identite(fiche_organisme(uuid.uuid4())))
        assert res.status_code == 200
        lecture.assert_called_once_with('cdupont', 'secret')


class TestCompte:
    def test_nouveau_compte_cree_avec_jetons_cicada(self):
        res, _ = connecter(identite(fiche_organisme(uuid.uuid4())))
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
        res, _ = connecter(identite(fiche_organisme(organisme.uuid_organisme)))
        assert res.status_code == 200
        existant.refresh_from_db()
        assert existant.usershub_id_role == 146
        assert existant.role_level == 'admin_og'
        assert Role.objects.filter(email__iexact='claire.dupont@reserve.fr').count() == 1

    def test_compte_relie_retrouve_par_id_meme_si_email_change(self):
        relie = RoleFactory(email='ancien@reserve.fr', usershub_id_role=146)
        res, _ = connecter(identite(fiche_organisme(uuid.uuid4())))
        assert res.status_code == 200
        relie.refresh_from_db()
        assert relie.email == 'claire.dupont@reserve.fr'
        assert Role.objects.filter(usershub_id_role=146).count() == 1

    def test_email_pris_par_un_compte_relie_a_un_autre_usershub(self):
        RoleFactory(email='claire.dupont@reserve.fr', usershub_id_role=999)
        res, _ = connecter(identite(fiche_organisme(uuid.uuid4())))
        assert res.status_code == 409

    def test_compte_desactive_refuse(self):
        RoleFactory(email='claire.dupont@reserve.fr', active=False)
        res, _ = connecter(identite(fiche_organisme(uuid.uuid4())))
        assert res.status_code == 403


class TestOrganisme:
    def test_organisme_connu_retrouve_par_uuid_pas_par_id(self):
        # L'id_organisme UsersHub (3) n'a rien à voir avec l'id CICADA : seul l'uuid compte.
        organisme = OrganismeFactory(uuid_organisme=uuid.uuid4(), nom_organisme='RNF')
        avant = BibOrganismes.objects.count()
        res, _ = connecter(identite(fiche_organisme(organisme.uuid_organisme)))
        assert res.status_code == 200
        assert BibOrganismes.objects.count() == avant
        assert Role.objects.get(usershub_id_role=146).id_organisme == organisme

    def test_organisme_inconnu_cree(self):
        u = uuid.uuid4()
        res, _ = connecter(identite(fiche_organisme(u, nom='CEN Exemple')))
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
        connecter(identite(fiche_organisme(nouveau.uuid_organisme)))
        compte.refresh_from_db()
        assert compte.id_organisme == nouveau

    def test_pseudo_organisme_exclu(self):
        avant = BibOrganismes.objects.count()
        res, _ = connecter(identite(fiche_organisme(uuid.uuid4(), nom='Autre'), id_organisme=-1))
        assert res.status_code == 200
        assert BibOrganismes.objects.count() == avant
        assert Role.objects.get(usershub_id_role=146).id_organisme is None

    def test_fiche_absente_n_empeche_pas_d_entrer_et_ne_retire_rien(self):
        organisme = OrganismeFactory(uuid_organisme=uuid.uuid4())
        compte = RoleFactory(email='claire.dupont@reserve.fr', id_organisme=organisme)
        res, _ = connecter(identite(None))
        assert res.status_code == 200
        compte.refresh_from_db()
        assert compte.id_organisme == organisme


class TestPremiereConnexion:
    def test_compte_cree_par_geonature_notifie_les_admins_de_l_organisme(self):
        """#706 — un compte créé à la connexion n'a été vu par aucun admin."""
        from apps.notifications.models import Notification

        organisme = OrganismeFactory(uuid_organisme=uuid.uuid4())
        admin = AdminOrganismeFactory(id_organisme=organisme)
        res, _ = connecter(identite(fiche_organisme(organisme.uuid_organisme)))
        assert res.status_code == 200
        notif = Notification.objects.get(notification_type='user_first_login')
        assert notif.recipient == admin
        assert notif.related_user == Role.objects.get(usershub_id_role=146)
