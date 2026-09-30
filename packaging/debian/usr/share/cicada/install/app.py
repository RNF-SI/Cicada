#!/usr/bin/env python3
"""
Application Flask pour l'installation de CICADA
"""
from flask import Flask, render_template, request, jsonify
from install_service import InstallService

app = Flask(__name__)
install_service = InstallService()


@app.route('/')
def index():
    if install_service.is_installed():
        return "Installation déjà effectuée. Accédez à votre application.", 403
    return render_template('install.html')


@app.route('/api/install', methods=['POST'])
def install():
    if install_service.is_installed():
        return jsonify({'error': 'Déjà installé'}), 403

    data = request.json
    result = install_service.run_installation(data)
    return jsonify(result)


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
