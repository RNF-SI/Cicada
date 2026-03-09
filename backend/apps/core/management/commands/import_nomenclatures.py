"""
Commande Django pour importer les nomenclatures de référence.

Les nomenclatures sont des données essentielles au fonctionnement de l'application
(types de sites, types d'évaluation, types de documents, etc.).
Cette commande est idempotente : elle ne réimporte pas si les données existent déjà.

Usage:
    python manage.py import_nomenclatures           # Import (skip si déjà fait)
    python manage.py import_nomenclatures --force    # Force la réimportation
"""
import logging
from pathlib import Path

from django.core.management.base import BaseCommand
from django.db import connection, transaction

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Importe les nomenclatures de référence depuis les fichiers SQL'

    def add_arguments(self, parser):
        parser.add_argument(
            '--force',
            action='store_true',
            help='Force la réimportation même si les nomenclatures existent déjà',
        )

    def handle(self, *args, **options):
        self.stdout.write(self.style.MIGRATE_HEADING('=== IMPORT DES NOMENCLATURES ==='))

        force = options['force']

        if not force and self._nomenclatures_already_exist():
            self.stdout.write(self.style.SUCCESS(
                '✓ Les nomenclatures sont déjà importées - import ignoré'
            ))
            self.stdout.write('  (Utilisez --force pour forcer la réimportation)')
            return

        # Chemins vers les fichiers SQL
        project_dir = Path(__file__).resolve().parents[4]  # backend/
        types_file = project_dir / 'nomenclatures_data' / 'types_inserts.sql'
        nomenclatures_file = project_dir / 'nomenclatures_data' / 'nomenclatures_inserts.sql'

        if not types_file.exists():
            self.stderr.write(self.style.ERROR(f'Fichier non trouvé: {types_file}'))
            return

        if not nomenclatures_file.exists():
            self.stderr.write(self.style.ERROR(f'Fichier non trouvé: {nomenclatures_file}'))
            return

        try:
            with transaction.atomic():
                # Vider les tables pour un import propre
                self._clear_existing_data()

                # Charger les types puis les nomenclatures
                self._execute_insert_file(types_file, 'types de nomenclatures')
                self._execute_insert_file(nomenclatures_file, 'nomenclatures')

                # Mettre à jour les séquences
                self._update_sequences()

                # Vérifier l'import
                self._verify_import()

            self.stdout.write(self.style.SUCCESS('✓ Import des nomenclatures terminé avec succès!'))

        except Exception as e:
            self.stderr.write(self.style.ERROR(f'✗ Erreur lors de l\'import: {e}'))
            raise

    def _nomenclatures_already_exist(self):
        """Vérifie si les nomenclatures sont déjà importées."""
        try:
            with connection.cursor() as cursor:
                cursor.execute('SELECT COUNT(*) FROM t_nomenclatures')
                count = cursor.fetchone()[0]
                return count > 0
        except Exception:
            return False

    def _clear_existing_data(self):
        """Vide les tables de nomenclatures."""
        self.stdout.write('  Vidage des tables existantes...')
        with connection.cursor() as cursor:
            cursor.execute('TRUNCATE TABLE t_nomenclatures CASCADE;')
            cursor.execute('TRUNCATE TABLE bib_nomenclatures_types CASCADE;')
        self.stdout.write(self.style.SUCCESS('  ✓ Tables vidées'))

    def _execute_insert_file(self, file_path, description):
        """Exécute un fichier contenant des INSERT statements."""
        self.stdout.write(f'  Import des {description}...')

        with open(file_path, 'r', encoding='utf-8') as f:
            sql_content = f.read()

        if not sql_content.strip():
            self.stderr.write(self.style.WARNING(f'  Fichier vide: {file_path}'))
            return

        with connection.cursor() as cursor:
            for statement in sql_content.split('\n'):
                statement = statement.strip()
                if statement and statement.startswith('INSERT INTO'):
                    cursor.execute(statement)

        self.stdout.write(self.style.SUCCESS(f'  ✓ {description} importés'))

    def _update_sequences(self):
        """Met à jour les séquences PostgreSQL après l'import."""
        with connection.cursor() as cursor:
            # Séquence pour bib_nomenclatures_types
            cursor.execute("""
                SELECT setval(
                    pg_get_serial_sequence('ref_nomenclatures.bib_nomenclatures_types', 'id_type'),
                    COALESCE((SELECT MAX(id_type) FROM bib_nomenclatures_types), 1),
                    true
                )
            """)
            # Séquence pour t_nomenclatures
            cursor.execute("""
                SELECT setval(
                    pg_get_serial_sequence('ref_nomenclatures.t_nomenclatures', 'id_nomenclature'),
                    COALESCE((SELECT MAX(id_nomenclature) FROM t_nomenclatures), 1),
                    true
                )
            """)

    def _verify_import(self):
        """Vérifie et affiche le résultat de l'import."""
        with connection.cursor() as cursor:
            cursor.execute('SELECT COUNT(*) FROM bib_nomenclatures_types')
            types_count = cursor.fetchone()[0]

            cursor.execute('SELECT COUNT(*) FROM t_nomenclatures')
            nomenclatures_count = cursor.fetchone()[0]

        self.stdout.write(f'  ✓ Types de nomenclatures importés: {types_count}')
        self.stdout.write(f'  ✓ Nomenclatures importées: {nomenclatures_count}')
