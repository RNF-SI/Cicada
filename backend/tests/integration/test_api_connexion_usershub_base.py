"""
Connexion UsersHub par la base (#764) : CICADA lit la base UsersHub et contrôle
le droit sur SON application, ce que l'API GeoNature (retirée) ne faisait pas.

Pas de simulation : un schéma UsersHub minimal est créé dans la base de test
(la base de CICADA a déjà un schéma « utilisateurs », d'où USERSHUB_DB_SCHEMA),
et le module s'y connecte comme il le ferait à la base de GeoNature. Les
requêtes, les jointures de groupes et bcrypt sont donc réellement exécutés.

Le schéma est rempli par une connexion à part, en autocommit : le module ouvre
sa propre connexion et ne verrait pas les écritures de la transaction du test.
"""
import hashlib
import uuid

import bcrypt
import psycopg
import pytest
from django.db import connection
from rest_framework.test import APIClient

from apps.users.models import BibOrganismes, Role

URL = '/api/auth/login-geonature/'
SCHEMA = 'uh_test_764'
UUID_RNF = uuid.UUID('6c7a3b0e-0d1f-4a8e-9a55-2f7f2b1f1001')

pytestmark = [pytest.mark.django_db, pytest.mark.integration]

SCHEMA_SQL = f"""
CREATE SCHEMA {SCHEMA};
CREATE TABLE {SCHEMA}.t_applications (id_application int PRIMARY KEY, code_application text);
CREATE TABLE {SCHEMA}.bib_organismes (
    id_organisme int PRIMARY KEY, uuid_organisme uuid, nom_organisme text, adresse_organisme text,
    cp_organisme text, ville_organisme text, tel_organisme text, fax_organisme text,
    email_organisme text, url_organisme text);
CREATE TABLE {SCHEMA}.t_roles (
    id_role int PRIMARY KEY, groupe boolean DEFAULT false, identifiant text, email text,
    nom_role text, prenom_role text, id_organisme int, pass text, pass_plus text,
    active boolean DEFAULT true);
CREATE TABLE {SCHEMA}.cor_roles (id_role_groupe int, id_role_utilisateur int);
CREATE TABLE {SCHEMA}.cor_role_app_profil (id_role int, id_application int, id_profil int);

INSERT INTO {SCHEMA}.t_applications VALUES (1, 'GNG'), (18, 'CICADA');
INSERT INTO {SCHEMA}.bib_organismes (id_organisme, uuid_organisme, nom_organisme, ville_organisme)
    VALUES (3, '{UUID_RNF}', 'Réserves Naturelles de France', 'Dijon'), (2, gen_random_uuid(), 'ALL', NULL);
-- Grp_all a un profil sur CICADA, Grp_admin sur GeoNature
INSERT INTO {SCHEMA}.t_roles (id_role, groupe, nom_role) VALUES (900, true, 'Grp_all'), (901, true, 'Grp_admin');
INSERT INTO {SCHEMA}.cor_role_app_profil VALUES (900, 18, 1), (901, 1, 1);
"""


def base_usershub_sql():
    """Connexion à la base de test, hors de la transaction du test."""
    base = connection.settings_dict
    return psycopg.connect(host=base['HOST'] or 'localhost', port=base['PORT'] or 5432,
                           dbname=base['NAME'], user=base['USER'], password=base['PASSWORD'],
                           autocommit=True)


def bcrypt_de(mdp):
    return bcrypt.hashpw(mdp.encode(), bcrypt.gensalt(rounds=4)).decode()


