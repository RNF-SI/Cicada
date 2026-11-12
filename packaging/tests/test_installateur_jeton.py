"""L'installateur web n'obéit qu'à qui a le lien affiché par le paquet.

Il écoute sur le réseau, en root, le temps que l'opérateur remplisse le
formulaire (parfois plusieurs jours). Sans jeton, quiconque atteignait le port
installait l'instance avec son propre compte administrateur, ou s'en servait
pour sonder le réseau interne depuis le serveur.
"""
import pathlib
import sys

import pytest

INSTALL_DIR = pathlib.Path(__file__).resolve().parents[1] / 'debian/usr/share/cicada/install'
sys.path.insert(0, str(INSTALL_DIR))

import app as installateur  # noqa: E402


@pytest.fixture
def client(tmp_path, monkeypatch):
    jeton = tmp_path / 'installer_token'
    jeton.write_text('secret-du-paquet\n')
    monkeypatch.setattr(installateur, 'FICHIER_JETON', jeton)
    monkeypatch.setattr(installateur.install_service, 'is_installed', lambda: False)
    monkeypatch.setattr(installateur.install_service, 'client_ip_for', lambda host: '192.0.2.1')
    monkeypatch.setattr(installateur.install_service, 'is_local_db', lambda host: False)
    monkeypatch.setattr(installateur.install_service, 'prepare_db_script', lambda: '#!/bin/sh\n')
    installateur.app.config['TESTING'] = True
    return installateur.app.test_client()


@pytest.mark.parametrize('methode, url', [
    ('get', '/'),
    ('post', '/api/install'),
    ('post', '/api/test-db'),
    ('post', '/api/test-usershub'),
    ('get', '/api/db-client-ip?host=intranet'),
    ('get', '/api/status'),
])
def test_sans_jeton_rien_ne_repond(client, methode, url):
    assert getattr(client, methode)(url, json={}).status_code == 403


def test_un_faux_jeton_est_refuse(client):
    assert client.get('/', headers={'X-Installer-Token': 'devine'}).status_code == 403


def test_le_lien_du_paquet_ouvre_le_formulaire_et_pose_un_cookie(client):
    reponse = client.get('/?jeton=secret-du-paquet')
    assert reponse.status_code == 302
    assert 'jeton' not in reponse.headers['Location']
    cookie = reponse.headers['Set-Cookie']
    assert 'HttpOnly' in cookie and 'SameSite=Strict' in cookie
    # Le navigateur renvoie le cookie : les appels de la page passent.
    assert client.get('/api/db-client-ip?host=intranet').status_code == 200


def test_les_scripts_et_la_sante_restent_publics(client):
    assert client.get('/api/health').status_code == 200
    assert client.get('/prepare-db.sh').status_code == 200


def test_sans_fichier_de_jeton_l_installateur_est_verrouille(client, tmp_path, monkeypatch):
    monkeypatch.setattr(installateur, 'FICHIER_JETON', tmp_path / 'absent')
    assert client.get('/', headers={'X-Installer-Token': ''}).status_code == 503
