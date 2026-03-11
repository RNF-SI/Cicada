"""
Commande Django pour importer les données INPG (Inventaire National
du Patrimoine Géologique) dans la base de données.

Les données proviennent du projet socle et sont stockées dans un fichier
SQL d'inserts (backend/inpg_data/inpg_inserts.sql).

Pour mettre à jour les données : régénérer le fichier SQL depuis la base
source, puis relancer avec --force.

Usage:
    python manage.py import_inpg                # Import (skip si déjà fait)
    python manage.py import_inpg --force        # Force la réimportation
"""

import logging
import os

from django.core.management.base import BaseCommand
from django.db import connection, transaction

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Importe les données INPG depuis le fichier SQL'

    def add_arguments(self, parser):
        parser.add_argument(
            '--force',
            action='store_true',
            help='Force le rechargement complet',
        )

    def handle(self, *args, **options):
        force = options['force']

        self.stdout.write(self.style.MIGRATE_HEADING(
            '=== IMPORT INPG ==='
        ))

        if not force and self._is_installed():
            self.stdout.write(self.style.SUCCESS(
                'INPG est déjà importé. '
                'Utilisez --force pour forcer le rechargement.'
            ))
            return

        sql_file = os.path.join(
            os.path.dirname(os.path.dirname(os.path.dirname(
                os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            ))),
            'inpg_data', 'inpg_inserts.sql'
        )

        if not os.path.exists(sql_file):
            self.stderr.write(self.style.ERROR(
                f'Fichier SQL introuvable : {sql_file}'
            ))
            return

        self.stdout.write(f'  Fichier SQL : {sql_file}')

        with transaction.atomic():
            self._ensure_schema()

            if force:
                self._truncate_table()

            self._execute_sql(sql_file)

        count = self._count_records()
        self.stdout.write(self.style.SUCCESS(
            f'Import INPG terminé : {count} sites géologiques'
        ))

    def _is_installed(self):
        try:
            with connection.cursor() as cursor:
                cursor.execute('SELECT COUNT(*) FROM ref_inpg.inpg')
                return cursor.fetchone()[0] > 0
        except Exception:
            return False

    def _ensure_schema(self):
        with connection.cursor() as cursor:
            cursor.execute('CREATE SCHEMA IF NOT EXISTS ref_inpg')

    def _truncate_table(self):
        try:
            with connection.cursor() as cursor:
                cursor.execute('TRUNCATE TABLE ref_inpg.inpg CASCADE')
            self.stdout.write('  Table vidée (--force)')
        except Exception:
            pass

    def _execute_sql(self, sql_file):
        self.stdout.write('  Exécution du SQL...')
        with open(sql_file, 'r', encoding='utf-8') as f:
            sql = f.read()

        with connection.cursor() as cursor:
            cursor.execute(sql)

    def _count_records(self):
        with connection.cursor() as cursor:
            cursor.execute('SELECT COUNT(*) FROM ref_inpg.inpg')
            return cursor.fetchone()[0]