def ajouter_compte(id_role, identifiant, groupes=(), droit_direct=None, pass_plus='secret', pass_md5=None,
                   active=True, email=None, id_organisme=3):
    with base_usershub_sql() as cx, cx.cursor() as c:
        c.execute(
            f"INSERT INTO {SCHEMA}.t_roles (id_role, identifiant, email, nom_role, prenom_role, id_organisme,"
            f" pass, pass_plus, active) VALUES (%s, %s, %s, 'Dupont', 'Claire', %s, %s, %s, %s)",
            [id_role, identifiant, email or f'{identifiant}@reserve.fr', id_organisme,
             hashlib.md5(pass_md5.encode()).hexdigest() if pass_md5 else None,
             bcrypt_de(pass_plus) if pass_plus else None, active],
        )
        for groupe in groupes:
            c.execute(f"INSERT INTO {SCHEMA}.cor_roles VALUES (%s, %s)", [groupe, id_role])
        if droit_direct:
            c.execute(f"INSERT INTO {SCHEMA}.cor_role_app_profil VALUES (%s, %s, 1)", [id_role, droit_direct])


@pytest.fixture(autouse=True)
def base_usershub(settings):
    with base_usershub_sql() as cx:
        cx.execute(f"DROP SCHEMA IF EXISTS {SCHEMA} CASCADE")
        cx.execute(SCHEMA_SQL)
    base = connection.settings_dict
    settings.AUTH_PROVIDER = 'geonature'
    settings.GEONATURE_AUTH_CODE_APPLICATION = 'CICADA'
    settings.GEONATURE_AUTH_LIBELLE = 'RNF'
    settings.GEONATURE_AUTH_ORGANISMES_EXCLUS = {2}
    settings.USERSHUB_DB_HOST = base['HOST'] or 'localhost'
    settings.USERSHUB_DB_PORT = int(base['PORT'] or 5432)
    settings.USERSHUB_DB_NAME = base['NAME']
    settings.USERSHUB_DB_USER = base['USER']
    settings.USERSHUB_DB_PASSWORD = base['PASSWORD']
    settings.USERSHUB_DB_SCHEMA = SCHEMA
    from django.core.cache import cache
    cache.clear()
    yield
    with base_usershub_sql() as cx:
        cx.execute(f"DROP SCHEMA IF EXISTS {SCHEMA} CASCADE")


def connecter(login='cdupont', password='secret'):
    return APIClient().post(URL, {'login': login, 'password': password}, format='json')


class TestDroitSurLApplication:
    """Le cœur de #764 : c'est le droit sur CICADA qui compte, pas celui sur GeoNature."""

    def test_droit_via_un_groupe(self):
        ajouter_compte(146, 'cdupont', groupes=[900])
        res = connecter()
        assert res.status_code == 200, res.json()
        assert 'access' in res.json()

    def test_droit_direct(self):
        ajouter_compte(146, 'cdupont', droit_direct=18)
        assert connecter().status_code == 200

    def test_droit_sur_geonature_seulement_refuse(self):
        # Ce que l'API GeoNature laissait entrer : un droit sur GNG, aucun sur CICADA.
        ajouter_compte(146, 'cdupont', groupes=[901])
        res = connecter()
        assert res.status_code == 403
        assert "n'a pas accès à CICADA" in res.json()['detail']
        assert not Role.objects.filter(usershub_id_role=146).exists()

    def test_aucun_droit_refuse(self):
        # Ce que pypnusershub <= 3.2 laissait entrer (bug du filtre par application).
        ajouter_compte(146, 'cdupont')
        assert connecter().status_code == 403

    def test_code_application_reglable(self, settings):
        ajouter_compte(146, 'cdupont', groupes=[901])
        settings.GEONATURE_AUTH_CODE_APPLICATION = 'GNG'
        assert connecter().status_code == 200


class TestMotDePasse:

    def test_mauvais_mot_de_passe(self):
        ajouter_compte(146, 'cdupont', groupes=[900])
        res = connecter(password='faux')
        assert res.status_code == 401
        assert res.json()['detail'] == "Identifiant ou mot de passe incorrect."

    def test_identifiant_inconnu_meme_message(self):
        res = connecter(login='inconnu')
        assert res.status_code == 401
        assert res.json()['detail'] == "Identifiant ou mot de passe incorrect."

    def test_ancien_mot_de_passe_md5(self):
        ajouter_compte(146, 'cdupont', groupes=[900], pass_plus=None, pass_md5='secret')
        assert connecter().status_code == 200
        assert connecter(password='faux').status_code == 401

    def test_md5_jamais_reecrit(self):
        # Lecture seule : contrairement à pypnusershub, rien n'est écrit dans UsersHub.
        ajouter_compte(146, 'cdupont', groupes=[900], pass_plus=None, pass_md5='secret')
        connecter()
        with base_usershub_sql() as cx:
            assert cx.execute(f"SELECT pass_plus FROM {SCHEMA}.t_roles WHERE id_role = 146").fetchone()[0] is None

    def test_le_droit_n_est_pas_devoile_sans_le_bon_mot_de_passe(self):
        ajouter_compte(146, 'cdupont')  # aucun droit
        assert connecter(password='faux').status_code == 401


