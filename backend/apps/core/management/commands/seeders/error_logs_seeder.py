"""
Seeder pour les logs d'erreur.
"""
from datetime import timedelta
from typing import Any, Dict, List

from django.utils import timezone

from apps.core.models import ErrorLog
from apps.users.models import Role

from .base import BaseSeeder


class ErrorLogsSeeder(BaseSeeder):
    """
    Cree des logs d'erreur de test.

    Niveaux:
    - WARNING (3)
    - ERROR (3)
    - CRITICAL (2)

    Statuts:
    - Non acquittes (4)
    - Acquittes (4)
    """

    name = 'error_logs'
    dependencies = ['users']

    def _get_error_logs_data(self, users: List[Role]) -> List[Dict]:
        """Retourne les donnees des logs d'erreur."""
        now = timezone.now()
        admin = users[0]
        admin_rnf = users[1]
        user_rnf = users[5]
        user_cen = users[6]

        return [
            # WARNING - non acquitte, recent
            {
                'level': 'WARNING',
                'message': 'Tentative de connexion avec un token expire',
                'logger_name': 'apps.authentication.views',
                'correlation_id': 'a1b2c3d4-e5f6-7890-abcd-ef1234567890',
                'user': user_rnf,
                'path': '/api/auth/me/',
                'method': 'GET',
                'exception_type': None,
                'stack_trace': None,
                'context': {'token_expired_at': '2024-01-15T10:30:00Z', 'user_agent': 'Mozilla/5.0'},
                'acknowledged': False,
                'acknowledged_by': None,
                'acknowledged_at': None,
                'created_at': now - timedelta(hours=2),
            },
            # WARNING - acquitte
            {
                'level': 'WARNING',
                'message': "Rate limit atteint pour l'utilisateur",
                'logger_name': 'apps.core.middleware.throttling',
                'correlation_id': 'b2c3d4e5-f6a7-8901-bcde-f23456789012',
                'user': user_cen,
                'path': '/api/plans/',
                'method': 'GET',
                'exception_type': None,
                'stack_trace': None,
                'context': {'requests_count': 150, 'limit': 100, 'window': '1h'},
                'acknowledged': True,
                'acknowledged_by': admin,
                'acknowledged_at': now - timedelta(days=2),
                'created_at': now - timedelta(days=3),
            },
            # WARNING - non acquitte
            {
                'level': 'WARNING',
                'message': 'Fichier temporaire non supprime apres upload',
                'logger_name': 'apps.plans.views',
                'correlation_id': 'c3d4e5f6-a7b8-9012-cdef-345678901234',
                'user': admin_rnf,
                'path': '/api/plans/files/upload/',
                'method': 'POST',
                'exception_type': None,
                'stack_trace': None,
                'context': {'temp_file': '/tmp/upload_xyz123.pdf', 'size_bytes': 2456789},
                'acknowledged': False,
                'acknowledged_by': None,
                'acknowledged_at': None,
                'created_at': now - timedelta(days=1),
            },
            # ERROR - non acquitte, recent
            {
                'level': 'ERROR',
                'message': 'Erreur de validation lors de la creation du plan de gestion',
                'logger_name': 'apps.plans.serializers',
                'correlation_id': 'd4e5f6a7-b8c9-0123-defa-456789012345',
                'user': user_rnf,
                'path': '/api/plans/plans/',
                'method': 'POST',
                'exception_type': 'ValidationError',
                'stack_trace': '''Traceback (most recent call last):
  File "/app/apps/plans/views.py", line 145, in create
    serializer.is_valid(raise_exception=True)
  File "/usr/local/lib/python3.11/site-packages/rest_framework/serializers.py", line 235, in is_valid
    raise ValidationError(self.errors)
rest_framework.exceptions.ValidationError: {'date_fin': ['La date de fin doit etre superieure a la date de debut.']}''',
                'context': {'plan_data': {'nom': 'Plan test', 'date_debut': '2025-01-01', 'date_fin': '2024-01-01'}},
                'acknowledged': False,
                'acknowledged_by': None,
                'acknowledged_at': None,
                'created_at': now - timedelta(hours=6),
            },
            # ERROR - acquitte
            {
                'level': 'ERROR',
                'message': 'Impossible de generer le PDF du plan de gestion',
                'logger_name': 'apps.plans.pdf_generator',
                'correlation_id': 'e5f6a7b8-c9d0-1234-efab-567890123456',
                'user': admin_rnf,
                'path': '/api/plans/plans/15/export-pdf/',
                'method': 'GET',
                'exception_type': 'PDFGenerationError',
                'stack_trace': '''Traceback (most recent call last):
  File "/app/apps/plans/pdf_generator.py", line 89, in generate
    self._render_template()
  File "/app/apps/plans/pdf_generator.py", line 156, in _render_template
    raise PDFGenerationError("Template rendering failed")
apps.plans.exceptions.PDFGenerationError: Template rendering failed''',
                'context': {'plan_id': 15, 'template': 'plan_gestion_v2.html'},
                'acknowledged': True,
                'acknowledged_by': admin,
                'acknowledged_at': now - timedelta(days=1),
                'created_at': now - timedelta(days=2),
            },
            # ERROR - acquitte
            {
                'level': 'ERROR',
                'message': 'Timeout lors de la connexion au service externe INPN',
                'logger_name': 'apps.core.services.inpn',
                'correlation_id': 'f6a7b8c9-d0e1-2345-fabc-678901234567',
                'user': None,
                'path': '/api/sites/sync-inpn/',
                'method': 'POST',
                'exception_type': 'requests.exceptions.Timeout',
                'stack_trace': '''Traceback (most recent call last):
  File "/app/apps/core/services/inpn.py", line 45, in sync_sites
    response = requests.get(url, timeout=30)
  File "/usr/local/lib/python3.11/site-packages/requests/api.py", line 73, in get
    return request('get', url, **kwargs)
requests.exceptions.Timeout: HTTPSConnectionPool: Read timed out.''',
                'context': {'service_url': 'https://inpn.mnhn.fr/api/v1/sites', 'timeout': 30},
                'acknowledged': True,
                'acknowledged_by': admin,
                'acknowledged_at': now - timedelta(days=4),
                'created_at': now - timedelta(days=5),
            },
            # CRITICAL - non acquitte
            {
                'level': 'CRITICAL',
                'message': 'Echec de la connexion a la base de donnees',
                'logger_name': 'django.db.backends',
                'correlation_id': 'a7b8c9d0-e1f2-3456-abcd-789012345678',
                'user': None,
                'path': None,
                'method': None,
                'exception_type': 'psycopg2.OperationalError',
                'stack_trace': '''Traceback (most recent call last):
  File "/usr/local/lib/python3.11/site-packages/django/db/backends/base/base.py", line 289, in ensure_connection
    self.connect()
  File "/usr/local/lib/python3.11/site-packages/django/db/backends/base/base.py", line 270, in connect
    self.connection = self.get_new_connection(conn_params)
psycopg2.OperationalError: could not connect to server: Connection refused
    Is the server running on host "db" (172.18.0.2) and accepting TCP/IP connections on port 5432?''',
                'context': {'host': 'db', 'port': 5432, 'database': 'cicada'},
                'acknowledged': False,
                'acknowledged_by': None,
                'acknowledged_at': None,
                'created_at': now - timedelta(days=1, hours=5),
            },
            # CRITICAL - acquitte
            {
                'level': 'CRITICAL',
                'message': 'Espace disque insuffisant pour le stockage des fichiers',
                'logger_name': 'apps.core.storage',
                'correlation_id': 'b8c9d0e1-f2a3-4567-bcde-890123456789',
                'user': admin_rnf,
                'path': '/api/plans/files/upload/',
                'method': 'POST',
                'exception_type': 'OSError',
                'stack_trace': '''Traceback (most recent call last):
  File "/app/apps/core/storage.py", line 78, in save
    self._check_disk_space()
  File "/app/apps/core/storage.py", line 92, in _check_disk_space
    raise OSError("Insufficient disk space")
OSError: [Errno 28] No space left on device: '/app/media/plans/files/'
Disk usage: 98.5% (available: 512MB, required: 2GB)''',
                'context': {'disk_usage_percent': 98.5, 'available_mb': 512, 'required_mb': 2048},
                'acknowledged': True,
                'acknowledged_by': admin,
                'acknowledged_at': now - timedelta(days=6),
                'created_at': now - timedelta(days=7),
            },
        ]

    def seed(self) -> List[ErrorLog]:
        """
        Cree les logs d'erreur de test.

        Returns:
            Liste des ErrorLog crees
        """
        self.log_header("Creation des logs d'erreur")

        users = self.context.require('users')
        error_logs_data = self._get_error_logs_data(users)

        error_logs = []
        for log_data in error_logs_data:
            created_at = log_data.pop('created_at')

            log = ErrorLog.objects.create(**log_data)
            # Mettre a jour created_at manuellement
            ErrorLog.objects.filter(pk=log.pk).update(created_at=created_at)
            log.refresh_from_db()

            error_logs.append(log)

            ack_status = "[ACK]" if log.acknowledged else "[NON ACK]"
            self.log_item('cree', f"{log.level} - {log.message[:50]}... {ack_status}")

        self.log_summary(len(error_logs), "logs d'erreur")
        self.context.set('error_logs', error_logs)
        return error_logs

    def reset(self) -> int:
        """
        Supprime les logs d'erreur de test.

        Returns:
            Nombre de ErrorLog supprimes
        """
        return ErrorLog.objects.all().delete()[0]

    def get_dry_run_summary(self) -> List[str]:
        """
        Resume des logs d'erreur qui seraient crees.

        Returns:
            Liste des lignes du resume
        """
        return [
            "\nLogs d'erreur (8):",
            '  Niveaux: WARNING, ERROR, CRITICAL',
            '  - 3 WARNING (avertissements)',
            '  - 3 ERROR (erreurs standards)',
            '  - 2 CRITICAL (erreurs critiques)',
            '  - 4 non acquittes, 4 acquittes',
            '  - Dates variees sur les 7 derniers jours',
        ]
