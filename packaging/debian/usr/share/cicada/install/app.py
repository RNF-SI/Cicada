#!/usr/bin/env python3
"""
Application Flask pour l'installation de CICADA
"""
import hmac
import os
from pathlib import Path

from flask import Flask, Response, abort, jsonify, redirect, render_template, request
from install_service import InstallService, get_hub_url

app = Flask(__name__)
install_service = InstallService()

#: Jeton tiré par le paquet (postinst) et affiché dans le terminal avec le lien
#: de l'installateur. Sans lui, quiconque atteignait le port 4567 installait
#: l'instance avec SON compte administrateur, ou s'en servait pour sonder le
#: réseau interne depuis le serveur.
FICHIER_JETON = Path(os.environ.get('CICADA_INSTALLER_TOKEN_FILE', '/etc/cicada/installer_token'))
COOKIE = 'cicada_installeur'
#: Servis sans jeton : ils ne contiennent aucun secret (ils sont dans le dépôt
#: public) et sont lancés par curl depuis le serveur de base, sans navigateur.
ROUTES_PUBLIQUES = {'/api/health', '/prepare-db.sh', '/usershub-lecture.sh'}


def _jeton_attendu():
    try:
        return FICHIER_JETON.read_text().strip()
    except OSError:
        return ''


def _jeton_presente():
    return (request.args.get('jeton') or request.headers.get('X-Installer-Token')
            or request.cookies.get(COOKIE) or '')


@app.before_request
def exiger_le_jeton():
    if request.path in ROUTES_PUBLIQUES or request.path.startswith('/static/'):
        return None
    attendu = _jeton_attendu()
    if not attendu:
        return ("Installateur verrouillé : jeton absent. Sur le serveur, lancez "
                "« sudo dpkg-reconfigure cicada » pour en obtenir un.", 503)
    if not hmac.compare_digest(_jeton_presente(), attendu):
        abort(403)
    if request.args.get('jeton'):
        # Le jeton quitte l'URL (historique, en-tête Referer) pour un cookie.
        reponse = redirect(request.path)
        reponse.set_cookie(COOKIE, attendu, httponly=True, samesite='Strict')
        return reponse
    return None


@app.route('/')
def index():
    if install_service.is_installed():
        return "Installation déjà effectuée. Accédez à votre application.", 403
    return render_template('install.html', hub_url=get_hub_url())


@app.route('/api/install', methods=['POST'])
def install():
    if install_service.is_installed():
        return jsonify({'error': 'Déjà installé'}), 403

    data = request.json
    result = install_service.run_installation(data)
    if result.get('success'):
        _arreter_l_installateur_plus_tard()
    return jsonify(result)


def _arreter_l_installateur_plus_tard():
    """L'instance installée, l'installateur cesse d'écouter sur le réseau.

    Dans deux minutes, le temps que la page affiche la fin de l'installation
    et redirige vers l'application. Sans systemd (tests en conteneur) : rien.
    """
    import subprocess
    try:
        subprocess.Popen(
            ['systemd-run', '--on-active=120', '--unit=cicada-installer-arret',
             'systemctl', 'disable', '--now', 'cicada-installer.service'],
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
        )
        FICHIER_JETON.unlink(missing_ok=True)
    except OSError:
        pass


@app.route('/prepare-db.sh')
def prepare_db_script():
    """Script de préparation du serveur de base, init.sql de cette version inclus."""
    return Response(install_service.prepare_db_script(), mimetype='text/x-shellscript')


@app.route('/usershub-lecture.sh')
def usershub_lecture_script():
    """Script du compte de lecture UsersHub (#764), à lancer sur le serveur de la
    base GeoNature (curl … | sudo bash -s -- --db <base> --client <ip>)."""
    return Response(install_service.usershub_lecture_script(), mimetype='text/x-shellscript')


@app.route('/api/db-client-ip')
def db_client_ip():
    """Adresse de cette machine vue depuis le serveur de base indiqué."""
    host = (request.args.get('host') or '').strip()
    return jsonify({
        'client_ip': install_service.client_ip_for(host) if host else None,
        # PostgreSQL installé sur ce serveur : préparation par --docker-local
        'local': install_service.is_local_db(host),
    })


@app.route('/api/test-usershub', methods=['POST'])
def test_usershub():
    if install_service.is_installed():
        return jsonify({'error': 'Déjà installé'}), 403
    return jsonify({'checks': install_service.test_usershub(request.json or {})})


@app.route('/api/test-db', methods=['POST'])
def test_db():
    if install_service.is_installed():
        return jsonify({'error': 'Déjà installé'}), 403
    return jsonify({'checks': install_service.test_database(request.json or {})})


@app.route('/api/status')
def status():
    return jsonify(install_service.get_status())


@app.route('/api/health')
def health():
    return jsonify({'status': 'ok'})


if __name__ == '__main__':
    # En développement/test, permettre l'accès depuis l'extérieur du conteneur
    import os
    host = os.environ.get('FLASK_HOST', '127.0.0.1')
    port = int(os.environ.get('FLASK_PORT', 4567))
    app.run(host=host, port=port, debug=False)