class TestCompteUsersHub:

    def test_compte_desactive(self):
        ajouter_compte(146, 'cdupont', groupes=[900], active=False)
        res = connecter()
        assert res.status_code == 403
        assert 'désactivé' in res.json()['detail']

    def test_un_groupe_ne_se_connecte_pas(self):
        with base_usershub_sql() as cx:
            cx.execute(f"UPDATE {SCHEMA}.t_roles SET identifiant = 'grp', pass_plus = %s WHERE id_role = 900",
                       [bcrypt_de('secret')])
        assert connecter(login='grp').status_code == 401

    def test_identifiant_ambigu_refuse(self):
        ajouter_compte(146, 'cdupont', groupes=[900])
        ajouter_compte(147, 'cdupont', groupes=[900], email='autre@reserve.fr')
        assert connecter().status_code == 401

    def test_sans_email(self):
        ajouter_compte(146, 'cdupont', groupes=[900], email='-')
        assert connecter().status_code == 403


class TestRattachement:
    """Compte et organisme CICADA (#689, #691), à partir de la fiche lue dans la base."""

    def test_compte_et_organisme_crees(self):
        ajouter_compte(146, 'cdupont', groupes=[900])
        assert connecter().status_code == 200
        compte = Role.objects.get(usershub_id_role=146)
        assert compte.email == 'cdupont@reserve.fr'
        assert compte.id_organisme.uuid_organisme == UUID_RNF
        assert compte.id_organisme.ville_organisme == 'Dijon'

    def test_organisme_existant_retrouve_par_uuid(self):
        existant = BibOrganismes.objects.create(uuid_organisme=UUID_RNF, nom_organisme='RNF (local)')
        ajouter_compte(146, 'cdupont', groupes=[900])
        connecter()
        assert Role.objects.get(usershub_id_role=146).id_organisme == existant

    def test_organisme_exclu(self):
        ajouter_compte(146, 'cdupont', groupes=[900], id_organisme=2)
        assert connecter().status_code == 200
        assert Role.objects.get(usershub_id_role=146).id_organisme is None


