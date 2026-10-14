#!/usr/bin/env python3
"""Fausse API de suivi, pour que le banc n'écrive jamais dans la vraie.

Répond comme tracking-api aux routes appelées par l'installateur et le
heartbeat, et journalise chaque appel (une ligne JSON) pour les contrôles.
Bibliothèque standard uniquement : elle tourne avant toute installation.
"""
import json
import sys
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, HTTPServer

LOG = sys.argv[1]
PORT = int(sys.argv[2]) if len(sys.argv) > 2 else 8099


class Handler(BaseHTTPRequestHandler):
    def _reply(self, payload):
        body = json.dumps(payload).encode()
        self.send_response(200)
        self.send_header('Content-Type', 'application/json')
        self.send_header('Content-Length', str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _log(self, body):
        with open(LOG, 'a') as f:
            f.write(json.dumps({
                'method': self.command,
                'path': self.path,
                'token_header': self.headers.get('X-Instance-Token'),
                'body': body,
            }) + '\n')

    def do_POST(self):
        length = int(self.headers.get('Content-Length') or 0)
        raw = self.rfile.read(length).decode() if length else ''
        try:
            body = json.loads(raw) if raw else None
        except ValueError:
            body = raw
        self._log(body)
        now = datetime.now(timezone.utc).isoformat()
        if self.path.rstrip('/').endswith('/heartbeat'):
            self._reply({'update_available': False, 'latest_version': None, 'last_heartbeat': now})
        else:
            self._reply({'status': 'ok'})

    def do_GET(self):
        self._log(None)
        self._reply({'update_available': False, 'latest_version': None})

    def log_message(self, *args):
        pass


HTTPServer(('127.0.0.1', PORT), Handler).serve_forever()