class TestPanneEtConfiguration:

    def test_base_injoignable(self, settings):
        ajouter_compte(146, 'cdupont', groupes=[900])
        settings.USERSHUB_DB_PORT = 1
        settings.GEONATURE_AUTH_TIMEOUT = 2
        res = connecter()
        assert res.status_code == 502
        assert 'RNF' in res.json()['detail']

    def test_schema_inattendu(self, settings):
        settings.USERSHUB_DB_SCHEMA = 'schema_absent'
        assert connecter().status_code == 502

    def test_non_configuree(self, settings):
        settings.GEONATURE_AUTH_CODE_APPLICATION = ''
        assert connecter().status_code == 503

    def test_avertissement_au_demarrage(self, settings):
        from apps.authentication.checks import verifier_mode_connexion
        settings.USERSHUB_DB_HOST = ''
        assert 'authentication.W004' in [p.id for p in verifier_mode_connexion(None)]

    def test_ancienne_verification_par_l_api_signalee(self, settings, monkeypatch):
        # Instance mise à jour sans avoir configuré la base : l'avertissement
        # dit que GEONATURE_AUTH_URL ne sert plus.
        from apps.authentication.checks import verifier_mode_connexion
        settings.USERSHUB_DB_HOST = ''
        monkeypatch.setenv('GEONATURE_AUTH_URL', 'https://geonature.test/api')
        w004 = [p for p in verifier_mode_connexion(None) if p.id == 'authentication.W004']
        assert w004 and 'GEONATURE_AUTH_URL' in w004[0].msg

    @pytest.mark.parametrize('hote, sslmode, attendu', [
        ('10.0.200.11', 'prefer', True),       # base distante, connexion en clair possible
        ('10.0.200.11', 'disable', True),
        ('10.0.200.11', 'require', False),
        ('10.0.200.11', 'verify-full', False),
        ('host.docker.internal', 'prefer', False),  # même serveur : rien sur le réseau
        ('localhost', 'prefer', False),
    ])
    def test_avertissement_base_distante_sans_chiffrement(self, settings, hote, sslmode, attendu):
        from apps.authentication.checks import verifier_mode_connexion
        settings.USERSHUB_DB_HOST = hote
        settings.USERSHUB_DB_SSLMODE = sslmode
        ids = [p.id for p in verifier_mode_connexion(None)]
        assert ('authentication.W005' in ids) is attendu

    def test_chiffrement_exige_transmis_a_la_connexion(self, settings):
        # La base de test n'a pas ssl : « require » doit échouer, preuve que
        # le réglage atteint bien libpq au lieu d'être ignoré.
        ajouter_compte(146, 'cdupont', groupes=[900])
        settings.USERSHUB_DB_SSLMODE = 'require'
        assert connecter().status_code == 502
        settings.USERSHUB_DB_SSLMODE = 'disable'
        assert connecter().status_code == 200


class TestVerifierUsersHub:
    """Avant de basculer une instance en service : qui serait refusé ?"""

    def lancer(self):
        from io import StringIO

        from django.core.management import call_command
        sortie = StringIO()
        try:
            call_command('verifier_usershub', stdout=sortie, stderr=sortie)
            code = 0
        except SystemExit as exc:
            code = exc.code
        return code, sortie.getvalue()

    def test_bilan_des_comptes_existants(self):
        Role.objects.all().delete()
        ajouter_compte(146, 'relie', groupes=[900])
        ajouter_compte(147, 'relie_sans_droit', groupes=[901])
        ajouter_compte(148, 'local_par_email', groupes=[900], email='claire@reserve.fr')
        ajouter_compte(149, 'inactif', groupes=[900], active=False)
        Role.objects.create(email='relie@reserve.fr', usershub_id_role=146)
        Role.objects.create(email='relie_sans_droit@reserve.fr', usershub_id_role=147)
        Role.objects.create(email='Claire@Reserve.fr')
        Role.objects.create(email='inactif@reserve.fr', usershub_id_role=149)
        Role.objects.create(email='admin@instance.fr', is_superuser=True)

        code, sortie = self.lancer()

        assert code == 1
        assert '5 compte(s) CICADA actif(s) : 2 pourront se connecter, 3 seraient refusés' in sortie
        assert "relie_sans_droit@reserve.fr — pas de profil sur l'application" in sortie
        assert 'inactif@reserve.fr — compte UsersHub désactivé' in sortie
        assert 'admin@instance.fr — aucun compte UsersHub' in sortie
        assert 'Super-utilisateurs qui pourront se connecter : 0' in sortie

    def test_tout_le_monde_passe(self):
        Role.objects.all().delete()
        ajouter_compte(146, 'relie', groupes=[900])
        Role.objects.create(email='relie@reserve.fr', usershub_id_role=146)
        assert self.lancer()[0] == 0

    def test_base_injoignable(self, settings):
        settings.USERSHUB_DB_PORT = 1
        settings.GEONATURE_AUTH_TIMEOUT = 2
        assert self.lancer()[0] == 2

    def test_fonctionne_meme_en_mode_local(self, settings):
        # On vérifie AVANT de passer en mode GeoNature : le mode en service n'importe pas.
        settings.AUTH_PROVIDER = 'local'
        Role.objects.all().delete()
        assert self.lancer()[0] == 0
